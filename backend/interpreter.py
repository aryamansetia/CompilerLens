"""Small bounded AST interpreter for the CompilerLens educational subset."""

from __future__ import annotations

import ast as py_ast
import math
import re
from typing import Any


class RuntimeErrorInProgram(Exception):
    pass


class _Return(Exception):
    def __init__(self, value: Any = 0) -> None:
        self.value = value


class Interpreter:
    MAX_STEPS = 10_000
    MAX_CALL_DEPTH = 64

    def __init__(self, stdin: str = "") -> None:
        self.environments: list[dict[str, Any]] = [{}]
        self.functions: dict[str, dict] = {}
        self.output: list[str] = []
        self.inputs = stdin.split()
        self.input_index = 0
        self.steps = 0
        self.call_depth = 0

    def run(self, program: dict) -> dict:
        statements = program.get("children", [])
        self.functions = {str(item.get("detail", "")).split(maxsplit=1)[-1]: item
                          for item in statements if item.get("node_type") == "Function"}
        try:
            for statement in statements:
                if statement.get("node_type") != "Function":
                    self._statement(statement)
            if "main" in self.functions:
                self._call(self.functions["main"], [])
        except _Return:
            pass
        return {"stdout": "".join(self.output), "steps": self.steps}

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.MAX_STEPS:
            raise RuntimeErrorInProgram("Execution stopped after the 10,000-step safety limit.")

    def _lookup(self, name: str) -> Any:
        for env in reversed(self.environments):
            if name in env:
                return env[name]
        raise RuntimeErrorInProgram(f"Variable '{name}' has no runtime value.")

    def _assign(self, name: str, value: Any) -> None:
        for env in reversed(self.environments):
            if name in env:
                env[name] = value
                return
        raise RuntimeErrorInProgram(f"Variable '{name}' is not declared.")

    @staticmethod
    def _literal_string(value: str) -> str:
        try:
            result = py_ast.literal_eval(value)
            return result if isinstance(result, str) else str(result)
        except (ValueError, SyntaxError):
            return value.replace("\\n", "\n").replace("\\t", "\t")

    def _expr(self, node: dict) -> Any:
        self._tick()
        kind = node.get("node_type")
        detail = str(node.get("detail") or "")
        children = node.get("children", [])
        if kind == "NumberLiteral":
            try:
                if detail.lower().endswith("f"): detail = detail[:-1]
                return float(detail) if any(char in detail.lower() for char in ".e") else int(re.sub(r"(u|l)+$", "", detail, flags=re.I))
            except ValueError as error:
                raise RuntimeErrorInProgram(f"Invalid numeric value '{detail}'.") from error
        if kind == "BooleanLiteral":
            return detail == "true"
        if kind == "StringLiteral":
            return self._literal_string(detail) if detail.startswith('"') else detail.replace("\\n", "\n")
        if kind == "Identifier":
            return self._lookup(detail)
        if kind == "UnaryExpression":
            value = self._expr(children[0])
            return -value if detail == "-" else +value
        if kind == "BinaryExpression":
            left = self._expr(children[0])
            if detail == "&&" and not left: return False
            if detail == "||" and left: return True
            right = self._expr(children[1])
            operations = {
                "+": lambda: left + right, "-": lambda: left - right,
                "*": lambda: left * right, "/": lambda: left / right,
                "%": lambda: left % right, "<": lambda: left < right,
                ">": lambda: left > right, "<=": lambda: left <= right,
                ">=": lambda: left >= right, "==": lambda: left == right,
                "!=": lambda: left != right, "&&": lambda: bool(left and right),
                "||": lambda: bool(left or right),
            }
            if detail not in operations:
                raise RuntimeErrorInProgram(f"Operator '{detail}' is not executable in this subset.")
            try: return operations[detail]()
            except (ArithmeticError, TypeError) as error:
                raise RuntimeErrorInProgram(str(error)) from error
        if kind == "FunctionCall":
            if detail == "scanf":
                return self._scanf(children)
            values = [self._expr(child) for child in children]
            return self._builtin(detail, values, children)
        raise RuntimeErrorInProgram(f"Expression '{kind}' is not executable in this subset.")

    def _builtin(self, name: str, values: list[Any], arguments: list[dict]) -> Any:
        if name.endswith(".nextInt") and name.rsplit(".", 1)[0] in self._all_names():
            if self.input_index >= len(self.inputs):
                raise RuntimeErrorInProgram("Input ended before Scanner.nextInt() received a value.")
            raw = self.inputs[self.input_index]; self.input_index += 1
            try: return int(raw)
            except ValueError as error: raise RuntimeErrorInProgram(f"'{raw}' is not a valid integer input.") from error
        if name in {"printf", "puts"}:
            if not values: return 0
            fmt = str(values[0])
            if name == "puts":
                self.output.append(fmt + "\n")
            else:
                args = iter(values[1:])
                def replace(match):
                    spec = match.group(0)
                    if spec == "%%": return "%"
                    try: value = next(args)
                    except StopIteration: return spec
                    if spec[-1] in "di": return str(int(value))
                    if spec[-1] in "fFeEgG": return str(float(value))
                    if spec[-1] == "c": return chr(int(value)) if isinstance(value, (int, float)) else str(value)[:1]
                    return str(value)
                self.output.append(re.sub(r"%(?:[-+0-9.#]*)[diuoxXfFeEgGcs%]", replace, fmt))
            return 0
        if name == "std::cout":
            self.output.append("".join(str(value) for value in values))
            return 0
        if name in {"System.out.print", "System.out.println"}:
            self.output.append("".join(str(value) for value in values))
            if name.endswith("println"): self.output.append("\n")
            return 0
        if name == "std::cin":
            for argument in arguments:
                if argument.get("node_type") != "Identifier":
                    raise RuntimeErrorInProgram("cin input targets must be variable names.")
                if self.input_index >= len(self.inputs):
                    raise RuntimeErrorInProgram("Input ended before cin received a value.")
                raw = self.inputs[self.input_index]; self.input_index += 1
                target = str(argument.get("detail"))
                current = self._lookup(target)
                try: value = float(raw) if isinstance(current, float) else int(raw) if isinstance(current, int) else raw
                except ValueError as error: raise RuntimeErrorInProgram(f"'{raw}' is not valid input for '{target}'.") from error
                self._assign(target, value)
            return 0
        short_name = name.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
        if short_name in {"sqrt", "pow", "abs", "max", "min"}:
            functions = {"sqrt": math.sqrt, "pow": math.pow, "abs": abs, "max": max, "min": min}
            try: return functions[short_name](*values)
            except (ValueError, TypeError, OverflowError) as error: raise RuntimeErrorInProgram(str(error)) from error
        function = self.functions.get(name)
        if function is None:
            raise RuntimeErrorInProgram(f"Function '{name}' has no runtime implementation.")
        return self._call(function, values)

    def _scanf(self, arguments: list[dict]) -> int:
        if not arguments or arguments[0].get("node_type") != "StringLiteral":
            raise RuntimeErrorInProgram("scanf needs a format string as its first argument.")
        fmt = self._literal_string(str(arguments[0].get("detail") or ""))
        conversions = [match[-1] for match in re.findall(r"%(?:[-+0-9.#]*)?([diuoxXfFeEgGcs%])", fmt) if match != "%"]
        targets = arguments[1:]
        if len(targets) < len(conversions):
            raise RuntimeErrorInProgram("scanf has fewer destination variables than format conversions.")
        for conversion, target in zip(conversions, targets):
            if self.input_index >= len(self.inputs):
                raise RuntimeErrorInProgram("Input ended before scanf received all values.")
            if target.get("node_type") != "UnaryExpression" or target.get("detail") != "&" or not target.get("children"):
                raise RuntimeErrorInProgram("scanf destinations must use '&variable'.")
            identifier = target["children"][0]
            name = str(identifier.get("detail") or "")
            raw = self.inputs[self.input_index]; self.input_index += 1
            try:
                if conversion in "diuoxX": value = int(raw, 0 if raw.lower().startswith("0x") else 10)
                elif conversion in "fFeEgG": value = float(raw)
                elif conversion == "c": value = raw[0]
                else: value = raw
            except (ValueError, IndexError) as error:
                raise RuntimeErrorInProgram(f"'{raw}' is invalid input for scanf conversion '%{conversion}'.") from error
            self._assign(name, value)
        return len(conversions)

    def _all_names(self) -> set[str]:
        return {name for env in self.environments for name in env}

    def _call(self, function: dict, arguments: list[Any]) -> Any:
        self.call_depth += 1
        if self.call_depth > self.MAX_CALL_DEPTH:
            self.call_depth -= 1
            raise RuntimeErrorInProgram("Maximum function call depth (64) exceeded.")
        env: dict[str, Any] = {}
        parameters = [child for child in function.get("children", []) if child.get("node_type") == "Parameter"]
        if len(parameters) != len(arguments):
            self.call_depth -= 1
            raise RuntimeErrorInProgram(f"Function expects {len(parameters)} argument(s), received {len(arguments)}.")
        for parameter, value in zip(parameters, arguments):
            parts = str(parameter.get("detail") or "").split()
            if len(parts) == 2: env[parts[1]] = value
        self.environments.append(env)
        try:
            for statement in function.get("children", []):
                if statement.get("node_type") != "Parameter": self._statement(statement)
        except _Return as returned:
            return returned.value
        finally:
            self.environments.pop()
            self.call_depth -= 1
        return 0

    def _statement(self, node: dict) -> None:
        self._tick()
        kind = node.get("node_type")
        children = node.get("children", [])
        if kind == "Declaration":
            name = str(children[1].get("detail") or "")
            initial = children[2]["children"][0] if len(children) > 2 and children[2].get("children") else None
            self.environments[-1][name] = self._expr(initial) if initial else 0
        elif kind == "Assignment":
            self._assign(str(children[0].get("detail") or ""), self._expr(children[1]))
        elif kind == "ExpressionStatement" and children:
            self._expr(children[0])
        elif kind == "FunctionCall":
            self._expr(node)
        elif kind == "Return":
            condition = next((item for item in children if item.get("node_type") == "Condition"), None)
            value = self._expr(condition["children"][0]) if condition and condition.get("children") else 0
            raise _Return(value)
        elif kind in {"If", "While", "For"}:
            sections = {item.get("node_type"): item.get("children", []) for item in children}
            if kind == "If":
                condition = bool(self._expr(sections["Condition"][0]))
                branch = sections.get("Body" if condition else "Else", [])
                self._block(branch)
            elif kind == "While":
                while bool(self._expr(sections["Condition"][0])):
                    self._tick(); self._block(sections.get("Body", []))
            else:
                self.environments.append({})
                try:
                    if sections.get("Initializer"): self._statement(sections["Initializer"][0])
                    while not sections.get("Condition") or bool(self._expr(sections["Condition"][0])):
                        self._tick(); self._block(sections.get("Body", []))
                        if sections.get("Update"): self._statement(sections["Update"][0])
                finally:
                    self.environments.pop()
        else:
            raise RuntimeErrorInProgram(f"Statement '{kind}' is not executable in this subset.")

    def _block(self, statements: list[dict]) -> None:
        self.environments.append({})
        try:
            for statement in statements: self._statement(statement)
        finally:
            self.environments.pop()
