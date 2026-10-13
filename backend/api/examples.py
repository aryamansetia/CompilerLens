"""
Ready-made programs that the user can load with one click.

The first one is the demonstration program: it exercises declarations, an
arithmetic expression and produces a tree that fits on screen.
"""

from __future__ import annotations

EXAMPLES: list[dict] = [
    {
        "id": "basic-declarations",
        "title": "Declarations and addition",
        "description": "The main demonstration program. Three declarations, one of them an expression.",
        "language": "c",
        "source_code": "int a = 10;\nint b = 20;\nint c = a + b;\n",
    },
    {
        "id": "operator-precedence",
        "title": "Operator precedence",
        "description": "Shows that * binds tighter than +, and how brackets change the tree.",
        "language": "c",
        "source_code": "int x = 2 + 3 * 4;\nint y = (2 + 3) * 4;\n",
    },
    {
        "id": "assignment-and-reuse",
        "title": "Assignment to an existing variable",
        "description": "A declaration followed by an assignment that reads the variable it writes.",
        "language": "c",
        "source_code": "int a = 10;\na = a + 5;\nfloat average = a / 2;\n",
    },
    {
        "id": "syntax-error",
        "title": "Syntax error: missing identifier",
        "description": "Demonstrates a precise parser error instead of a generic failure message.",
        "language": "c",
        "source_code": "int = 10;\nint b = 20;\n",
    },
    {
        "id": "lexical-error",
        "title": "Lexical error: invalid character",
        "description": "Demonstrates the lexer catching a character that cannot appear in the language.",
        "language": "c",
        "source_code": "int a = 10;\nint b@ = 5;\nint c = 12abc;\n",
    },
    {
        "id": "semantic-undeclared",
        "title": "Semantic error: undeclared variable",
        "description": "Shows semantic analysis catching a variable that was never declared.",
        "language": "c",
        "source_code": "int total = price + 5;\n",
    },
    {
        "id": "semantic-duplicate",
        "title": "Semantic error: duplicate declaration",
        "description": "Shows the symbol table preventing the same variable from being declared twice.",
        "language": "c",
        "source_code": "int score = 10;\nint score = 20;\n",
    },
    {
        "id": "java-sample",
        "title": "Java types",
        "description": "The same grammar analysed with Java's keyword table.",
        "language": "java",
        "source_code": "int count = 5;\ndouble rate = 2.5;\nint total = count * 3;\n",
    },
    {
        "id": "cpp-booleans",
        "title": "C++ boolean types",
        "description": "Demonstrates bool symbols and true/false literals in semantic analysis and TAC.",
        "language": "cpp",
        "source_code": "bool ready = true;\nbool finished = false;\n",
    },
    {
        "id": "java-booleans",
        "title": "Java boolean types",
        "description": "Demonstrates boolean symbols and true/false literals in Java.",
        "language": "java",
        "source_code": "boolean active = true;\nboolean done = false;\n",
    },
]
