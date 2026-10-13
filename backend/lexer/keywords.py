"""
Language tables: which words are keywords, and which words name a type.

Keeping this in its own file means adding a new language later is a data change,
not a code change.
"""

from __future__ import annotations

# Words reserved by each language.  Anything that looks like a word but is not
# in this set becomes an IDENTIFIER instead.
C_KEYWORDS: set[str] = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if", "int",
    "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile",
    "while",
}

CPP_KEYWORDS: set[str] = C_KEYWORDS | {
    "bool", "catch", "class", "delete", "false", "friend", "inline",
    "namespace", "new", "operator", "private", "protected", "public",
    "template", "this", "throw", "true", "try", "using", "virtual",
}

JAVA_KEYWORDS: set[str] = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null",
}

KEYWORDS_BY_LANGUAGE: dict[str, set[str]] = {
    "c": C_KEYWORDS,
    "cpp": CPP_KEYWORDS,
    "java": JAVA_KEYWORDS,
}

# The subset of keywords the *parser* currently accepts at the start of a
# declaration.  The educational grammar only handles simple scalar types.
TYPE_KEYWORDS_BY_LANGUAGE: dict[str, set[str]] = {
    "c": {"int", "float", "double", "char", "long", "short"},
    "cpp": {"int", "float", "double", "char", "long", "short", "bool"},
    "java": {"int", "float", "double", "char", "long", "short", "boolean"},
}

SUPPORTED_LANGUAGES: tuple[str, ...] = ("c", "cpp", "java")

LANGUAGE_LABELS: dict[str, str] = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}


def normalise_language(language: str | None) -> str:
    """Accept friendly spellings like 'C++' or 'JAVA' and return our key."""
    if not language:
        return "c"
    cleaned = language.strip().lower()
    aliases = {"c++": "cpp", "cplusplus": "cpp", "cpp": "cpp", "c": "c", "java": "java"}
    return aliases.get(cleaned, "c")


def get_keywords(language: str) -> set[str]:
    return KEYWORDS_BY_LANGUAGE[normalise_language(language)]


def get_type_keywords(language: str) -> set[str]:
    return TYPE_KEYWORDS_BY_LANGUAGE[normalise_language(language)]
