"""Compiler phases after syntax analysis.

This module implements semantic analysis, three-address code generation,
optimisation, and educational target pseudo-assembly. The later stages consume
serialised AST or TAC data so their contracts remain easy to inspect in the API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from decimal import Decimal, InvalidOperation
import re

from utils.errors import CompilerError


class CompilerStage(ABC):
    """Common contract for the compiler's later stages."""

    name: str = "Unnamed stage"
    phase_id: str = ""

    @abstractmethod
    def run(self, ast: dict, **context: Any) -> dict:
        """Take the previous stage's output and produce this stage's output."""

    def is_implemented(self) -> bool:
        """Return whether the stage has working logic."""
        return self.phase_id in {"semantic", "intermediate", "optimization", "codegen"}


_NUMERIC_TYPES = {"char", "short", "int", "long", "float", "double"}
_TYPE_RANK = {"char": 0, "short": 1, "int": 2, "long": 3, "float": 4, "double": 5}


def _literal_type(value: str) -> str:
    """Infer a practical educational type for the lexer's numeric literal text."""
    text = value.strip()
    lowered = text.lower()
    if lowered.endswith(("f", "f32")):
        return "float"
    if lowered.endswith(("d", "f64")) or "." in text or "e" in lowered:
        return "double"
    if lowered.endswith(("l", "ll", "ul", "lu")):
        return "long"
    return "int"


class SemanticAnalyzer(CompilerStage):
    """Build a symbol table and report declaration, use, and type errors.

    Supported checks match CompilerLens' grammar: declaration before use,
    duplicate declarations, reads before initialisation, arithmetic operand
    types, and assignment/initialisation compatibility. The grammar currently
    Function and block scopes support lexical lookup and inner shadowing.
    """

    name = "Semantic Analysis"
    phase_id = "semantic"

    def __init__(self) -> None:
        self.scopes: list[dict[str, Any]] = []
        self.symbol_table: list[dict[str, Any]] = []
        self.errors: list[CompilerError] = []
        self.language = "c"
        self.functions: dict[str, dict[str, Any]] = {}
        self.headers: set[str] = set()

    def run(self, ast: dict, **context: Any) -> dict:
        self.scopes = [{"name": "global", "symbols": {}}]
        self.symbol_table = []
        self.errors = []
        self.functions = {}
        self.language = str(context.get("language", "c")).strip().lower().replace("c++", "cpp")
        self.headers = set(context.get("headers", []))
        if ast and ast.get("node_type") == "Program":
            for statement in ast.get("children", []):
                if statement.get("node_type") == "Function":
                    parts = str(statement.get("detail") or "").split(maxsplit=1)
                    if len(parts) == 2:
                        params = [str(child.get("detail") or "").split() for child in statement.get("children", []) if child.get("node_type") == "Parameter"]
                        self.functions[parts[1]] = {"return_type": parts[0], "parameters": params}
            for statement in ast.get("children", []):
                self._analyse_statement(statement)
        return {
            "symbol_table": self.symbol_table,
            "errors": [error.to_dict() for error in self.errors],
            "success": not self.errors,
        }

    def _error(self, node: dict, message: str, hint: str, lexeme: str = "") -> None:
        self.errors.append(
            CompilerError(
                phase=self.name,
                message=message,
                line=int(node.get("line") or 1),
                column=int(node.get("column") or 1),
                lexeme=lexeme,
                hint=hint,
            )
        )

    def _lookup(self, name: str) -> dict[str, Any] | None:
        for scope in reversed(self.scopes):
            if name in scope["symbols"]:
                return scope["symbols"][name]
        return None

    def _push_scope(self, name: str) -> None:
        parent = self.scopes[-1]["name"] if self.scopes else "global"
        self.scopes.append({"name": f"{parent}/{name}", "symbols": {}})

    def _pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    @staticmethod
    def _declaration_parts(node: dict) -> tuple[str, str, dict | None]:
        children = node.get("children", [])
        var_type = str(children[0].get("detail") or "unknown") if children else "unknown"
        name = str(children[1].get("detail") or "") if len(children) > 1 else ""
        initializer = None
        if len(children) > 2 and children[2].get("children"):
            initializer = children[2]["children"][0]
        return var_type, name, initializer

    def _analyse_statement(self, node: dict) -> None:
        node_type = node.get("node_type")
        children = node.get("children", [])

        if node_type == "Declaration":
            var_type, name, initializer = self._declaration_parts(node)
            identifier_node = children[1] if len(children) > 1 else node
            if not name:
                return
            current_scope = self.scopes[-1]
            if name in current_scope["symbols"]:
                first = current_scope["symbols"][name]
                self._error(
                    identifier_node,
                    f"Variable '{name}' has already been declared on line {first['line'] }.",
                    "Choose a different variable name or assign a new value to the existing variable.",
                    name,
                )
                # Analyse the initializer too, so independent problems are visible.
                if initializer is not None:
                    self._infer_expression(initializer)
                return

            symbol = {
                "name": name,
                "type": var_type,
                "scope": current_scope["name"],
                "line": int(identifier_node.get("line") or node.get("line") or 1),
                "column": int(identifier_node.get("column") or node.get("column") or 1),
                "initialised": var_type == "Scanner" and self.language == "java",
            }
            current_scope["symbols"][name] = symbol
            self.symbol_table.append(symbol)
            if initializer is not None:
                # Only mark the variable initialised if its initial expression
                # was semantically valid. This keeps the symbol table honest
                # when the RHS uses an undeclared/uninitialised variable or
                # has an incompatible type.
                errors_before = len(self.errors)
                value_type = self._infer_expression(initializer)
                if value_type is not None:
                    self._check_assignment_compatibility(var_type, value_type, identifier_node, name, "initialise")
                symbol["initialised"] = len(self.errors) == errors_before
            return

        if node_type == "Assignment":
            identifier_node = children[0] if children else node
            name = str(identifier_node.get("detail") or "")
            symbol = self._lookup(name)
            was_initialised = bool(symbol and symbol.get("initialised"))
            value_node = children[1] if len(children) > 1 else {}
            errors_before = len(self.errors)
            value_type = self._infer_expression(value_node)
            if symbol is None:
                self._error(
                    identifier_node,
                    f"Variable '{name}' is assigned before it is declared.",
                    f"Declare '{name}' with a type such as int or double before assigning to it.",
                    name,
                )
            else:
                if value_type is not None:
                    self._check_assignment_compatibility(symbol["type"], value_type, identifier_node, name, "assign")
                # A failed reassignment does not erase a value from a prior
                # valid initialisation; it only fails to establish a new one.
                symbol["initialised"] = True if len(self.errors) == errors_before else was_initialised
            return

        if node_type == "ExpressionStatement" and children:
            self._infer_expression(children[0])
            return

        if node_type == "FunctionCall":
            self._infer_expression(node)
            return

        if node_type in {"If", "While", "For", "Return", "Function"}:
            # Function parameters and block-local scope are introduced as symbols;
            # control conditions and nested statements are checked recursively.
            if node_type == "Function":
                self._push_scope(f"function {str(node.get('detail') or '').split()[-1]}")
                for child in children:
                    if child.get("node_type") == "Parameter":
                        parts = str(child.get("detail") or "").split()
                        if len(parts) == 2:
                            symbol = {"name": parts[1], "type": parts[0], "scope": self.scopes[-1]["name"], "line": int(child.get("line") or node.get("line") or 1), "column": 1, "initialised": True}
                            if parts[1] in self.scopes[-1]["symbols"]:
                                self._error(child, f"Parameter '{parts[1]}' is declared more than once.", "Give each function parameter a unique name.", parts[1])
                            else:
                                self.scopes[-1]["symbols"][parts[1]] = symbol
                                self.symbol_table.append(symbol)
                    else:
                        self._analyse_statement(child)
                self._pop_scope()
                return
            if node_type == "For":
                self._push_scope("for")
            for section in children:
                section_type = section.get("node_type")
                if section_type in {"Condition", "Initializer", "Update"}:
                    for nested in section.get("children", []): self._analyse_statement(nested) if nested.get("node_type") in {"Declaration", "Assignment"} else self._infer_expression(nested)
                elif section_type in {"Body", "Else"}:
                    self._push_scope(section_type.lower())
                    for nested in section.get("children", []): self._analyse_statement(nested)
                    self._pop_scope()
            if node_type == "For":
                self._pop_scope()

    def _infer_expression(self, node: dict) -> str | None:
        node_type = node.get("node_type")
        detail = str(node.get("detail") or "")
        children = node.get("children", [])

        if node_type == "NumberLiteral":
            return _literal_type(detail)

        if node_type == "BooleanLiteral":
            return "bool" if self.language == "cpp" else "boolean"

        if node_type == "StringLiteral":
            return "string"

        if node_type == "FunctionCall":
            signature = self.functions.get(detail)
            if detail == "scanf" and self.language in {"c", "cpp"}:
                if "stdio.h" not in self.headers:
                    self._error(node, "'scanf' requires #include <stdio.h>.", "Add #include <stdio.h> before reading input.", detail)
                if not children or children[0].get("node_type") != "StringLiteral":
                    self._error(node, "'scanf' expects a format string as its first argument.", "Use a format such as scanf(\"%d\", &value).", detail)
                for target in children[1:]:
                    address = target.get("children", [])
                    if target.get("node_type") != "UnaryExpression" or target.get("detail") != "&" or not address or address[0].get("node_type") != "Identifier":
                        self._error(target, "scanf destinations must use '&variable'.", "Pass the address of each declared variable.")
                        continue
                    symbol = self._lookup(str(address[0].get("detail") or ""))
                    if symbol is None:
                        self._error(target, f"Variable '{address[0].get('detail')}' is read into before it is declared.", "Declare the destination variable before scanf.")
                    else:
                        symbol["initialised"] = True
                return "int"
            if self.language == "java" and detail.endswith(".nextInt"):
                receiver_name = detail.rsplit(".", 1)[0]
                receiver = self._lookup(receiver_name)
                if receiver is None or receiver.get("type") != "Scanner":
                    self._error(node, f"'{detail}' must be called on a declared Scanner variable.", "Create a Scanner with new Scanner(System.in).", detail)
                    return None
                if children:
                    self._error(node, "Scanner.nextInt() does not take arguments.", "Call it with empty parentheses.", detail)
                return "int"
            if detail == "std::cin" and self.language == "cpp":
                if "iostream" not in self.headers and "bits/stdc++.h" not in self.headers:
                    self._error(node, "'std::cin' requires #include <iostream>.", "Add #include <iostream> before reading input.", detail)
                for target in children:
                    if target.get("node_type") != "Identifier":
                        self._error(target, "cin input targets must be variable names.", "Use a declared variable after the >> operator.")
                        continue
                    symbol = self._lookup(str(target.get("detail") or ""))
                    if symbol is None:
                        self._error(target, f"Variable '{target.get('detail')}' is read into before it is declared.", "Declare the input variable before using cin.", str(target.get("detail") or ""))
                    else:
                        symbol["initialised"] = True
                return "void"
            argument_types = [self._infer_expression(child) for child in children]
            is_output_builtin = (
                (detail in {"printf", "puts"} and self.language in {"c", "cpp"})
                or (detail == "std::cout" and self.language == "cpp")
                or (detail in {"System.out.print", "System.out.println"} and self.language == "java")
            )
            if is_output_builtin:
                required = "iostream" if detail == "std::cout" else "stdio.h" if detail in {"printf", "puts"} else ""
                if required and required not in self.headers and not (required == "iostream" and "bits/stdc++.h" in self.headers):
                    self._error(node, f"'{detail}' requires #include <{required}>.", f"Add #include <{required}> at the top of the source file.", detail)
                if not children or children[0].get("node_type") != "StringLiteral":
                    if detail not in {"std::cout", "std::cin"}:
                        self._error(node, f"'{detail}' expects a string literal as its first argument.", "Pass a string literal as the first output value.", detail)
                if detail == "std::cin" or (self.language == "java" and detail.startswith("System.out.")):
                    return "void"
                return "int"
            math_name = detail.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
            if math_name in {"abs", "sqrt", "pow", "max", "min"} and (detail.startswith("std::") or detail.startswith("Math.") or detail == math_name):
                if self.language == "cpp" and not (self.headers & {"cmath", "math.h", "bits/stdc++.h"}):
                    self._error(node, f"'{detail}' requires #include <cmath>.", "Add #include <cmath> before using standard math functions.", detail)
                if math_name in {"sqrt", "pow"}: return "double"
                return argument_types[0] if argument_types and argument_types[0] else "int"
            if signature is None:
                self._error(node, f"Function '{detail}' is called but has no definition.", "Define the function before compiling the program.", detail)
                return None
            params = signature["parameters"]
            if len(params) != len(children):
                self._error(node, f"Function '{detail}' expects {len(params)} argument(s), but received {len(children)}.", "Pass one value for each function parameter.", detail)
            for index, (actual, parameter) in enumerate(zip(argument_types, params)):
                if len(parameter) == 2 and actual is not None:
                    self._check_assignment_compatibility(parameter[0], actual, children[index], parameter[1], "assign")
            return str(signature["return_type"])

        if node_type == "Identifier":
            symbol = self._lookup(detail)
            if symbol is None:
                self._error(
                    node,
                    f"Variable '{detail}' is used before it is declared.",
                    f"Declare '{detail}' before using it in an expression.",
                    detail,
                )
                return None
            if not symbol["initialised"]:
                self._error(
                    node,
                    f"Variable '{detail}' may be used before it is initialised.",
                    f"Give '{detail}' an initial value or assign to it before reading it.",
                    detail,
                )
            return str(symbol["type"])

        if node_type == "UnaryExpression" and children:
            operand_type = self._infer_expression(children[0])
            if operand_type is not None and operand_type not in _NUMERIC_TYPES:
                self._error(
                    node,
                    f"Unary operator '{detail}' cannot be applied to type '{operand_type}'.",
                    "Use a numeric value with unary + or -.",
                    detail,
                )
                return None
            return "int" if operand_type in {"char", "short"} else operand_type

        if node_type == "BinaryExpression" and len(children) >= 2:
            left_type = self._infer_expression(children[0])
            right_type = self._infer_expression(children[1])
            if detail in {"<", ">", "<=", ">=", "==", "!=", "&&", "||"}:
                return "boolean" if self.language == "java" else "bool"
            for operand_type, operand_node in ((left_type, children[0]), (right_type, children[1])):
                if operand_type is not None and operand_type not in _NUMERIC_TYPES:
                    self._error(
                        operand_node,
                        f"Arithmetic operator '{detail}' cannot be applied to type '{operand_type}'.",
                        "Both sides of an arithmetic expression must be numeric.",
                        str(operand_node.get("detail") or ""),
                    )
            if left_type is None or right_type is None:
                return None
            if left_type not in _NUMERIC_TYPES or right_type not in _NUMERIC_TYPES:
                return None
            return self._promote(left_type, right_type)

        # Nodes not part of the current expression grammar are intentionally
        # left unsupported rather than being assigned a guessed type.
        return None

    @staticmethod
    def _promote(left_type: str, right_type: str) -> str:
        left = "int" if left_type in {"char", "short"} else left_type
        right = "int" if right_type in {"char", "short"} else right_type
        return max((left, right), key=lambda type_name: _TYPE_RANK.get(type_name, -1))

    def _check_assignment_compatibility(
        self, target_type: str, value_type: str, node: dict, name: str, action: str
    ) -> None:
        # Numeric widening is allowed; narrowing conversions are reported as a
        # semantic error to keep type checking clear in this learning tool.
        if target_type == value_type:
            return
        if target_type in _TYPE_RANK and value_type in _TYPE_RANK:
            if _TYPE_RANK[value_type] <= _TYPE_RANK[target_type]:
                return
        action_word = "initialise" if action == "initialise" else "assign to"
        self._error(
            node,
            f"Cannot {action_word} variable '{name}' of type '{target_type}' with a value of type '{value_type}'.",
            "Use compatible types or explicitly change the variable's declared type.",
            name,
        )


class IntermediateCodeGenerator(CompilerStage):
    """Translate the supported AST into three-address code (TAC)."""

    name = "Intermediate Code Generation"
    phase_id = "intermediate"

    def __init__(self) -> None:
        self.instructions: list[dict[str, Any]] = []
        self.temp_counter = 0
        self.label_counter = 0

    def run(self, ast: dict, **context: Any) -> dict:
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0
        if ast and ast.get("node_type") == "Program":
            for statement in ast.get("children", []):
                self._generate_statement(statement)
        lines = [instruction["instruction"] for instruction in self.instructions]
        return {
            "instructions": self.instructions,
            "text": "\n".join(lines),
            "instruction_count": len(self.instructions),
            "temporary_count": self.temp_counter,
        }

    def _new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def _emit(
        self,
        instruction: str,
        node: dict,
        result: str,
        operator: str,
        arg1: str,
        arg2: str | None = None,
    ) -> None:
        self.instructions.append(
            {
                "index": len(self.instructions) + 1,
                "instruction": instruction,
                "result": result,
                "operator": operator,
                "arg1": arg1,
                "arg2": arg2,
                "line": int(node.get("line") or 1),
            }
        )

    def _generate_statement(self, node: dict) -> None:
        node_type = node.get("node_type")
        children = node.get("children", [])
        if node_type == "Declaration":
            name = str(children[1].get("detail") or "") if len(children) > 1 else ""
            initializer = children[2]["children"][0] if len(children) > 2 and children[2].get("children") else None
            if name and initializer is not None:
                source = self._generate_expression(initializer)
                self._emit(f"{name} = {source}", node, name, "=", source)
        elif node_type == "Assignment" and len(children) >= 2:
            name = str(children[0].get("detail") or "")
            source = self._generate_expression(children[1])
            self._emit(f"{name} = {source}", node, name, "=", source)
        elif node_type == "ExpressionStatement" and children:
            self._generate_expression(children[0])
        elif node_type == "FunctionCall":
            self._generate_expression(node)
        elif node_type == "Function":
            signature = str(node.get("detail", "")).split(maxsplit=1)
            self._control(f"func {node.get('detail', '')}", node, "func", signature[-1] if signature else "")
            for child in children:
                if child.get("node_type") != "Parameter": self._generate_statement(child)
            self._control("endfunc", node, "endfunc")
        elif node_type in {"If", "While", "For"}:
            self._generate_control(node)
        elif node_type == "Return":
            value = self._generate_expression(children[0]["children"][0]) if children and children[0].get("children") else ""
            self._control(f"return {value}".rstrip(), node, "return", value)

    def _control(self, text: str, node: dict, operator: str, arg1: str = "", arg2: str | None = None) -> None:
        self.instructions.append({"index": len(self.instructions)+1, "instruction": text, "result": "", "operator": operator, "arg1": arg1, "arg2": arg2, "line": int(node.get("line") or 1)})

    def _generate_control(self, node: dict) -> None:
        sections = {child.get("node_type"): child.get("children", []) for child in node.get("children", [])}
        kind = node.get("node_type")
        if kind == "For" and sections.get("Initializer"): self._generate_statement(sections["Initializer"][0])
        start = f"L{self.label_counter+1}"; end = f"L{self.label_counter+2}"; alt = f"L{self.label_counter+3}"
        self.label_counter += 3
        if kind in {"While", "For"}: self._control(f"label {start}", node, "label", start)
        condition = sections.get("Condition", [])
        test = self._generate_expression(condition[0]) if condition else "true"
        self._control(f"ifFalse {test} goto {end if kind != 'If' else alt}", node, "ifFalse", test, end if kind != "If" else alt)
        for statement in sections.get("Body", []): self._generate_statement(statement)
        if kind in {"While", "For"}:
            if kind == "For" and sections.get("Update"): self._generate_statement(sections["Update"][0])
            self._control(f"goto {start}", node, "goto", start)
            self._control(f"label {end}", node, "label", end)
        elif sections.get("Else"):
            self._control(f"goto {end}", node, "goto", end)
            self._control(f"label {alt}", node, "label", alt)
            for statement in sections["Else"]: self._generate_statement(statement)
            self._control(f"label {end}", node, "label", end)
        else: self._control(f"label {alt}", node, "label", alt)

    def _generate_expression(self, node: dict) -> str:
        node_type = node.get("node_type")
        detail = str(node.get("detail") or "")
        children = node.get("children", [])

        if node_type in {"NumberLiteral", "BooleanLiteral", "Identifier"}:
            return detail
        if node_type == "StringLiteral":
            return detail
        if node_type == "FunctionCall":
            if detail == "scanf":
                for target in children[1:]:
                    address = target.get("children", [])
                    name = str(address[0].get("detail") or "") if address else ""
                    self._control(f"read {name}", node, "read", name)
                return "0"
            arguments = [self._generate_expression(child) for child in children]
            if detail in {"printf", "puts", "std::cout", "System.out.print", "System.out.println"}:
                for argument in arguments:
                    self._control(f"param {argument}", node, "param", argument)
                self._control(f"{detail} {len(arguments)}", node, "print", detail, str(len(arguments)))
                return "0" if detail in {"printf", "puts", "std::cout"} else ""
            if detail == "std::cin":
                for argument in arguments:
                    self._control(f"read {argument}", node, "read", argument)
                return ""
            math_name = detail.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
            if math_name in {"abs", "sqrt", "pow", "max", "min"} and (detail.startswith("std::") or detail.startswith("Math.") or detail == math_name):
                for argument in arguments:
                    self._control(f"param {argument}", node, "param", argument)
                temp = self._new_temp()
                self._control(f"{temp} = libcall {detail}, {len(arguments)}", node, "libcall", detail, str(len(arguments)))
                self.instructions[-1]["result"] = temp
                return temp
            for argument in arguments:
                self._control(f"param {argument}", node, "param", argument)
            temp = self._new_temp()
            self._control(f"{temp} = call {detail}, {len(arguments)}", node, "call", detail, str(len(arguments)))
            self.instructions[-1]["result"] = temp
            return temp
        if node_type == "UnaryExpression" and children:
            operand = self._generate_expression(children[0])
            temp = self._new_temp()
            instruction = f"{temp} = {detail}{operand}"
            self._emit(instruction, node, temp, f"u{detail}", operand)
            return temp
        if node_type == "BinaryExpression" and len(children) >= 2:
            left = self._generate_expression(children[0])
            right = self._generate_expression(children[1])
            temp = self._new_temp()
            instruction = f"{temp} = {left} {detail} {right}"
            self._emit(instruction, node, temp, detail, left, right)
            return temp
        return detail


_TEMP_RE = re.compile(r"^t\d+$")
_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fFdD]?$")


def _is_temp(value: Any) -> bool:
    return bool(_TEMP_RE.fullmatch(str(value or "")))


def _is_number(value: Any) -> bool:
    return bool(_NUMERIC_RE.fullmatch(str(value or "").strip()))


def _decimal(value: str) -> Decimal | None:
    text = str(value).strip()
    if not _is_number(text):
        return None
    if text[-1:] in {"f", "F", "d", "D"}:
        text = text[:-1]
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


class Optimizer(CompilerStage):
    """Optimise TAC with educational, local IR transformations.

    Implemented passes: constant folding for literal-only arithmetic, temporary
    constant propagation, algebraic identities, and removal of unused temporary
    assignments. Named source variables are deliberately not globally replaced
    with constants; this keeps the intermediate representation easy to inspect.
    """

    name = "Optimization"
    phase_id = "optimization"

    def run(self, ast: dict | None = None, **context: Any) -> dict:
        source_instructions = [dict(item) for item in context.get("instructions", [])]
        constants: dict[str, str] = {}
        aliases: dict[str, str] = {}
        optimizations: list[str] = []
        transformed: list[dict[str, Any]] = []

        def resolve(operand: Any) -> str:
            text = str(operand if operand is not None else "")
            # Propagate only compiler temporaries. Never replace a named source
            # variable with its initializer, because it may be reassigned later.
            seen: set[str] = set()
            while _is_temp(text) and text not in seen:
                seen.add(text)
                if text in constants:
                    text = constants[text]
                elif text in aliases:
                    text = aliases[text]
                else:
                    break
            return text

        for original in source_instructions:
            item = dict(original)
            if item.get("operator") in {"label", "goto", "ifFalse", "return", "func", "endfunc", "param", "call", "print", "libcall", "read"}:
                transformed.append(item)
                continue
            old_text = str(item.get("instruction", ""))
            op = str(item.get("operator", "="))
            result = str(item.get("result", ""))
            arg1 = resolve(item.get("arg1", ""))
            arg2 = resolve(item.get("arg2", "")) if item.get("arg2") is not None else None

            replacement_reason = ""
            if op == "=" or op.startswith("u"):
                # Unary TAC is stored as u+ / u- and uses arg1 as its operand.
                if op in {"u+", "u-"} and _is_number(arg1):
                    number = _decimal(arg1)
                    if number is not None:
                        folded = _format_decimal(number if op == "u+" else -number)
                        item.update(operator="=", arg1=folded, arg2=None)
                        replacement_reason = "folded unary literal"
                else:
                    item.update(arg1=arg1, arg2=arg2)
            else:
                left_num = _decimal(arg1)
                right_num = _decimal(arg2) if arg2 is not None else None
                folded: str | None = None
                if left_num is not None and right_num is not None:
                    try:
                        if op == "+": folded = _format_decimal(left_num + right_num)
                        elif op == "-": folded = _format_decimal(left_num - right_num)
                        elif op == "*": folded = _format_decimal(left_num * right_num)
                        elif op == "%" and left_num == left_num.to_integral_value() and right_num == right_num.to_integral_value() and right_num != 0:
                            folded = str(int(left_num) % int(right_num))
                    except (ArithmeticError, ValueError):
                        folded = None
                if folded is not None:
                    item.update(operator="=", arg1=folded, arg2=None)
                    replacement_reason = "constant folding"
                else:
                    # Simple algebraic identities; avoid division by zero rules.
                    simplified: str | None = None
                    if op == "+" and right_num == 0: simplified = arg1
                    elif op == "+" and left_num == 0: simplified = str(arg2)
                    elif op == "-" and right_num == 0: simplified = arg1
                    elif op == "*" and right_num == 1: simplified = arg1
                    elif op == "*" and left_num == 1: simplified = str(arg2)
                    elif op == "*" and (left_num == 0 or right_num == 0): simplified = "0"
                    elif op == "/" and right_num == 1: simplified = arg1
                    if simplified is not None:
                        item.update(operator="=", arg1=simplified, arg2=None)
                        replacement_reason = "algebraic simplification"
                    else:
                        item.update(arg1=arg1, arg2=arg2)

            if item.get("operator") == "=":
                item["instruction"] = f"{item['result']} = {item['arg1']}"
            elif item.get("operator") in {"u+", "u-"}:
                unary_symbol = "+" if item["operator"] == "u+" else "-"
                item["instruction"] = f"{item['result']} = {unary_symbol}{item['arg1']}"
            else:
                item["instruction"] = f"{item['result']} = {item['arg1']} {item['operator']} {item['arg2']}"
            if item["instruction"] != old_text:
                if replacement_reason:
                    optimizations.append(f"{replacement_reason.capitalize()}: {old_text}  →  {item['instruction']}")
                else:
                    optimizations.append(f"Temporary propagation: {old_text}  →  {item['instruction']}")

            if _is_temp(result):
                constants.pop(result, None)
                aliases.pop(result, None)
                if item.get("operator") == "=" and (_is_number(item.get("arg1")) or str(item.get("arg1")) in {"true", "false"}):
                    constants[result] = str(item["arg1"])
                elif item.get("operator") == "=" and item.get("arg1") is not None:
                    aliases[result] = str(item["arg1"])
            else:
                # A new definition of a source variable invalidates any older
                # temp copy aliases that would otherwise incorrectly read it.
                aliases = {temp: alias for temp, alias in aliases.items() if alias != result}
            transformed.append(item)

        # Repeatedly remove temporary assignments whose results are not used.
        # The source subset has no I/O or control-flow statements, so temp-only
        # assignments have no observable side effect.
        kept = transformed
        while True:
            used_temps: set[str] = set()
            for item in kept:
                for key in ("arg1", "arg2"):
                    value = item.get(key)
                    if _is_temp(value):
                        used_temps.add(str(value))
            next_kept = [item for item in kept if not (_is_temp(item.get("result")) and item.get("result") not in used_temps)]
            removed = [item for item in kept if item not in next_kept]
            if not removed:
                break
            for item in removed:
                optimizations.append(f"Removed unused temporary: {item['instruction']}")
            kept = next_kept

        final_instructions: list[dict[str, Any]] = []
        for index, item in enumerate(kept, start=1):
            final = dict(item)
            final["index"] = index
            final_instructions.append(final)

        return {
            "instructions": final_instructions,
            "text": "\n".join(item["instruction"] for item in final_instructions),
            "original_instruction_count": len(source_instructions),
            "optimized_instruction_count": len(final_instructions),
            "removed_instruction_count": max(0, len(source_instructions) - len(final_instructions)),
            "optimizations": optimizations,
            "success": True,
        }


class CodeGenerator(CompilerStage):
    """Generate readable pseudo-assembly from optimised TAC.

    The output targets a tiny educational register machine and is intentionally
    not advertised as native x86/ARM assembly or a directly executable binary.
    """

    name = "Code Generation"
    phase_id = "codegen"
    TARGET = "CompilerLens educational register machine"

    def run(self, ast: dict | None = None, **context: Any) -> dict:
        instructions = context.get("instructions", [])
        output = [
            "; CompilerLens educational pseudo-assembly",
            "; Target: simple register machine (illustrative, not native executable assembly)",
        ]
        emitted_count = 0

        def load_operand(operand: Any) -> str:
            text = str(operand if operand is not None else "")
            if _is_number(text) or text in {"true", "false"}:
                output.append(f"MOV R0, #{text}")
            else:
                output.append(f"LOAD R0, [{text}]")
            return text

        opcode = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
                  "<": "CMP_LT", ">": "CMP_GT", "<=": "CMP_LE", ">=": "CMP_GE",
                  "==": "CMP_EQ", "!=": "CMP_NE", "&&": "AND", "||": "OR"}
        for item in instructions:
            operator = str(item.get("operator", "="))
            result = str(item.get("result", "result"))
            arg1 = str(item.get("arg1", ""))
            arg2 = item.get("arg2")
            if operator in {"label", "goto", "ifFalse", "return", "func", "endfunc", "param", "call", "print", "libcall", "read"}:
                if operator == "call":
                    output.append(f"CALL {arg1}, {arg2 or 0}")
                    output.append(f"STORE [{result}], R0")
                    emitted_count += 2
                    continue
                if operator == "print":
                    output.append(f"PRINT {arg1}, {arg2 or 0} ARGUMENT(S)")
                    emitted_count += 1
                    continue
                if operator == "libcall":
                    output.append(f"LIBCALL {arg1}, {arg2 or 0}")
                    output.append(f"STORE [{result}], R0")
                    emitted_count += 2
                    continue
                if operator == "read":
                    output.append(f"READ [{arg1}]")
                    emitted_count += 1
                    continue
                output.append(f"{operator.upper()} {item.get('arg1', '')} {item.get('arg2') or ''}".rstrip())
                emitted_count += 1
                continue
            if operator == "=":
                load_operand(arg1)
                output.append(f"STORE [{result}], R0")
                emitted_count += 2
            elif operator in {"u+", "u-"}:
                load_operand(arg1)
                if operator == "u-":
                    output.append("NEG R0")
                    emitted_count += 1
                output.append(f"STORE [{result}], R0")
                emitted_count += 1
            elif operator in opcode and arg2 is not None:
                load_operand(arg1)
                arg2_text = str(arg2)
                if _is_number(arg2_text) or arg2_text in {"true", "false"}:
                    output.append(f"{opcode[operator]} R0, #{arg2_text}")
                else:
                    output.append(f"{opcode[operator]} R0, [{arg2_text}]")
                output.append(f"STORE [{result}], R0")
                emitted_count += 3
            else:
                output.append(f"; Unsupported TAC instruction skipped: {item.get('instruction', '')}")

        return {
            "target": self.TARGET,
            "instructions": output,
            "text": "\n".join(output),
            "instruction_count": emitted_count,
            "success": True,
            "note": "Educational pseudo-assembly for learning only; it is not a native executable binary.",
        }


FUTURE_STAGES: dict[str, type[CompilerStage]] = {
    "semantic": SemanticAnalyzer,
    "intermediate": IntermediateCodeGenerator,
    "optimization": Optimizer,
    "codegen": CodeGenerator,
}
