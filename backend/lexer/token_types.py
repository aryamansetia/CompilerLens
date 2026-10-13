"""
Token type definitions for CompilerLens.

A *token* is the smallest meaningful unit of a program, the way a word is the
smallest meaningful unit of a sentence.  The lexer's only job is to turn a flat
stream of characters into a list of these tokens.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class TokenType(str, Enum):
    """Every category of token the lexer can produce."""

    # --- words ---------------------------------------------------------
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"

    # --- literals ------------------------------------------------------
    NUMBER = "NUMBER"
    STRING_LITERAL = "STRING_LITERAL"
    CHAR_LITERAL = "CHAR_LITERAL"
    PREPROCESSOR_DIRECTIVE = "PREPROCESSOR_DIRECTIVE"
    IMPORT_DIRECTIVE = "IMPORT_DIRECTIVE"

    # --- operators -----------------------------------------------------
    ASSIGNMENT_OPERATOR = "ASSIGNMENT_OPERATOR"
    ARITHMETIC_OPERATOR = "ARITHMETIC_OPERATOR"
    RELATIONAL_OPERATOR = "RELATIONAL_OPERATOR"
    LOGICAL_OPERATOR = "LOGICAL_OPERATOR"
    BITWISE_OPERATOR = "BITWISE_OPERATOR"
    OTHER_OPERATOR = "OTHER_OPERATOR"

    # --- separators / punctuation ---------------------------------------
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"
    DOT = "DOT"
    LEFT_PAREN = "LEFT_PAREN"
    RIGHT_PAREN = "RIGHT_PAREN"
    LEFT_BRACE = "LEFT_BRACE"
    RIGHT_BRACE = "RIGHT_BRACE"
    LEFT_BRACKET = "LEFT_BRACKET"
    RIGHT_BRACKET = "RIGHT_BRACKET"

    # --- special ---------------------------------------------------------
    UNKNOWN = "UNKNOWN"
    END_OF_FILE = "END_OF_FILE"


#: Broad groups used by the UI to colour-code the token table.
TOKEN_CATEGORIES: dict[TokenType, str] = {
    TokenType.KEYWORD: "keyword",
    TokenType.IDENTIFIER: "identifier",
    TokenType.NUMBER: "literal",
    TokenType.STRING_LITERAL: "literal",
    TokenType.CHAR_LITERAL: "literal",
    TokenType.PREPROCESSOR_DIRECTIVE: "directive",
    TokenType.IMPORT_DIRECTIVE: "directive",
    TokenType.ASSIGNMENT_OPERATOR: "operator",
    TokenType.ARITHMETIC_OPERATOR: "operator",
    TokenType.RELATIONAL_OPERATOR: "operator",
    TokenType.LOGICAL_OPERATOR: "operator",
    TokenType.BITWISE_OPERATOR: "operator",
    TokenType.OTHER_OPERATOR: "operator",
    TokenType.SEMICOLON: "separator",
    TokenType.COMMA: "separator",
    TokenType.DOT: "separator",
    TokenType.LEFT_PAREN: "separator",
    TokenType.RIGHT_PAREN: "separator",
    TokenType.LEFT_BRACE: "separator",
    TokenType.RIGHT_BRACE: "separator",
    TokenType.LEFT_BRACKET: "separator",
    TokenType.RIGHT_BRACKET: "separator",
    TokenType.UNKNOWN: "invalid",
    TokenType.END_OF_FILE: "eof",
}


@dataclass
class Token:
    """One token produced by the lexer."""

    lexeme: str          # the exact text that was matched, e.g. "int"
    type: TokenType      # its category, e.g. TokenType.KEYWORD
    line: int            # 1-based line number in the source
    column: int          # 1-based column where the lexeme starts
    position: int        # index of this token inside the token stream

    @property
    def category(self) -> str:
        """Coarse group used for colour-coding in the frontend."""
        return TOKEN_CATEGORIES.get(self.type, "other")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["type"] = self.type.value
        data["category"] = self.category
        return data

    def __repr__(self) -> str:  # makes terminal debugging readable
        return f"<{self.type.value} {self.lexeme!r} @ {self.line}:{self.column}>"
