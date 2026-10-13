# CompilerLens

**An Interactive Visualization Platform for Understanding Compiler Internals**

Compiler Design Lab project · six educational phases implemented

---

## Problem statement

A compiler is normally a black box. Source code goes in, an executable comes out,
and everything in between is invisible. Students are taught that a compiler works
in phases — lexical analysis, syntax analysis, semantic analysis, intermediate
code, optimization, code generation — but they never *see* those phases produce
anything. The gap between the textbook diagram and a real compiler is large
enough that the phases stay abstract.

## Objective

CompilerLens opens the box. A user types a program, presses one button, and sees
the actual output of each compiler phase: the token stream, the abstract syntax
tree, and the errors each phase produced. The tool is built phase by phase, and
the interface always shows which phases are implemented and which are not.

---

## Implemented compiler phases

| Phase | Status | Produces |
| --- | --- | --- |
| 1. Lexical Analysis | **Implemented** | Tokens |
| 2. Syntax Analysis | **Implemented** | Abstract Syntax Tree |
| 3. Semantic Analysis | **Implemented** | Symbol table and semantic diagnostics |
| 4. Intermediate Code Generation | **Implemented** | Three-address code (TAC) |
| 5. Optimization | **Implemented** | Optimised intermediate representation and pass notes |
| 6. Code Generation | **Implemented** | Educational register-machine pseudo-assembly |
| Program execution | **Implemented for the supported subset** | Captured output and optional input through a bounded AST interpreter |

Phases 3–6 live in `backend/pipeline/future_stages.py`. Optimisation applies
literal constant folding, temporary propagation, algebraic simplification, and
removal of unused temporary assignments. Code generation translates optimized
TAC into readable instructions for a small educational register machine. This
output is pseudo-assembly for learning, not native x86/ARM assembly or an executable
binary. Later stages run only when lexical, syntax, and semantic checks succeed.

### Features

**Lexical analysis**
- Keywords, using separate tables for C, C++ and Java
- Identifiers, numbers (with type suffixes such as `3.14f` and `100L`),
  string literals and character literals
- Over 40 operators, matched longest-first so `==` is one token, not two
- Separators, brackets, braces and semicolons
- `//` line comments and `/* */` block comments
- Line and column recorded for every token
- Errors: invalid characters, malformed numbers such as `12abc`, unterminated
  strings, unclosed block comments
- Recognises common C/C++ headers including `stdio.h`, `stdlib.h`, `math.h`,
  `string.h`, `iostream`, `cmath`, `vector`, and `algorithm`; basic `printf`/`puts`
  require `stdio.h`, C++ `std::cout` requires `iostream`, and common `std::` math
  calls such as `sqrt`/`pow` require `cmath`
- Recognises Java import declarations; models `System.out.print/println` and
  common `Math` calls (`abs`, `sqrt`, `pow`, `min`, `max`) as educational IR;
  supports `Scanner(System.in)` with `nextInt()` for input

**Syntax analysis**
- Hand-written recursive-descent parser
- Operator precedence arises from the grammar's structure, not a lookup table
- Panic-mode error recovery: a bad statement is reported, then the parser skips
  to the next semicolon and keeps going, so one mistake does not hide the rest
- Specific error messages with a fix suggestion, never "compilation failed"

**Abstract syntax tree**
- Structured AST nodes, each serialised for the frontend and shown as a collapsible tree
- Drawn as an interactive collapsible tree, or as plain indented text

**Semantic analysis**
- Builds a symbol table containing each declared variable's type, scope, source position, and initialisation status
- Reports undeclared variables, duplicate declarations, reads before initialisation, arithmetic type issues, and incompatible assignments
- Tracks global, function, nested-block, and `for` scopes, including inner-variable shadowing and out-of-scope diagnostics; uses educational numeric widening rules
- Supports `true`/`false` as boolean literals in C++ (`bool`) and Java (`boolean`); boolean values cannot be used as arithmetic operands

**Intermediate code generation**
- Walks the AST and emits machine-independent three-address code
- Produces temporary values (`t1`, `t2`, …) for nested arithmetic, preserving operator precedence
- Shows each instruction, its source line, total instruction count, and temporary count
- Blocks TAC generation when lexical, syntax, or semantic errors are present

### Supported grammar

```
Program     -> (Function | Statement)*
Function    -> Type Identifier '(' Parameters? ')' Block
Statement   -> Declaration | Assignment | ExpressionStatement | If | While | For | Return
Declaration -> Type Identifier ';'
             | Type Identifier '=' Expression ';'
Assignment  -> Identifier '=' Expression ';'
If          -> 'if' '(' Expression ')' Block ('else' Block)?
While       -> 'while' '(' Expression ')' Block
For         -> 'for' '(' (Declaration | Assignment)? ';' Expression? ';' Update ')' Block
Expression  -> Term (('+' | '-' | relational | logical) Term)*
Term        -> Factor (('*' | '/' | '%') Factor)*
Factor      -> Number | BooleanLiteral (C++/Java) | Identifier | '(' Expression ')' | ('-' | '+') Factor
```

Types: `int`, `float`, `double`, `char`, `long`, `short`, plus `bool` in C++ and
`boolean` in Java.

This remains an educational subset rather than a standards-complete compiler.
Implemented control flow lowers to labels and conditional jumps in TAC. Simple
function definitions and calls are supported. Included headers and Java imports
are recognized, but this does not implement the full APIs of those libraries.
Dynamic allocation, string/vector algorithms, Java Scanner methods
other than `nextInt()`, and most library calls remain unsupported. Java accepts a simple class wrapper and modifiers around methods,
including `public static void main()`; Java `String[] args` parameters, C/C++
preprocessor directives, pointers, arrays, structs/classes, switch/do-while,
exceptions, I/O library calls, and advanced declarations are not implemented.
When the parser encounters unsupported syntax it reports a syntax diagnostic
instead of silently accepting it.

---

## Technology stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Python 3.10+ with FastAPI | Automatic request validation, generated API docs, and Python suits string and tree work |
| Validation | Pydantic v2 | One guaranteed response shape for the frontend |
| Frontend | React 18 with Vite | An AST is recursive; a recursive component draws it at any depth |
| Styling | Hand-written CSS | No framework, so every rule in the file is one someone chose |
| Tests | 38 tests, no external runner needed | Runs with plain Python or with pytest |

No parser generator is used. The lexer and parser are written by hand so that
every decision they make is visible and explainable.

---

## Architecture

```
Browser (React, port 5173)
    |
    |  POST /api/analyze   { source_code, language }
    v
FastAPI (port 8000)
    |
    +-- Pydantic validates the request
    |
    +-- Phase 1  Lexer   -> tokens + lexical errors     IMPLEMENTED
    +-- Phase 2  Parser  -> AST    + syntax errors      IMPLEMENTED
    +-- Phase 3  Semantic analyzer -> symbol table      IMPLEMENTED
    +-- Phase 4  IR generator -> three-address code     IMPLEMENTED
    +-- Phase 5  Optimizer                              IMPLEMENTED
    +-- Phase 6  Code generator                         IMPLEMENTED
    +-- Run      Bounded AST interpreter                 IMPLEMENTED (subset)
    |
    v
JSON response: tokens, AST, symbol table, source TAC, optimised TAC,
               target pseudo-assembly, diagnostics, phase statuses, statistics
```

### Project structure

```
CompilerLens/
├── backend/
│   ├── main.py                     FastAPI app, CORS, static mount
│   ├── api/
│   │   ├── routes.py               the five endpoints
│   │   └── examples.py             ready-made demo programs
│   ├── lexer/
│   │   ├── lexer.py                the scanner
│   │   ├── token_types.py          TokenType enum and Token dataclass
│   │   └── keywords.py             C / C++ / Java keyword tables
│   ├── parser/
│   │   ├── parser.py               recursive-descent parser
│   │   └── ast_nodes.py            AST node classes
│   ├── models/schemas.py           Pydantic request and response models
│   ├── pipeline/
│   │   ├── phases.py               description of all six phases
│   │   └── future_stages.py        semantic checks, TAC, optimizer, target pseudo-assembly
│   ├── utils/
│   │   ├── errors.py               shared CompilerError type
│   │   └── ast_printer.py          text tree renderer
│   ├── static/index.html           built-in UI, needs no Node.js
│   └── tests/test_compiler.py      38 tests
├── frontend/
│   ├── package.json
│   ├── vite.config.js              proxies /api to port 8000
│   ├── index.html
│   └── src/
│       ├── App.jsx                 application state
│       ├── api.js                  every backend call
│       ├── styles.css
│       └── components/             editor, tabs, token table, AST tree, ...
├── examples/                       demo programs, including C++/Java booleans
├── START_HERE.md                   shortest setup path for a new developer
├── RUN_ON_MAC.md                   detailed VS Code/macOS instructions
├── REVIEW_DEMO.md                  demonstration order and explanation script
├── requirements.txt
└── README.md
```

---

## Installation

Requirements: Python 3.10 or newer, and Node.js 18 or newer.

### 1. Backend

From the project root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
```

### 2. Frontend

In a second terminal, from the project root:

```bash
cd frontend
npm install
```

The first `npm install` takes a few minutes. Do it before demo day, not during.

---

## Running

**Terminal 1 — backend**

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173**

### Other useful URLs

| URL | What it is |
| --- | --- |
| http://localhost:5173 | The React interface |
| http://127.0.0.1:8000 | Built-in interface, works with Python alone |
| http://127.0.0.1:8000/docs | Interactive API documentation |

The built-in interface at port 8000 is a fallback. It needs no Node.js and no
build step, so the project stays demonstrable if npm misbehaves.

### Running the tests

```bash
cd backend
python3 -m tests.test_compiler
```

Expected output ends with `38/38 tests passed.`

---

## API

### `POST /api/analyze`

Request:

```json
{
  "source_code": "int a = 10;",
  "language": "c"
}
```

Response (abridged):

```json
{
  "success": true,
  "language": "c",
  "tokens": [
    { "lexeme": "int", "type": "KEYWORD", "category": "keyword", "line": 1, "column": 1, "position": 0 },
    { "lexeme": "a",   "type": "IDENTIFIER", "category": "identifier", "line": 1, "column": 5, "position": 1 }
  ],
  "ast": { "node_type": "Program", "label": "Program", "children": [] },
  "ast_text": "Program: 1 statement\n└── Declaration\n    ├── Type: int\n    ...",
  "lexical_errors": [],
  "syntax_errors": [],
  "semantic_errors": [],
  "symbol_table": [
    { "name": "a", "type": "int", "scope": "global", "line": 1, "column": 5, "initialised": true }
  ],
  "intermediate_code": [
    { "index": 1, "instruction": "a = 10", "result": "a", "operator": "=", "arg1": "10", "arg2": null, "line": 1 }
  ],
  "intermediate_code_text": "a = 10",
  "optimized_code_text": "a = 10",
  "optimization_notes": [],
  "target_code_text": "; CompilerLens educational pseudo-assembly\n...",
  "phases": [],
  "statistics": { "token_count": 5, "ast_node_count": 6, "ast_depth": 4 }
}
```

### Other endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/examples` | The demo programs |
| POST | `/api/run` | Interpret supported programs and return output |
| GET | `/api/languages` | Supported languages and their type keywords |
| GET | `/api/pipeline` | All six phases and their status |
| GET | `/api/health` | Service health check |

---

## Example

**Input**

```c
int a = 10;
int b = 20;
int c = a + b;
```

**Tokens** (17 in total, first five shown)

| Lexeme | Token type | Line | Col |
| --- | --- | --- | --- |
| `int` | KEYWORD | 1 | 1 |
| `a` | IDENTIFIER | 1 | 5 |
| `=` | ASSIGNMENT_OPERATOR | 1 | 7 |
| `10` | NUMBER | 1 | 9 |
| `;` | SEMICOLON | 1 | 11 |

**Three-address code**

For the source `int a = 10; int b = 20; int c = a + b;`, the symbol table contains
`a`, `b`, and `c`, all with type `int` and initialised status `Yes`. The generated
three-address code is:

```
a = 10
b = 20
t1 = a + b
c = t1
```

**Abstract syntax tree**

```
Program: 3 statements
├── Declaration
│   ├── Type: int
│   ├── Identifier: a
│   └── Value
│       └── Number: 10
├── Declaration
│   ├── Type: int
│   ├── Identifier: b
│   └── Value
│       └── Number: 20
└── Declaration
    ├── Type: int
    ├── Identifier: c
    └── Value
        └── BinaryExpression: +
            ├── Identifier: a
            └── Identifier: b
```

### Error reporting

Input `int a = missing + 1;` produces a semantic diagnostic explaining that
`missing` is used before it is declared. Since the semantic phase reports an
error, the intermediate-code panel remains empty for that run.

Input `int = 10;` produces:

```
Syntax Analysis, line 1, column 5
Expected an identifier after type 'int', but found '='.
Hint: A declaration looks like: int a = 10;
```

Input `int b@ = 5;` produces:

```
Lexical Analysis, line 1, column 6
'@' is not a valid character in C source code.
Hint: Remove this character.
```

---

## Future scope

| Stage | Status | Potential extension |
| --- | --- | --- |
| Native assembly / executable output | Future extension | Real target-specific assembly and machine-code generation |
| Wider optimisation | Future extension | Global constant propagation, control-flow analysis, richer dead-code elimination |
| Wider C / C++ / Java support | Planned | Function calls, nested lexical scopes, Java argument arrays, and richer declarations |
| Advanced visualisation | Planned | Step-through mode and token-to-tree highlighting |
| Testing and deployment | Ongoing | More edge cases, frontend tests, and hosting |

All six educational phases run for the supported scalar and structured-control subset. The project is not a full C/C++/Java compiler: native assembly and executable binaries remain future extensions, as do the unsupported constructs listed above.
