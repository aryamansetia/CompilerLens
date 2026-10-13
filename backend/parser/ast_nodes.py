"""
Abstract Syntax Tree node definitions.

The AST is the parser's output: a tree that keeps the *structure* of the program
and throws away noise such as semicolons and parentheses.  Every node knows how
to turn itself into a plain dictionary, which is what the frontend draws.

The dictionary shape is deliberately uniform:

    {
      "node_type": "Declaration",   # what kind of node this is
      "label":     "Declaration",   # what to print in the tree
      "detail":    "int",           # optional extra shown next to the label
      "line":      1,
      "column":    1,
      "children":  [ ... ]          # nested nodes
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ASTNode:
    """Base class for every node in the tree."""

    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:  # pragma: no cover - overridden by subclasses
        raise NotImplementedError

    @staticmethod
    def _node(
        node_type: str,
        label: str,
        detail: str | None = None,
        line: int = 0,
        column: int = 0,
        children: list[dict] | None = None,
    ) -> dict:
        return {
            "node_type": node_type,
            "label": label,
            "detail": detail,
            "line": line,
            "column": column,
            "children": children or [],
        }


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------
@dataclass
class NumberLiteral(ASTNode):
    """A numeric constant such as 10 or 3.14."""

    value: str
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node("NumberLiteral", "Number", self.value, self.line, self.column)


@dataclass
class StringLiteral(ASTNode):
    value: str
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node("StringLiteral", "String", self.value, self.line, self.column)


@dataclass
class Identifier(ASTNode):
    """A name that refers to a variable, such as `a`."""

    name: str
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node("Identifier", "Identifier", self.name, self.line, self.column)


@dataclass
class BooleanLiteral(ASTNode):
    """A boolean constant (`true` or `false`) in C++/Java examples."""

    value: str
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node("BooleanLiteral", "Boolean", self.value, self.line, self.column)


@dataclass
class FunctionCall(ASTNode):
    name: str
    arguments: list[ASTNode] = field(default_factory=list)
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node("FunctionCall", "FunctionCall", self.name, self.line, self.column,
                          [argument.to_dict() for argument in self.arguments])


@dataclass
class BinaryExpression(ASTNode):
    """Two operands joined by an operator, such as `a + 5`."""

    operator: str
    left: ASTNode
    right: ASTNode
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node(
            "BinaryExpression",
            "BinaryExpression",
            self.operator,
            self.line,
            self.column,
            [self.left.to_dict(), self.right.to_dict()],
        )


@dataclass
class UnaryExpression(ASTNode):
    """A single operand with a prefix operator, such as `-5`."""

    operator: str
    operand: ASTNode
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node(
            "UnaryExpression",
            "UnaryExpression",
            self.operator,
            self.line,
            self.column,
            [self.operand.to_dict()],
        )


# ----------------------------------------------------------------------
# Statements
# ----------------------------------------------------------------------
@dataclass
class Declaration(ASTNode):
    """`int a;` or `int a = 10;`"""

    var_type: str
    name: str
    initializer: ASTNode | None = None
    line: int = 0
    column: int = 0
    name_line: int = 0
    name_column: int = 0

    def to_dict(self) -> dict:
        children = [
            self._node("Type", "Type", self.var_type, self.line, self.column),
            self._node(
                "Identifier", "Identifier", self.name,
                self.name_line or self.line, self.name_column or self.column,
            ),
        ]
        if self.initializer is not None:
            children.append(
                self._node(
                    "Value", "Value", None, self.line, self.column,
                    [self.initializer.to_dict()],
                )
            )
        return self._node("Declaration", "Declaration", None, self.line, self.column, children)


@dataclass
class Assignment(ASTNode):
    """`a = a + 5;`"""

    name: str
    value: ASTNode
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node(
            "Assignment", "Assignment", None, self.line, self.column,
            [
                self._node("Identifier", "Identifier", self.name, self.line, self.column),
                self.value.to_dict(),
            ],
        )


@dataclass
class ExpressionStatement(ASTNode):
    """An expression used as a statement, such as `a + b;`"""

    expression: ASTNode
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        return self._node(
            "ExpressionStatement", "ExpressionStatement", None, self.line, self.column,
            [self.expression.to_dict()],
        )


@dataclass
class Program(ASTNode):
    """The root of the tree: a list of statements."""

    statements: list[ASTNode] = field(default_factory=list)
    line: int = 1
    column: int = 1

    def to_dict(self) -> dict:
        count = len(self.statements)
        detail = f"{count} statement{'s' if count != 1 else ''}"
        return self._node(
            "Program", "Program", detail, self.line, self.column,
            [statement.to_dict() for statement in self.statements],
        )


@dataclass
class ControlStatement(ASTNode):
    """Structured control-flow node; children are condition/body sections."""
    kind: str
    condition: ASTNode | None = None
    body: list[ASTNode] = field(default_factory=list)
    alternate: list[ASTNode] = field(default_factory=list)
    initializer: ASTNode | None = None
    update: ASTNode | None = None
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        children = []
        if self.initializer: children.append(self._node("Initializer", "Initializer", children=[self.initializer.to_dict()]))
        if self.condition: children.append(self._node("Condition", "Condition", children=[self.condition.to_dict()]))
        if self.update: children.append(self._node("Update", "Update", children=[self.update.to_dict()]))
        children.append(self._node("Body", "Body", children=[item.to_dict() for item in self.body]))
        if self.alternate: children.append(self._node("Else", "Else", children=[item.to_dict() for item in self.alternate]))
        return self._node(self.kind, self.kind, None, self.line, self.column, children)


@dataclass
class Function(ASTNode):
    return_type: str
    name: str
    parameters: list[tuple[str, str]] = field(default_factory=list)
    body: list[ASTNode] = field(default_factory=list)
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict:
        children = [self._node("Parameter", "Parameter", f"{typ} {name}") for typ, name in self.parameters]
        children.extend(item.to_dict() for item in self.body)
        return self._node("Function", "Function", f"{self.return_type} {self.name}", self.line, self.column, children)
