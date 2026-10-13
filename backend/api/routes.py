"""
HTTP endpoints for CompilerLens.

The routing layer is deliberately thin: it validates input, calls the lexer and
the parser, and packs the results into a Pydantic response.  All of the actual
compiler logic lives in `lexer/` and `parser/`.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException

from api.examples import EXAMPLES
from lexer.keywords import (
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    get_keywords,
    get_type_keywords,
)
from lexer.lexer import Lexer
from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExampleModel,
    HealthModel,
    LanguageModel,
    PhaseModel,
    RunRequest,
    RunResponse,
    StatisticsModel,
)
from parser.parser import Parser
from pipeline.future_stages import (
    CodeGenerator, IntermediateCodeGenerator, Optimizer, SemanticAnalyzer,
)
from pipeline.phases import PIPELINE, get_pipeline
from interpreter import Interpreter, RuntimeErrorInProgram
from utils.ast_printer import count_nodes, render_ast, tree_depth

router = APIRouter(prefix="/api", tags=["compiler"])

VERSION = "0.7.0"  # all six educational phases implemented for the supported grammar


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Run the implemented compiler phases on a source program",
)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run all six educational compiler phases when all preceding checks pass.

    Returns tokens, AST, symbol table, source TAC, optimised TAC, educational
    pseudo-assembly, and every diagnostic tagged with the phase that produced it.
    """
    try:
        # ---- Phase 1: Lexical Analysis --------------------------------
        lexer = Lexer(request.source_code, request.language)
        tokens, lexical_errors = lexer.tokenize()

        # ---- Phase 2: Syntax Analysis ---------------------------------
        parser = Parser(tokens, request.language)
        program, syntax_errors = parser.parse()
    except RecursionError:
        raise HTTPException(
            status_code=400,
            detail="The expression is nested too deeply for this educational parser.",
        )

    ast_dict = program.to_dict()

    # Later stages only consume a syntactically valid program. This avoids
    # misleading semantic diagnostics derived from a partially recovered AST.
    semantic_result = None
    intermediate_result = None
    optimization_result = None
    codegen_result = None
    if not lexical_errors and not syntax_errors:
        included_headers = [
            token.lexeme.split("<")[-1].split(">")[0].split('"')[0]
            for token in tokens if token.type.value == "PREPROCESSOR_DIRECTIVE"
        ]
        semantic_result = SemanticAnalyzer().run(ast_dict, language=request.language, headers=included_headers)
        if semantic_result["success"]:
            intermediate_result = IntermediateCodeGenerator().run(ast_dict, language=request.language)
            optimization_result = Optimizer().run(
                ast_dict,
                instructions=intermediate_result["instructions"],
                language=request.language,
            )
            codegen_result = CodeGenerator().run(
                ast_dict,
                instructions=optimization_result["instructions"],
                language=request.language,
            )

    semantic_errors = semantic_result["errors"] if semantic_result else []
    symbol_table = semantic_result["symbol_table"] if semantic_result else []
    intermediate_code = intermediate_result["instructions"] if intermediate_result else []
    intermediate_code_text = intermediate_result["text"] if intermediate_result else ""
    optimized_code = optimization_result["instructions"] if optimization_result else []
    optimized_code_text = optimization_result["text"] if optimization_result else ""

    # Tokens shown in the table exclude the end-of-file marker, which is an
    # internal convenience rather than something the student wrote.
    visible_tokens = [t.to_dict() for t in tokens if t.type.value != "END_OF_FILE"]

    statistics = StatisticsModel(
        line_count=len(request.source_code.splitlines()),
        character_count=len(request.source_code),
        token_count=len(visible_tokens),
        ast_node_count=count_nodes(ast_dict),
        ast_depth=tree_depth(ast_dict),
        tokens_by_category=dict(Counter(t["category"] for t in visible_tokens)),
    )

    phases = [
        PhaseModel(**phase)
        for phase in get_pipeline(
            lexical_ok=not lexical_errors,
            syntax_ok=not syntax_errors,
            semantic_ok=(not semantic_errors) if semantic_result is not None else None,
            intermediate_ok=True if intermediate_result is not None else None,
            optimization_ok=True if optimization_result is not None else None,
            codegen_ok=True if codegen_result is not None else None,
        )
    ]

    return AnalyzeResponse(
        success=not lexical_errors and not syntax_errors and not semantic_errors,
        language=request.language,
        source_code=request.source_code,
        tokens=visible_tokens,
        ast=ast_dict,
        ast_text=render_ast(ast_dict),
        lexical_errors=[error.to_dict() for error in lexical_errors],
        syntax_errors=[error.to_dict() for error in syntax_errors],
        semantic_errors=semantic_errors,
        symbol_table=symbol_table,
        intermediate_code=intermediate_code,
        intermediate_code_text=intermediate_code_text,
        intermediate_instruction_count=(intermediate_result["instruction_count"] if intermediate_result else 0),
        temporary_count=(intermediate_result["temporary_count"] if intermediate_result else 0),
        optimized_code=optimized_code,
        optimized_code_text=optimized_code_text,
        optimization_notes=(optimization_result["optimizations"] if optimization_result else []),
        optimized_instruction_count=(optimization_result["optimized_instruction_count"] if optimization_result else 0),
        target_code=(codegen_result["instructions"] if codegen_result else []),
        target_code_text=(codegen_result["text"] if codegen_result else ""),
        target_instruction_count=(codegen_result["instruction_count"] if codegen_result else 0),
        target_name=(codegen_result["target"] if codegen_result else ""),
        target_code_note=(codegen_result["note"] if codegen_result else ""),
        phases=phases,
        statistics=statistics,
    )


@router.post("/run", response_model=RunResponse, summary="Execute a program in the bounded educational interpreter")
def run_program(request: RunRequest) -> RunResponse:
    """Interpret the supported AST subset without invoking a system compiler."""
    analysis = analyze(AnalyzeRequest(source_code=request.source_code, language=request.language))
    if not analysis.success:
        errors = analysis.lexical_errors + analysis.syntax_errors + analysis.semantic_errors
        return RunResponse(
            success=False,
            stderr="\n".join(f"{error.phase}, line {error.line}: {error.message}" for error in errors),
        )
    try:
        result = Interpreter(request.stdin).run(analysis.ast.model_dump())
        return RunResponse(success=True, stdout=result["stdout"], steps=result["steps"])
    except RuntimeErrorInProgram as error:
        return RunResponse(success=False, stderr=str(error))
    except RecursionError:
        return RunResponse(success=False, stderr="Execution stopped because the call stack became too deep.")


@router.get("/examples", response_model=list[ExampleModel], summary="Ready-made demo programs")
def list_examples() -> list[ExampleModel]:
    return [ExampleModel(**example) for example in EXAMPLES]


@router.get("/languages", response_model=list[LanguageModel], summary="Languages the lexer knows")
def list_languages() -> list[LanguageModel]:
    return [
        LanguageModel(
            id=language,
            label=LANGUAGE_LABELS[language],
            keyword_count=len(get_keywords(language)),
            supported_types=sorted(get_type_keywords(language)),
        )
        for language in SUPPORTED_LANGUAGES
    ]


@router.get("/pipeline", response_model=list[PhaseModel], summary="All compiler phases and their status")
def describe_pipeline() -> list[PhaseModel]:
    """Used by the UI to draw the pipeline strip before any code is analysed."""
    return [PhaseModel(**phase, ran=False, ok=None) for phase in PIPELINE]


@router.get("/health", response_model=HealthModel, summary="Service health check")
def health() -> HealthModel:
    return HealthModel(
        status="ok",
        service="CompilerLens API",
        version=VERSION,
        implemented_phases=[p["name"] for p in PIPELINE if p["status"] == "implemented"],
    )
