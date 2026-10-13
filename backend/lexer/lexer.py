"""
Phase 1 of the compiler: Lexical Analysis.

The lexer reads the source program one character at a time and groups those
characters into tokens.  It is a hand-written scanner (no regex engine, no
generator tool) so that every decision it makes is visible and explainable.

Usage:
    lexer = Lexer("int a = 10;", language="c")
    tokens, errors = lexer.tokenize()
"""

from __future__ import annotations

import re

from lexer.keywords import get_keywords, normalise_language
from lexer.token_types import Token, TokenType
from utils.errors import CompilerError

# Operators, longest first.  The scanner always tries the longest match so that
# "==" is read as one token rather than two "=" tokens.
OPERATORS: dict[str, TokenType] = {
    # three characters
    "<<=": TokenType.ASSIGNMENT_OPERATOR,
    ">>=": TokenType.ASSIGNMENT_OPERATOR,
    # two characters
    "==": TokenType.RELATIONAL_OPERATOR,
    "!=": TokenType.RELATIONAL_OPERATOR,
    "<=": TokenType.RELATIONAL_OPERATOR,
    ">=": TokenType.RELATIONAL_OPERATOR,
    "&&": TokenType.LOGICAL_OPERATOR,
    "||": TokenType.LOGICAL_OPERATOR,
    "++": TokenType.ARITHMETIC_OPERATOR,
    "--": TokenType.ARITHMETIC_OPERATOR,
    "+=": TokenType.ASSIGNMENT_OPERATOR,
    "-=": TokenType.ASSIGNMENT_OPERATOR,
    "*=": TokenType.ASSIGNMENT_OPERATOR,
    "/=": TokenType.ASSIGNMENT_OPERATOR,
    "%=": TokenType.ASSIGNMENT_OPERATOR,
    "<<": TokenType.BITWISE_OPERATOR,
    ">>": TokenType.BITWISE_OPERATOR,
    "->": TokenType.OTHER_OPERATOR,
    "::": TokenType.OTHER_OPERATOR,
    # one character
    "=": TokenType.ASSIGNMENT_OPERATOR,
    "+": TokenType.ARITHMETIC_OPERATOR,
    "-": TokenType.ARITHMETIC_OPERATOR,
    "*": TokenType.ARITHMETIC_OPERATOR,
    "/": TokenType.ARITHMETIC_OPERATOR,
    "%": TokenType.ARITHMETIC_OPERATOR,
    "<": TokenType.RELATIONAL_OPERATOR,
    ">": TokenType.RELATIONAL_OPERATOR,
    "!": TokenType.LOGICAL_OPERATOR,
    "&": TokenType.BITWISE_OPERATOR,
    "|": TokenType.BITWISE_OPERATOR,
    "^": TokenType.BITWISE_OPERATOR,
    "~": TokenType.BITWISE_OPERATOR,
    "?": TokenType.OTHER_OPERATOR,
    ":": TokenType.OTHER_OPERATOR,
}

SEPARATORS: dict[str, TokenType] = {
    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,
}

# Suffixes a numeric literal is allowed to end with, e.g. 3.14f or 100L.
NUMBER_SUFFIXES: set[str] = {
    "", "f", "F", "d", "D", "l", "L", "u", "U",
    "ll", "LL", "ul", "UL", "lu", "LU", "f32", "f64",
}

PHASE_NAME = "Lexical Analysis"
SUPPORTED_HEADERS = {"stdio.h", "stdlib.h", "math.h", "string.h", "stdbool.h", "iostream", "cmath", "cstdlib", "cstring", "string", "vector", "algorithm", "cctype", "limits", "sstream", "iomanip", "array", "map", "set", "queue", "stack", "numeric", "utility", "bits/stdc++.h"}


class Lexer:
    """Converts a source string into a list of tokens."""

    def __init__(self, source_code: str, language: str = "c") -> None:
        self.source: str = source_code
        self.language: str = normalise_language(language)
        self.keywords: set[str] = get_keywords(self.language)

        self.index: int = 0      # cursor into self.source
        self.line: int = 1
        self.column: int = 1

        self.tokens: list[Token] = []
        self.errors: list[CompilerError] = []

    # ------------------------------------------------------------------
    # Low-level cursor helpers
    # ------------------------------------------------------------------
    def _at_end(self) -> bool:
        return self.index >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        """Look at a character without consuming it. Returns '' past the end."""
        position = self.index + offset
        if position >= len(self.source):
            return ""
        return self.source[position]

    def _advance(self) -> str:
        """Consume one character and keep the line/column counters correct."""
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _add_token(self, lexeme: str, token_type: TokenType, line: int, column: int) -> None:
        self.tokens.append(
            Token(
                lexeme=lexeme,
                type=token_type,
                line=line,
                column=column,
                position=len(self.tokens),
            )
        )

    def _add_error(self, message: str, line: int, column: int, lexeme: str = "", hint: str = "") -> None:
        self.errors.append(
            CompilerError(
                phase=PHASE_NAME,
                message=message,
                line=line,
                column=column,
                lexeme=lexeme,
                hint=hint,
            )
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def tokenize(self) -> tuple[list[Token], list[CompilerError]]:
        """Scan the whole source and return (tokens, lexical_errors)."""
        while not self._at_end():
            char = self._peek()

            if char == "#":
                self._scan_include()
                continue
            if self.language == "java" and self.source.startswith("import", self.index) and (self.index + 6 == len(self.source) or not (self.source[self.index + 6].isalnum() or self.source[self.index + 6] == "_")):
                self._scan_java_import()
                continue

            # 1. whitespace carries no meaning, throw it away
            if char in " \t\r\n":
                self._advance()
                continue

            # 2. comments are also discarded
            if char == "/" and self._peek(1) == "/":
                self._skip_line_comment()
                continue
            if char == "/" and self._peek(1) == "*":
                self._skip_block_comment()
                continue

            # 3. words: keywords and identifiers
            if char.isalpha() or char == "_":
                self._scan_word()
                continue

            # 4. numbers
            if char.isdigit():
                self._scan_number()
                continue

            # 5. text literals
            if char == '"':
                self._scan_string()
                continue
            if char == "'":
                self._scan_char()
                continue

            # 6. operators (longest match wins)
            if self._scan_operator():
                continue

            # 7. separators and punctuation
            if char in SEPARATORS:
                line, column = self.line, self.column
                self._advance()
                self._add_token(char, SEPARATORS[char], line, column)
                continue

            # 8. anything left over is not valid in this language
            self._scan_invalid_character()

        self._add_token("", TokenType.END_OF_FILE, self.line, self.column)
        return self.tokens, self.errors

    # ------------------------------------------------------------------
    # Individual scanners
    # ------------------------------------------------------------------
    def _scan_include(self) -> None:
        line, column = self.line, self.column
        chars = []
        while not self._at_end() and self._peek() != "\n":
            chars.append(self._advance())
        text = "".join(chars).strip()
        match = re.fullmatch(r'#\s*include\s*[<"]([A-Za-z0-9_./]+)[>"]\s*', text)
        if not match:
            self._add_error("Malformed preprocessor directive.", line, column, text,
                            "Use an include such as #include <stdio.h>.")
            self._add_token(text, TokenType.UNKNOWN, line, column)
            return
        header = match.group(1)
        if header not in SUPPORTED_HEADERS:
            self._add_error(f"Header '{header}' is not in the supported header set.", line, column, text,
                            "Supported headers: stdio.h, stdlib.h, math.h, string.h, stdbool.h, iostream.")
            self._add_token(text, TokenType.UNKNOWN, line, column)
            return
        if self.language == "java":
            self._add_error("C/C++ #include directives are not valid in Java mode.", line, column, text,
                            "Switch the language selector to C or C++.")
            self._add_token(text, TokenType.UNKNOWN, line, column)
            return
        self._add_token(text, TokenType.PREPROCESSOR_DIRECTIVE, line, column)

    def _scan_java_import(self) -> None:
        line, column = self.line, self.column
        chars = []
        while not self._at_end():
            char = self._advance()
            chars.append(char)
            if char == ";":
                break
        text = "".join(chars).strip()
        if not re.fullmatch(r"import\s+(static\s+)?[A-Za-z_$][A-Za-z0-9_$.]*(\.\*)?\s*;", text):
            self._add_error("Malformed Java import declaration.", line, column, text,
                            "Use an import such as import java.util.Scanner;")
            self._add_token(text, TokenType.UNKNOWN, line, column)
            return
        self._add_token(text, TokenType.IMPORT_DIRECTIVE, line, column)

    def _skip_line_comment(self) -> None:
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        start_line, start_column = self.line, self.column
        self._advance()  # '/'
        self._advance()  # '*'
        while not self._at_end():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        self._add_error(
            "Block comment was opened with /* but never closed.",
            start_line,
            start_column,
            "/*",
            "Add */ where the comment should end.",
        )

    def _scan_word(self) -> None:
        """A run of letters, digits and underscores starting with a letter."""
        line, column = self.line, self.column
        chars: list[str] = []
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            chars.append(self._advance())
        lexeme = "".join(chars)

        token_type = TokenType.KEYWORD if lexeme in self.keywords else TokenType.IDENTIFIER
        self._add_token(lexeme, token_type, line, column)

    def _scan_number(self) -> None:
        """Integer or floating point literal, with an optional type suffix."""
        line, column = self.line, self.column
        chars: list[str] = []

        while not self._at_end() and self._peek().isdigit():
            chars.append(self._advance())

        # a decimal point only counts if a digit follows it
        if self._peek() == "." and self._peek(1).isdigit():
            chars.append(self._advance())  # '.'
            while not self._at_end() and self._peek().isdigit():
                chars.append(self._advance())

        # collect any trailing word characters so that "12abc" is reported as
        # one bad number instead of a number followed by an identifier
        suffix_chars: list[str] = []
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            suffix_chars.append(self._advance())
        suffix = "".join(suffix_chars)

        lexeme = "".join(chars) + suffix
        if suffix in NUMBER_SUFFIXES:
            self._add_token(lexeme, TokenType.NUMBER, line, column)
        else:
            self._add_error(
                f"'{lexeme}' is not a valid number. A number cannot be followed by letters.",
                line,
                column,
                lexeme,
                "Identifiers must start with a letter or underscore, for example value1.",
            )
            self._add_token(lexeme, TokenType.UNKNOWN, line, column)

    def _scan_string(self) -> None:
        line, column = self.line, self.column
        chars: list[str] = [self._advance()]  # opening quote
        while not self._at_end() and self._peek() != '"':
            if self._peek() == "\n":
                self._add_error(
                    "String literal is not closed before the end of the line.",
                    line, column, "".join(chars),
                    'Add a closing " on the same line.',
                )
                self._add_token("".join(chars), TokenType.UNKNOWN, line, column)
                return
            if self._peek() == "\\":          # keep escape sequences intact
                chars.append(self._advance())
            if not self._at_end():
                chars.append(self._advance())
        if self._at_end():
            self._add_error(
                "String literal is not closed before the end of the file.",
                line, column, "".join(chars),
                'Add a closing " to finish the string.',
            )
            self._add_token("".join(chars), TokenType.UNKNOWN, line, column)
            return
        chars.append(self._advance())  # closing quote
        self._add_token("".join(chars), TokenType.STRING_LITERAL, line, column)

    def _scan_char(self) -> None:
        line, column = self.line, self.column
        chars: list[str] = [self._advance()]  # opening quote
        while not self._at_end() and self._peek() != "'":
            if self._peek() == "\n":
                break
            if self._peek() == "\\":
                chars.append(self._advance())
            if not self._at_end():
                chars.append(self._advance())
        if self._peek() != "'":
            self._add_error(
                "Character literal is not closed.",
                line, column, "".join(chars),
                "A character literal looks like 'a'.",
            )
            self._add_token("".join(chars), TokenType.UNKNOWN, line, column)
            return
        chars.append(self._advance())  # closing quote
        self._add_token("".join(chars), TokenType.CHAR_LITERAL, line, column)

    def _scan_operator(self) -> bool:
        """Try a 3, then 2, then 1 character operator. Returns True on success."""
        for length in (3, 2, 1):
            candidate = self.source[self.index:self.index + length]
            if candidate in OPERATORS:
                line, column = self.line, self.column
                for _ in range(length):
                    self._advance()
                self._add_token(candidate, OPERATORS[candidate], line, column)
                return True
        return False

    def _scan_invalid_character(self) -> None:
        line, column = self.line, self.column
        char = self._advance()

        if char == "#":
            message = "Preprocessor directives such as #include are not supported yet."
            hint = "Remove the # line for now; CompilerLens analyses plain statements."
        elif char in "@$`":
            message = f"'{char}' is not a valid character in {self.language.upper()} source code."
            hint = "Remove this character."
        else:
            message = f"Unexpected character '{char}' in the source program."
            hint = "Check for typos or characters copied from a word processor."

        self._add_error(message, line, column, char, hint)
        self._add_token(char, TokenType.UNKNOWN, line, column)


def tokenize(source_code: str, language: str = "c") -> tuple[list[Token], list[CompilerError]]:
    """Convenience wrapper so callers do not have to build a Lexer by hand."""
    return Lexer(source_code, language).tokenize()
