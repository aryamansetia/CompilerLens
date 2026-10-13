"""Metadata for all six phases of the CompilerLens pipeline."""

from __future__ import annotations

from typing import Literal

PhaseStatus = Literal["implemented", "planned"]

PIPELINE: list[dict] = [
    {
        "id": "lexical",
        "order": 1,
        "name": "Lexical Analysis",
        "produces": "Tokens",
        "status": "implemented",
        "summary": "Splits source text into tokens such as keywords, identifiers, numbers and operators.",
        "module": "backend/lexer/lexer.py",
    },
    {
        "id": "syntax",
        "order": 2,
        "name": "Syntax Analysis",
        "produces": "Abstract Syntax Tree",
        "status": "implemented",
        "summary": "Checks grammar and builds the AST that captures the program's structure.",
        "module": "backend/parser/parser.py",
    },
    {
        "id": "semantic",
        "order": 3,
        "name": "Semantic Analysis",
        "produces": "Symbol Table + Diagnostics",
        "status": "implemented",
        "summary": "Checks declarations before use, duplicate declarations, initialisation and type compatibility.",
        "module": "backend/pipeline/future_stages.py",
    },
    {
        "id": "intermediate",
        "order": 4,
        "name": "Intermediate Code Generation",
        "produces": "Three-Address Code",
        "status": "implemented",
        "summary": "Translates valid AST expressions into machine-independent three-address instructions.",
        "module": "backend/pipeline/future_stages.py",
    },
    {
        "id": "optimization",
        "order": 5,
        "name": "Optimization",
        "produces": "Optimised IR",
        "status": "implemented",
        "summary": "Applies constant folding, temporary propagation, algebraic simplification, and unused-temporary removal.",
        "module": "backend/pipeline/future_stages.py",
    },
    {
        "id": "codegen",
        "order": 6,
        "name": "Code Generation",
        "produces": "Assembly",
        "status": "implemented",
        "summary": "Translates optimised TAC into readable instructions for CompilerLens' educational register machine.",
        "module": "backend/pipeline/future_stages.py",
    },
]


def get_pipeline(
    lexical_ok: bool | None = None,
    syntax_ok: bool | None = None,
    semantic_ok: bool | None = None,
    intermediate_ok: bool | None = None,
    optimization_ok: bool | None = None,
    codegen_ok: bool | None = None,
) -> list[dict]:
    """Return pipeline metadata annotated with the outcome of the current run.

    ``None`` means the phase did not run, whereas ``False`` means it ran and
    found problems. The stage's build status is independent of run status.
    """
    results = {
        "lexical": lexical_ok,
        "syntax": syntax_ok,
        "semantic": semantic_ok,
        "intermediate": intermediate_ok,
        "optimization": optimization_ok,
        "codegen": codegen_ok,
    }
    annotated: list[dict] = []
    for phase in PIPELINE:
        entry = dict(phase)
        outcome = results.get(phase["id"])
        entry["ran"] = outcome is not None
        entry["ok"] = bool(outcome) if outcome is not None else None
        annotated.append(entry)
    return annotated
