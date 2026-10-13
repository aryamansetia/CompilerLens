"""
Pydantic models that define the shape of every API request and response.

Declaring them here gives three things for free:
  * validation of incoming requests,
  * a guaranteed response shape for the frontend,
  * automatic interactive documentation at /docs.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from lexer.keywords import SUPPORTED_LANGUAGES

Language = Literal["c", "cpp", "java"]


# ----------------------------------------------------------------------
# Request
# ----------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    """Body of POST /api/analyze."""

    source_code: str = Field(
        ...,
        description="The program to analyse.",
        examples=["int a = 10;\nint b = 20;\nint c = a + b;"],
    )
    language: str = Field(
        default="c",
        description="One of: c, cpp, java.",
        examples=["c"],
    )

    @field_validator("source_code")
    @classmethod
    def source_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_code cannot be empty.")
        if len(value) > 20_000:
            raise ValueError("source_code is too large for this educational tool (limit 20,000 characters).")
        return value

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, value: str) -> str:
        cleaned = value.strip().lower().replace("c++", "cpp")
        if cleaned not in SUPPORTED_LANGUAGES:
            raise ValueError(f"language must be one of: {', '.join(SUPPORTED_LANGUAGES)}")
        return cleaned


class RunRequest(AnalyzeRequest):
    """Input for the bounded educational interpreter."""
    stdin: str = Field(default="", description="Whitespace-separated input values for supported input operations.")

    @field_validator("stdin")
    @classmethod
    def stdin_must_be_bounded(cls, value: str) -> str:
        if len(value) > 20_000:
            raise ValueError("stdin is too large for this educational tool (limit 20,000 characters).")
        return value


# ----------------------------------------------------------------------
# Response pieces
# ----------------------------------------------------------------------
class TokenModel(BaseModel):
    """One row of the token table."""

    lexeme: str
    type: str
    category: str
    line: int
    column: int
    position: int


class CompilerErrorModel(BaseModel):
    """One diagnostic message from any phase."""

    phase: str
    message: str
    line: int
    column: int
    lexeme: str = ""
    hint: str = ""


class ASTNodeModel(BaseModel):
    """One node of the abstract syntax tree. Nests recursively via `children`."""

    node_type: str
    label: str
    detail: Optional[str] = None
    line: int = 0
    column: int = 0
    children: list["ASTNodeModel"] = Field(default_factory=list)


ASTNodeModel.model_rebuild()  # resolves the self-reference above


class PhaseModel(BaseModel):
    """One stage of the compiler pipeline, implemented or planned."""

    id: str
    order: int
    name: str
    produces: str
    status: Literal["implemented", "planned"]
    summary: str
    module: str
    ran: bool = False
    ok: Optional[bool] = None


class SemanticSymbolModel(BaseModel):
    """One entry in the semantic analyser's symbol table."""

    name: str
    type: str
    scope: str = "global"
    line: int
    column: int = 1
    initialised: bool = False


class IntermediateInstructionModel(BaseModel):
    """One three-address-code instruction, with operands for inspection."""

    index: int
    instruction: str
    result: str
    operator: str
    arg1: str
    arg2: Optional[str] = None
    line: int = 1


class StatisticsModel(BaseModel):
    """Small numbers shown in the summary bar."""

    line_count: int
    character_count: int
    token_count: int
    ast_node_count: int
    ast_depth: int
    tokens_by_category: dict[str, int]


# ----------------------------------------------------------------------
# Response
# ----------------------------------------------------------------------
class AnalyzeResponse(BaseModel):
    """Body of the response to POST /api/analyze."""

    success: bool = Field(description="True when lexical, syntax, and semantic analysis report no errors.")
    language: str
    source_code: str

    tokens: list[TokenModel]
    ast: Optional[ASTNodeModel] = None
    ast_text: str = ""

    lexical_errors: list[CompilerErrorModel] = Field(default_factory=list)
    syntax_errors: list[CompilerErrorModel] = Field(default_factory=list)
    semantic_errors: list[CompilerErrorModel] = Field(default_factory=list)

    symbol_table: list[SemanticSymbolModel] = Field(default_factory=list)
    intermediate_code: list[IntermediateInstructionModel] = Field(default_factory=list)
    intermediate_code_text: str = ""
    intermediate_instruction_count: int = 0
    temporary_count: int = 0

    optimized_code: list[IntermediateInstructionModel] = Field(default_factory=list)
    optimized_code_text: str = ""
    optimization_notes: list[str] = Field(default_factory=list)
    optimized_instruction_count: int = 0

    target_code: list[str] = Field(default_factory=list)
    target_code_text: str = ""
    target_instruction_count: int = 0
    target_name: str = ""
    target_code_note: str = ""

    phases: list[PhaseModel] = Field(default_factory=list)
    statistics: Optional[StatisticsModel] = None


class RunResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    steps: int = 0


class ExampleModel(BaseModel):
    """A ready-made program the user can load with one click."""

    id: str
    title: str
    description: str
    language: str
    source_code: str


class LanguageModel(BaseModel):
    id: str
    label: str
    keyword_count: int
    supported_types: list[str]


class HealthModel(BaseModel):
    status: str
    service: str
    version: str
    implemented_phases: list[str]
