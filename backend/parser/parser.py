"""
Phase 2 of the compiler: Syntax Analysis.

This is a hand-written **recursive descent** parser.  Each grammar rule becomes
one Python method, so the code reads almost exactly like the grammar:

    Program     -> Statement*
    Statement   -> Declaration | Assignment | ExpressionStatement
    Declaration -> Type Identifier ';'
                 | Type Identifier '=' Expression ';'
    Assignment  -> Identifier '=' Expression ';'
    Expression  -> Term (('+' | '-') Term)*
    Term        -> Factor (('*' | '/' | '%') Factor)*
    Factor      -> Number | Identifier | '(' Expression ')' | ('-' | '+') Factor

Precedence falls out of the nesting: Expression calls Term, Term calls Factor,
so `*` binds tighter than `+` without any extra tables.

When a statement is malformed the parser records a clear error, skips to the
next semicolon (this is called *panic-mode recovery*) and carries on, so one
mistake does not hide the rest of the program.
"""

from __future__ import annotations

from lexer.keywords import get_type_keywords, normalise_language
from lexer.token_types import Token, TokenType
from parser.ast_nodes import (
    Assignment,
    ASTNode,
    BinaryExpression,
    BooleanLiteral,
    Declaration,
    ExpressionStatement,
    Identifier,
    NumberLiteral,
    Program,
    UnaryExpression,
    ControlStatement,
    Function,
    FunctionCall,
    StringLiteral,
)
from utils.errors import CompilerError

PHASE_NAME = "Syntax Analysis"

ADDITIVE_OPERATORS = {"+", "-"}
MULTIPLICATIVE_OPERATORS = {"*", "/", "%"}

# Keywords that are valid in the language but outside the grammar we support.
UNSUPPORTED_STATEMENT_KEYWORDS = {
    "do", "switch", "case", "public", "private", "protected", "static", "struct",
    "break", "continue", "import", "namespace", "using", "printf",
}


class _ParseError(Exception):
    """Raised internally to unwind to the statement boundary."""


class Parser:
    """Builds an AST from a token list."""

    def __init__(self, tokens: list[Token], language: str = "c") -> None:
        self.language = normalise_language(language)
        self.type_keywords = set(get_type_keywords(self.language))
        if self.language == "java": self.type_keywords.add("Scanner")

        # UNKNOWN tokens were already reported by the lexer.  Dropping them here
        # stops the same bad character from producing a second, confusing error.
        self.tokens: list[Token] = [t for t in tokens if t.type not in {TokenType.UNKNOWN, TokenType.PREPROCESSOR_DIRECTIVE, TokenType.IMPORT_DIRECTIVE}]
        if not self.tokens or self.tokens[-1].type != TokenType.END_OF_FILE:
            self.tokens.append(Token("", TokenType.END_OF_FILE, 1, 1, len(self.tokens)))

        self.index: int = 0
        self.errors: list[CompilerError] = []

    # ------------------------------------------------------------------
    # Token stream helpers
    # ------------------------------------------------------------------
    def _current(self) -> Token:
        return self.tokens[min(self.index, len(self.tokens) - 1)]

    def _peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.index + offset, len(self.tokens) - 1)]

    def _at_end(self) -> bool:
        return self._current().type == TokenType.END_OF_FILE

    def _advance(self) -> Token:
        token = self._current()
        if not self._at_end():
            self.index += 1
        return token

    def _check(self, token_type: TokenType) -> bool:
        return self._current().type == token_type

    def _check_lexeme(self, *lexemes: str) -> bool:
        return self._current().lexeme in lexemes

    def _match_lexeme(self, lexemes: set[str]) -> Token | None:
        """Consume and return the current token if its text is in `lexemes`."""
        if self._current().lexeme in lexemes and not self._at_end():
            return self._advance()
        return None

    def _describe(self, token: Token) -> str:
        if token.type == TokenType.END_OF_FILE:
            return "end of file"
        return f"'{token.lexeme}'"

    def _error(self, message: str, hint: str = "", token: Token | None = None) -> _ParseError:
        token = token or self._current()
        self.errors.append(
            CompilerError(
                phase=PHASE_NAME,
                message=message,
                line=token.line,
                column=token.column,
                lexeme=token.lexeme,
                hint=hint,
            )
        )
        return _ParseError(message)

    def _expect_semicolon(self, statement_description: str) -> None:
        if self._check(TokenType.SEMICOLON):
            self._advance()
            return
        raise self._error(
            f"Expected ';' after the {statement_description}, but found "
            f"{self._describe(self._current())}.",
            "Every statement in this grammar ends with a semicolon.",
        )

    def _synchronize(self) -> None:
        """Panic-mode recovery: skip ahead until the next statement can start."""
        while not self._at_end():
            if self._check(TokenType.SEMICOLON):
                self._advance()
                return
            if self._current().lexeme in self.type_keywords:
                return
            self._advance()

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------
    def parse(self) -> tuple[Program, list[CompilerError]]:
        """Program -> Statement*"""
        program = Program(statements=[])
        while not self._at_end():
            before = self.index
            try:
                if self.language == "java" and self._current().lexeme == "class":
                    program.statements.extend(self._parse_java_class())
                    statement = None
                elif (self._current().type == TokenType.KEYWORD and self._current().lexeme in self.type_keywords | {"void"}
                        and self._peek().type == TokenType.IDENTIFIER and self._peek(2).type == TokenType.LEFT_PAREN):
                    statement = self._parse_function()
                else:
                    statement = self._parse_statement()
                if statement is not None:
                    program.statements.append(statement)
            except _ParseError:
                self._synchronize()
            # safety net: never loop forever on a token we cannot consume
            if self.index == before:
                self._advance()
        return program, self.errors

    def _parse_java_class(self) -> list[ASTNode]:
        """Parse a simple Java class wrapper and keep its method ASTs."""
        self._advance()  # class
        if not self._check(TokenType.IDENTIFIER):
            raise self._error("Expected a class name after 'class'.")
        self._advance()
        if not self._check(TokenType.LEFT_BRACE):
            raise self._error("Expected '{' after the class name.")
        self._advance()
        methods: list[ASTNode] = []
        while not self._at_end() and not self._check(TokenType.RIGHT_BRACE):
            while self._current().lexeme in {"public", "private", "protected", "static", "final"}:
                self._advance()
            if (self._current().type == TokenType.KEYWORD and self._current().lexeme in self.type_keywords | {"void"}
                    and self._peek().type == TokenType.IDENTIFIER and self._peek(2).type == TokenType.LEFT_PAREN):
                methods.append(self._parse_function())
            else:
                raise self._error("Unsupported Java class member.", "Use simple methods such as 'public static void main()'.")
        if self._check(TokenType.RIGHT_BRACE):
            self._advance()
        else:
            raise self._error("Expected '}' to close the Java class.")
        return methods

    def _parse_statement(self) -> ASTNode | None:
        token = self._current()

        if self.language == "cpp" and token.lexeme == "using" and self._peek().lexeme == "namespace":
            self._advance(); self._advance()
            if self._current().lexeme != "std":
                raise self._error("Only 'using namespace std;' is supported.")
            self._advance()
            self._expect_semicolon("namespace directive")
            return None

        if self.language == "cpp" and (token.lexeme in {"cout", "cin"} or (token.lexeme == "std" and self._peek().lexeme == "::")):
            return self._parse_cpp_stream_output()

        # Declaration: starts with a type keyword such as `int`
        if token.type in {TokenType.KEYWORD, TokenType.IDENTIFIER} and token.lexeme in self.type_keywords:
            return self._parse_declaration()

        if token.lexeme in {"if", "while", "for"}:
            return self._parse_control()
        if token.lexeme == "return":
            start = self._advance()
            value = None if self._check(TokenType.SEMICOLON) else self._parse_expression()
            self._expect_semicolon("return statement")
            return ControlStatement("Return", condition=value, line=start.line, column=start.column)

        # Assignment: IDENTIFIER '='
        if token.type == TokenType.IDENTIFIER and self._peek().lexeme == "=":
            return self._parse_assignment()

        # Blocks and other structures are not in the grammar yet
        if token.type in (TokenType.LEFT_BRACE, TokenType.RIGHT_BRACE):
            raise self._error(
                f"Blocks using {self._describe(token)} are not part of the "
                "supported grammar yet.",
                "The current grammar handles declarations, assignments and expressions.",
            )

        if token.type == TokenType.KEYWORD and token.lexeme in UNSUPPORTED_STATEMENT_KEYWORDS:
            raise self._error(
                f"The keyword '{token.lexeme}' is recognised by the lexer but the "
                "parser does not support this kind of statement yet.",
                "Supported statements include declarations, assignments, conditionals, loops, functions and returns.",
            )

        if token.type == TokenType.SEMICOLON:
            self._advance()          # an empty statement `;` is harmless
            return None

        # Anything else is treated as a bare expression statement
        return self._parse_expression_statement()

    def _parse_cpp_stream_output(self) -> ASTNode:
        start = self._current()
        if self._current().lexeme == "std":
            self._advance()
            if self._current().lexeme == "::": self._advance()
            if self._current().lexeme in {"cout", "cin"}: stream_name = self._advance().lexeme
            else: raise self._error("Expected 'cout' or 'cin' after 'std::'.")
        else: stream_name = self._advance().lexeme
        args: list[ASTNode] = []
        direction = ">>" if stream_name == "cin" else "<<"
        while self._current().lexeme == direction:
            self._advance()
            if stream_name == "cout" and self._current().lexeme == "endl":
                endline = self._advance()
                args.append(StringLiteral("\\n", endline.line, endline.column))
            elif stream_name == "cout" and self._current().lexeme == "std" and self._peek().lexeme == "::" and self._peek(2).lexeme == "endl":
                self._advance(); self._advance(); endline = self._advance()
                args.append(StringLiteral("\\n", endline.line, endline.column))
            else:
                args.append(self._parse_expression())
        if not args:
            raise self._error(f"Expected a value after '{stream_name} {direction}'.")
        self._expect_semicolon(f"{stream_name} stream operation")
        return FunctionCall(f"std::{stream_name}", args, start.line, start.column)

    def _parse_declaration(self) -> Declaration:
        """Declaration -> Type Identifier ';' | Type Identifier '=' Expression ';'"""
        type_token = self._advance()

        if not self._check(TokenType.IDENTIFIER):
            found = self._describe(self._current())
            raise self._error(
                f"Expected an identifier after type '{type_token.lexeme}', but found {found}.",
                f"A declaration looks like: {type_token.lexeme} a = 10;",
            )
        name_token = self._advance()

        initializer: ASTNode | None = None
        if self._check(TokenType.ASSIGNMENT_OPERATOR):
            if self._current().lexeme != "=":
                raise self._error(
                    f"Cannot use '{self._current().lexeme}' when declaring a variable.",
                    "Use a plain '=' to give a new variable its first value.",
                )
            self._advance()
            if self.language == "java" and type_token.lexeme == "Scanner":
                expected = ["new", "Scanner", "(", "System", ".", "in", ")"]
                for lexeme in expected:
                    if self._current().lexeme != lexeme:
                        raise self._error(f"Expected '{lexeme}' in Scanner(System.in) initialization.")
                    self._advance()
                self._expect_semicolon(f"Scanner declaration '{name_token.lexeme}'")
                return Declaration(var_type="Scanner", name=name_token.lexeme, initializer=None,
                                   line=type_token.line, column=type_token.column,
                                   name_line=name_token.line, name_column=name_token.column)
            initializer = self._parse_expression()

        self._expect_semicolon(f"declaration of '{name_token.lexeme}'")
        return Declaration(
            var_type=type_token.lexeme,
            name=name_token.lexeme,
            initializer=initializer,
            line=type_token.line,
            column=type_token.column,
            name_line=name_token.line,
            name_column=name_token.column,
        )

    def _parse_assignment(self) -> Assignment:
        """Assignment -> Identifier '=' Expression ';'"""
        name_token = self._advance()
        self._advance()  # the '=' we already checked for
        value = self._parse_expression()
        self._expect_semicolon(f"assignment to '{name_token.lexeme}'")
        return Assignment(
            name=name_token.lexeme,
            value=value,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_expression_statement(self) -> ExpressionStatement:
        """ExpressionStatement -> Expression ';'"""
        start = self._current()
        expression = self._parse_expression()
        self._expect_semicolon("expression")
        return ExpressionStatement(expression=expression, line=start.line, column=start.column)

    def _parse_expression(self) -> ASTNode:
        """Expression with relational, logical, additive and multiplicative precedence."""
        node = self._parse_term()
        while self._current().type in (TokenType.ARITHMETIC_OPERATOR, TokenType.RELATIONAL_OPERATOR, TokenType.LOGICAL_OPERATOR) and self._check_lexeme("+", "-", "<", ">", "<=", ">=", "==", "!=", "&&", "||"):
            operator = self._advance()
            right = self._parse_term()
            node = BinaryExpression(
                operator=operator.lexeme,
                left=node,
                right=right,
                line=operator.line,
                column=operator.column,
            )
        return node

    def _parse_block(self) -> list[ASTNode]:
        if not self._check(TokenType.LEFT_BRACE):
            item = self._parse_statement()
            return [item] if item else []
        self._advance(); items = []
        while not self._at_end() and not self._check(TokenType.RIGHT_BRACE):
            before = self.index
            try:
                item = self._parse_statement()
                if item: items.append(item)
            except _ParseError:
                self._synchronize()
            if self.index == before: self._advance()
        if self._check(TokenType.RIGHT_BRACE): self._advance()
        else: raise self._error("Expected '}' to close this block.", "Add a matching closing brace.")
        return items

    def _parse_control(self) -> ControlStatement:
        start = self._advance(); kind = start.lexeme.capitalize()
        initializer = condition = update = None
        if start.lexeme == "for":
            self._advance() if self._check(TokenType.LEFT_PAREN) else None
            if not self._check(TokenType.SEMICOLON):
                initializer = self._parse_declaration() if self._current().lexeme in self.type_keywords else self._parse_assignment()
            else: self._advance()
            if not self._check(TokenType.SEMICOLON): condition = self._parse_expression()
            if self._check(TokenType.SEMICOLON): self._advance()
            if not self._check(TokenType.RIGHT_PAREN):
                name = self._advance(); op = self._advance() if self._current().lexeme in {"=", "++", "--", "+=", "-="} else name
                if op.lexeme in {"++", "--"}: update = Assignment(name.lexeme, BinaryExpression(op.lexeme[0], Identifier(name.lexeme), NumberLiteral("1")))
                else: update = Assignment(name.lexeme, self._parse_expression())
            if self._check(TokenType.RIGHT_PAREN): self._advance()
        else:
            if self._check(TokenType.LEFT_PAREN): self._advance()
            condition = self._parse_expression()
            if self._check(TokenType.RIGHT_PAREN): self._advance()
        body = self._parse_block()
        alternate = []
        if start.lexeme == "if" and self._current().lexeme == "else": self._advance(); alternate = self._parse_block()
        return ControlStatement(kind, condition, body, alternate, initializer, update, start.line, start.column)

    def _parse_function(self) -> Function:
        typ = self._advance(); name = self._advance(); self._advance()
        params = []
        while not self._at_end() and not self._check(TokenType.RIGHT_PAREN):
            ptype = self._advance()
            if ptype.lexeme == "void" and self._check(TokenType.RIGHT_PAREN): break
            if self._check(TokenType.IDENTIFIER): params.append((ptype.lexeme, self._advance().lexeme))
            if self._check(TokenType.COMMA): self._advance()
            elif not self._check(TokenType.RIGHT_PAREN): raise self._error("Expected ',' between parameters.")
        if self._check(TokenType.RIGHT_PAREN): self._advance()
        body = self._parse_block()
        return Function(typ.lexeme, name.lexeme, params, body, typ.line, typ.column)

    def _parse_term(self) -> ASTNode:
        """Term -> Factor (('*' | '/' | '%') Factor)*"""
        node = self._parse_factor()
        while self._current().type == TokenType.ARITHMETIC_OPERATOR and self._check_lexeme(*MULTIPLICATIVE_OPERATORS):
            operator = self._advance()
            right = self._parse_factor()
            node = BinaryExpression(
                operator=operator.lexeme,
                left=node,
                right=right,
                line=operator.line,
                column=operator.column,
            )
        return node

    def _parse_factor(self) -> ASTNode:
        """Factor -> Number | Identifier | '(' Expression ')' | ('-' | '+') Factor"""
        token = self._current()

        if token.type == TokenType.NUMBER:
            self._advance()
            return NumberLiteral(value=token.lexeme, line=token.line, column=token.column)

        if token.type == TokenType.STRING_LITERAL:
            self._advance()
            return StringLiteral(token.lexeme, token.line, token.column)

        if token.type == TokenType.KEYWORD and token.lexeme in {"true", "false"}:
            self._advance()
            return BooleanLiteral(value=token.lexeme, line=token.line, column=token.column)

        if token.type == TokenType.IDENTIFIER:
            self._advance()
            qualified_name = token.lexeme
            while self._current().lexeme in {".", "::"} and self._peek().type == TokenType.IDENTIFIER:
                qualified_name += self._advance().lexeme + self._advance().lexeme
            if self._check(TokenType.LEFT_PAREN):
                self._advance()
                arguments = []
                while not self._at_end() and not self._check(TokenType.RIGHT_PAREN):
                    arguments.append(self._parse_expression())
                    if self._check(TokenType.COMMA): self._advance()
                    elif not self._check(TokenType.RIGHT_PAREN): raise self._error("Expected ',' between function arguments.")
                if not self._check(TokenType.RIGHT_PAREN): raise self._error("Expected ')' after function arguments.")
                self._advance()
                return FunctionCall(qualified_name, arguments, token.line, token.column)
            if qualified_name != token.lexeme:
                raise self._error(f"Qualified name '{qualified_name}' must be a supported library call.", "Use a supported function such as std::sqrt(value).", token)
            return Identifier(name=token.lexeme, line=token.line, column=token.column)

        if token.type == TokenType.LEFT_PAREN:
            self._advance()
            inner = self._parse_expression()
            if not self._check(TokenType.RIGHT_PAREN):
                raise self._error(
                    f"Expected ')' to close the bracket opened at line {token.line}, "
                    f"but found {self._describe(self._current())}.",
                    "Every '(' needs a matching ')'.",
                )
            self._advance()
            return inner

        if (token.type == TokenType.ARITHMETIC_OPERATOR and token.lexeme in ("-", "+")) or (self.language in {"c", "cpp"} and token.lexeme == "&"):
            self._advance()
            operand = self._parse_factor()
            return UnaryExpression(
                operator=token.lexeme, operand=operand, line=token.line, column=token.column
            )

        raise self._error(
            f"Expected a number, boolean literal, variable name or '(' here, but found "
            f"{self._describe(token)}.",
            "An expression is built from numbers, boolean literals (C++/Java), variables and the operators + - * / %.",
        )


def parse(tokens: list[Token], language: str = "c") -> tuple[Program, list[CompilerError]]:
    """Convenience wrapper mirroring `lexer.tokenize`."""
    return Parser(tokens, language).parse()
