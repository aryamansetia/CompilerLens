"""
Tests for the implemented compiler phases.

Run from the `backend` directory:

    python3 -m tests.test_compiler        # no extra packages needed
    pytest                                # if you have pytest installed
"""

from __future__ import annotations

from lexer.lexer import Lexer
from lexer.token_types import TokenType
from parser.parser import Parser
from utils.ast_printer import render_ast


def analyse(source: str, language: str = "c"):
    tokens, lexical_errors = Lexer(source, language).tokenize()
    program, syntax_errors = Parser(tokens, language).parse()
    return tokens, lexical_errors, program, syntax_errors


# ----------------------------------------------------------------------
# Lexer
# ----------------------------------------------------------------------
def test_lexer_classifies_a_simple_declaration():
    tokens, errors, _, _ = analyse("int a = 10;")
    kinds = [(t.lexeme, t.type) for t in tokens if t.type != TokenType.END_OF_FILE]
    assert kinds == [
        ("int", TokenType.KEYWORD),
        ("a", TokenType.IDENTIFIER),
        ("=", TokenType.ASSIGNMENT_OPERATOR),
        ("10", TokenType.NUMBER),
        (";", TokenType.SEMICOLON),
    ]
    assert errors == []


def test_lexer_records_line_and_column():
    tokens, _, _, _ = analyse("int a = 10;\na = a + 5;")
    second_line = [t for t in tokens if t.line == 2]
    assert second_line[0].lexeme == "a"
    assert second_line[0].column == 1


def test_lexer_matches_longest_operator():
    tokens, _, _, _ = analyse("a == b;")
    assert tokens[1].lexeme == "=="
    assert tokens[1].type == TokenType.RELATIONAL_OPERATOR


def test_lexer_skips_comments():
    tokens, errors, _, _ = analyse("int a = 1; // note\n/* block */ int b = 2;")
    assert errors == []
    assert [t.lexeme for t in tokens if t.type == TokenType.IDENTIFIER] == ["a", "b"]


def test_lexer_reports_invalid_character():
    _, errors, _, _ = analyse("int a@ = 5;")
    assert len(errors) == 1
    assert errors[0].line == 1 and errors[0].column == 6
    assert "@" in errors[0].message


def test_lexer_reports_malformed_number():
    _, errors, _, _ = analyse("int a = 12abc;")
    assert any("not a valid number" in error.message for error in errors)


def test_lexer_uses_the_selected_language_keywords():
    tokens, _, _, _ = analyse("boolean flag;", language="java")
    assert tokens[0].type == TokenType.KEYWORD
    tokens_c, _, _, _ = analyse("boolean flag;", language="c")
    assert tokens_c[0].type == TokenType.IDENTIFIER


# ----------------------------------------------------------------------
# Parser and AST
# ----------------------------------------------------------------------
def test_parser_builds_declaration_tree():
    _, _, program, errors = analyse("int a = 10;")
    assert errors == []
    tree = program.to_dict()
    declaration = tree["children"][0]
    assert declaration["node_type"] == "Declaration"
    labels = [(c["label"], c["detail"]) for c in declaration["children"]]
    assert labels[0] == ("Type", "int")
    assert labels[1] == ("Identifier", "a")
    assert declaration["children"][2]["children"][0]["detail"] == "10"


def test_parser_builds_binary_expression():
    _, _, program, errors = analyse("a = a + 5;")
    assert errors == []
    assignment = program.to_dict()["children"][0]
    expression = assignment["children"][1]
    assert expression["node_type"] == "BinaryExpression"
    assert expression["detail"] == "+"


def test_multiplication_binds_tighter_than_addition():
    _, _, program, _ = analyse("int x = 2 + 3 * 4;")
    value = program.to_dict()["children"][0]["children"][2]["children"][0]
    assert value["detail"] == "+"                     # '+' is the root
    assert value["children"][1]["detail"] == "*"      # '*' sits below it


def test_brackets_override_precedence():
    _, _, program, _ = analyse("int y = (2 + 3) * 4;")
    value = program.to_dict()["children"][0]["children"][2]["children"][0]
    assert value["detail"] == "*"
    assert value["children"][0]["detail"] == "+"


def test_missing_identifier_produces_a_specific_message():
    _, _, _, errors = analyse("int = 10;")
    assert len(errors) == 1
    assert "Expected an identifier after type 'int'" in errors[0].message


def test_missing_semicolon_is_reported():
    _, _, _, errors = analyse("int a = 10")
    assert any("';'" in error.message for error in errors)


def test_parser_recovers_and_keeps_parsing():
    _, _, program, errors = analyse("int = 10;\nint b = 20;")
    assert len(errors) == 1
    assert len(program.statements) == 1        # the good statement survived
    assert program.statements[0].name == "b"


def test_unclosed_bracket_is_reported():
    _, _, _, errors = analyse("int a = (2 + 3;")
    assert any("')'" in error.message for error in errors)


def test_ast_text_rendering():
    _, _, program, _ = analyse("int a = 10;")
    text = render_ast(program.to_dict())
    assert "Declaration" in text
    assert "├── Type: int" in text
    assert "└── Number: 10" in text


# ----------------------------------------------------------------------
# Semantic analysis, TAC, optimisation, and target pseudo-assembly
# ----------------------------------------------------------------------
def test_semantic_analysis_builds_symbol_table_and_tac():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a = 10;\nint b = 20;\nint c = a + b * 2;", language="c"
    ))
    assert response.success is True
    assert [symbol.name for symbol in response.symbol_table] == ["a", "b", "c"]
    assert all(symbol.initialised for symbol in response.symbol_table)
    assert response.intermediate_code_text.splitlines() == [
        "a = 10", "b = 20", "t1 = b * 2", "t2 = a + t1", "c = t2"
    ]
    assert [phase.id for phase in response.phases if phase.status == "implemented"] == [
        "lexical", "syntax", "semantic", "intermediate", "optimization", "codegen"
    ]
    assert response.optimized_code_text == response.intermediate_code_text
    assert response.target_code_text.startswith("; CompilerLens educational pseudo-assembly")


def test_semantic_analysis_reports_undeclared_variables():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int a = missing + 1;", language="c"))
    assert response.success is False
    assert any("'missing' is used before it is declared" in error.message for error in response.semantic_errors)
    assert response.intermediate_code == []


def test_semantic_analysis_reports_duplicate_declarations():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int a = 1;\nint a = 2;", language="c"))
    assert any("already been declared" in error.message for error in response.semantic_errors)
    assert len(response.symbol_table) == 1


def test_semantic_analysis_reports_read_before_initialisation():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int a;\nint b = a + 1;", language="c"))
    assert any("before it is initialised" in error.message for error in response.semantic_errors)
    assert response.symbol_table[0].initialised is False


def test_semantic_analysis_reports_narrowing_type_mismatch():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int a = 2.5;", language="c"))
    assert any("type 'double'" in error.message and "type 'int'" in error.message for error in response.semantic_errors)


def test_assignment_initialises_a_previously_uninitialised_variable():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a;\na = 3;\nint b = a + 1;", language="c"
    ))
    assert response.success is True
    assert response.symbol_table[0].initialised is True
    assert response.intermediate_code_text.splitlines() == ["a = 3", "t1 = a + 1", "b = t1"]


def test_semantic_phase_is_skipped_after_syntax_errors():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int a = 1", language="c"))
    semantic_phase = next(phase for phase in response.phases if phase.id == "semantic")
    assert semantic_phase.ran is False
    assert response.symbol_table == []
    assert response.intermediate_code == []


def test_intermediate_code_preserves_unary_and_parenthesized_precedence():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a = -(2 + 3) * 4;", language="c"
    ))
    assert response.success is True
    assert response.intermediate_code_text.splitlines() == [
        "t1 = 2 + 3", "t2 = -t1", "t3 = t2 * 4", "a = t3"
    ]


def test_type_widening_is_allowed_for_numeric_initialization():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int count = 3; double total = count + 2;", language="c"
    ))
    assert response.success is True
    assert [symbol.initialised for symbol in response.symbol_table] == [True, True]


def test_invalid_initializer_does_not_mark_symbol_initialised():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int total = missing + 1;", language="c"
    ))
    assert response.success is False
    assert response.symbol_table[0].name == "total"
    assert response.symbol_table[0].initialised is False
    assert response.intermediate_code == []


def test_invalid_assignment_does_not_mark_target_initialised():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int total; total = missing + 1;", language="c"
    ))
    assert response.success is False
    assert response.symbol_table[0].initialised is False


def test_cpp_boolean_literal_and_type_are_supported():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="bool ready = true; bool finished = false;", language="cpp"
    ))
    assert response.success is True
    assert [(symbol.name, symbol.type, symbol.initialised) for symbol in response.symbol_table] == [
        ("ready", "bool", True), ("finished", "bool", True)
    ]
    assert response.intermediate_code_text.splitlines() == [
        "ready = true", "finished = false"
    ]


def test_java_boolean_literal_and_type_are_supported():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="boolean active = true; boolean done = false;", language="java"
    ))
    assert response.success is True
    assert [symbol.type for symbol in response.symbol_table] == ["boolean", "boolean"]
    assert response.intermediate_code_text.splitlines() == [
        "active = true", "done = false"
    ]


def test_boolean_values_cannot_be_used_in_arithmetic():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="boolean result = true + false;", language="java"
    ))
    assert response.success is False
    assert any("Arithmetic operator '+' cannot be applied" in error.message
               for error in response.semantic_errors)
    assert response.symbol_table[0].initialised is False
    assert response.intermediate_code == []


def test_boolean_and_numeric_assignment_are_incompatible():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="boolean active = 1;", language="java"
    ))
    assert response.success is False
    assert any("type 'boolean'" in error.message and "type 'int'" in error.message
               for error in response.semantic_errors)
    assert response.symbol_table[0].initialised is False


def test_failed_reassignment_does_not_clear_a_prior_initialization():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int total = 5; total = missing;", language="c"
    ))
    assert response.success is False
    assert response.symbol_table[0].initialised is True


def test_c_true_is_not_silently_treated_as_a_boolean_literal():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int value = true;", language="c"))
    assert response.success is False
    assert any("'true' is used before it is declared" in error.message
               for error in response.semantic_errors)


def test_optimizer_folds_constant_subexpressions_and_removes_dead_temps():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a = 10; int c = a + 2 * 3;", language="c"
    ))
    assert response.success is True
    assert response.intermediate_code_text.splitlines() == [
        "a = 10", "t1 = 2 * 3", "t2 = a + t1", "c = t2"
    ]
    assert response.optimized_code_text.splitlines() == [
        "a = 10", "t2 = a + 6", "c = t2"
    ]
    assert any("Constant folding" in note for note in response.optimization_notes)
    assert any("Removed unused temporary" in note for note in response.optimization_notes)


def test_codegen_emits_target_pseudo_assembly_from_optimized_ir():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a = 10; int c = a + 2 * 3;", language="c"
    ))
    assert response.target_name == "CompilerLens educational register machine"
    assert "ADD R0, #6" in response.target_code_text
    assert "STORE [c], R0" in response.target_code_text
    assert response.target_instruction_count > 0
    assert "not a native executable binary" in response.target_code_note


def test_semantic_errors_prevent_optimization_and_codegen():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(source_code="int total = missing + 1;", language="c"))
    assert response.success is False
    assert response.optimized_code == []
    assert response.target_code == []
    assert next(p for p in response.phases if p.id == "optimization").ran is False
    assert next(p for p in response.phases if p.id == "codegen").ran is False


def test_optimizer_preserves_unary_operations_on_variables():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest

    response = analyze(AnalyzeRequest(
        source_code="int a = 5; int b = -a;", language="c"
    ))
    assert response.success is True
    assert "t1 = -a" in response.optimized_code_text
    assert "NEG R0" in response.target_code_text


def test_phase_status_lists_all_six_implemented_phases():
    from api.routes import describe_pipeline

    phases = describe_pipeline()
    assert len(phases) == 6
    assert all(phase.status == "implemented" for phase in phases)
    assert [phase.order for phase in phases] == [1, 2, 3, 4, 5, 6]


def test_c_function_and_for_loop_emit_control_flow_tac():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "int sum(int n) { int s = 0; for (int i = 0; i < n; i++) { "
        "s = s + i; } return s; }"), language="c"))
    assert response.success is True
    assert "func int sum" in response.intermediate_code_text
    assert "label L1" in response.intermediate_code_text
    assert "ifFalse" in response.intermediate_code_text
    assert "return s" in response.intermediate_code_text
    assert "GOTO L1" in response.target_code_text


def test_if_else_and_boolean_condition_are_supported_in_cpp():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "bool ready = true; int value = 0; if (ready && value < 3) "
        "{ value = value + 1; } else { value = 5; }"), language="cpp"))
    assert response.success is True
    assert "ifFalse" in response.intermediate_code_text
    assert "label L" in response.intermediate_code_text


def test_undefined_function_call_is_reported_explicitly():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code="int x = compute(2);", language="c"))
    assert response.success is False
    assert any("has no definition" in error.message for error in response.semantic_errors)


def test_java_class_main_wrapper_with_if_else_is_supported():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "class Main { public static void main() { int x = 2; "
        "if (x < 3) { x = x + 1; } else { x = 0; } } }"), language="java"))
    assert response.success is True
    assert response.syntax_errors == []
    assert "func void main" in response.intermediate_code_text
    assert "ifFalse" in response.intermediate_code_text


def test_cpp_function_calls_flow_through_tac_and_codegen():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "int addOne(int x) { if (x < 3) { return x + 1; } else { return 0; } } "
        "int main() { int result = addOne(2); return result; }"), language="cpp"))
    assert response.success is True
    assert "param 2" in response.intermediate_code_text
    assert "call addOne, 1" in response.intermediate_code_text
    assert "CALL addOne, 1" in response.target_code_text
    assert "CMP_LT" in response.target_code_text


def test_c_stdio_header_printf_and_another_standard_header_are_supported():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "#include <stdio.h>\n#include <stdlib.h>\n"
        "int main() { int value = 7; printf(\"value=%d\\n\", value); return 0; }"), language="c"))
    assert response.success is True
    assert not response.lexical_errors and not response.syntax_errors and not response.semantic_errors
    assert any(token.type == "PREPROCESSOR_DIRECTIVE" for token in response.tokens)
    assert "printf 2" in response.intermediate_code_text
    assert "PRINT printf, 2 ARGUMENT(S)" in response.target_code_text


def test_stdio_call_requires_its_header_and_unsupported_header_is_named():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    no_header = analyze(AnalyzeRequest(source_code='int main() { printf("hi"); return 0; }', language="c"))
    assert any("requires #include <stdio.h>" in error.message for error in no_header.semantic_errors)
    bad_header = analyze(AnalyzeRequest(source_code="#include <mystery.h>\nint x = 1;", language="c"))
    assert any("not in the supported header set" in error.message for error in bad_header.lexical_errors)


def test_cpp_iostream_cmath_and_java_import_print_are_supported():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    cpp = analyze(AnalyzeRequest(source_code=(
        "#include <iostream>\n#include <cmath>\n"
        "int main() { double x = std::sqrt(9); std::cout << \"x=\" << x << std::endl; return 0; }"), language="cpp"))
    assert cpp.success is True
    assert "= libcall std::sqrt" in cpp.intermediate_code_text
    assert "std::cout 3" in cpp.intermediate_code_text
    assert "PRINT std::cout" in cpp.target_code_text
    java = analyze(AnalyzeRequest(source_code=(
        "import java.util.Scanner; class Main { public static void main() { "
        "System.out.println(\"Hello\"); } }"), language="java"))
    assert java.success is True
    assert any(token.type == "IMPORT_DIRECTIVE" for token in java.tokens)
    assert "System.out.println 1" in java.intermediate_code_text


def test_cpp_using_namespace_std_allows_unqualified_stream_and_math_names():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "#include <iostream>\n#include <cmath>\nusing namespace std;\n"
        "int main() { double value = sqrt(25); cout << value << endl; return 0; }"), language="cpp"))
    assert response.success is True
    assert "libcall sqrt" in response.intermediate_code_text
    assert "cout 2" in response.intermediate_code_text


def test_nested_block_can_shadow_global_and_symbol_table_keeps_both_scopes():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "int value = 1; int main() { if (value) { int value = 2; value = value + 1; } "
        "return value; }"), language="c"))
    assert response.success is True
    values = [symbol for symbol in response.symbol_table if symbol.name == "value"]
    assert len(values) == 2
    assert values[0].scope == "global"
    assert values[1].scope.startswith("global/function main/")


def test_block_and_for_variables_are_not_visible_after_scope_ends():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    block = analyze(AnalyzeRequest(source_code=(
        "int main() { if (1) { int hidden = 2; } return hidden; }"), language="c"))
    assert any("'hidden' is used before it is declared" in error.message for error in block.semantic_errors)
    loop = analyze(AnalyzeRequest(source_code=(
        "int main() { for (int i = 0; i < 2; i++) { } return i; }"), language="c"))
    assert any("'i' is used before it is declared" in error.message for error in loop.semantic_errors)


def test_program_runner_prints_computed_cpp_output_and_reads_input():
    from api.routes import run_program
    from models.schemas import RunRequest
    output = run_program(RunRequest(source_code=(
        "#include <iostream>\nusing namespace std; int main() { int a=8; int b=4; "
        "int c=a+b; cout << c; return 0; }"), language="cpp"))
    assert output.success is True and output.stdout == "12"
    input_output = run_program(RunRequest(source_code=(
        "#include <iostream>\nusing namespace std; int main() { int value; "
        "cin >> value; cout << value + 1; return 0; }"), language="cpp", stdin="12"))
    assert input_output.success is True and input_output.stdout == "13"


def test_cin_marks_declared_variables_initialized_for_semantic_analysis():
    from api.routes import analyze
    from models.schemas import AnalyzeRequest
    response = analyze(AnalyzeRequest(source_code=(
        "#include <iostream>\nusing namespace std;\nint main() { int a; int b; "
        "cin >> a >> b; int c = a + b; cout << c; return 0; }"), language="cpp"))
    assert response.success is True
    assert [symbol.initialised for symbol in response.symbol_table if symbol.name in {"a", "b"}] == [True, True]


def test_program_runner_reports_missing_input_and_runtime_errors():
    from api.routes import run_program
    from models.schemas import RunRequest
    response = run_program(RunRequest(source_code=(
        "#include <iostream>\nusing namespace std; int main() { int value; "
        "cin >> value; cout << value; }"), language="cpp"))
    assert response.success is False
    assert "Input ended" in response.stderr


def test_java_scanner_next_int_runs_even_odd_program():
    from api.routes import run_program
    from models.schemas import RunRequest
    source = ("import java.util.Scanner; class Main { public static void main() { "
              "Scanner input = new Scanner(System.in); int number = input.nextInt(); "
              "if (number % 2 == 0) { System.out.println(\"Even\"); } "
              "else { System.out.println(\"Odd\"); } } }")
    even = run_program(RunRequest(source_code=source, language="java", stdin="8"))
    odd = run_program(RunRequest(source_code=source, language="java", stdin="5"))
    assert even.success is True and even.stdout == "Even\n"
    assert odd.success is True and odd.stdout == "Odd\n"


def test_c_scanf_runs_even_odd_program_with_input_box_values():
    from api.routes import run_program
    from models.schemas import RunRequest
    source = ("#include <stdio.h>\nint main() { int number; scanf(\"%d\", &number); "
              "if (number % 2 == 0) { printf(\"Even\\n\"); } "
              "else { printf(\"Odd\\n\"); } return 0; }")
    even = run_program(RunRequest(source_code=source, language="c", stdin="8"))
    odd = run_program(RunRequest(source_code=source, language="c", stdin="5"))
    assert even.success is True and even.stdout == "Even\n"
    assert odd.success is True and odd.stdout == "Odd\n"


# ----------------------------------------------------------------------
# Runner (so the suite works without pytest installed)
# ----------------------------------------------------------------------
def _main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report anything unexpected
            failures += 1
            print(f"  ERROR {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
