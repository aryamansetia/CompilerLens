"""
A single, shared shape for every error the compiler reports.

Both the lexer and the parser produce `CompilerError` objects, so the frontend
only ever has to understand one format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class CompilerError:
    """One problem found in the source program."""

    phase: str            # "Lexical Analysis" or "Syntax Analysis"
    message: str          # plain-English description of what went wrong
    line: int             # where it happened
    column: int
    lexeme: str = ""      # the offending text, if there is one
    hint: str = ""        # a suggestion for how to fix it

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"[{self.phase}] line {self.line}, column {self.column}: {self.message}"
