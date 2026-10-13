# CompilerLens — Review Demo Script

## Project overview

CompilerLens implements all six phases for a restricted educational grammar: Lexical Analysis, Syntax Analysis, Semantic Analysis, Intermediate Code Generation, Optimization, and Code Generation. The supported grammar is an educational subset, not a full C/C++/Java compiler. The final output is pseudo-assembly for a small teaching machine, not a native executable.

## Demonstration 1: valid arithmetic program

Select C and compile:

```c
int a = 10;
int b = 20;
int c = a + b * 2;
```

Show the token stream and syntax tree first. In **Symbol table**, explain that each row records the identifier, type, declaration location, scope, and initialization state. In **Intermediate code**, the expected output is:

```text
a = 10
b = 20
t1 = b * 2
t2 = a + t1
c = t2
```

Explain that the temporary `t1` is produced by multiplication before `t2` adds `a`, preserving operator precedence.

## Demonstration 2: undeclared variable

```c
int total = price + 5;
```

Expected semantic diagnostic: `price` is used before it is declared. Intermediate code must not be generated when semantic analysis fails.

## Demonstration 3: duplicate declaration

```c
int score = 10;
int score = 20;
```

Expected diagnostic: `score` was already declared. The symbol table retains the first declaration.

## Demonstration 4: uninitialised variable

```c
int amount;
int result = amount + 1;
```

Expected diagnostic: `amount` may be used before it is initialised.

## Demonstration 5: incompatible assignment

```c
int count = 2.5;
```

Expected diagnostic: a `double` value cannot initialise an `int` variable under CompilerLens' educational narrowing rules.

## Demonstration 6: Optimization

Use this program (choose C):

```c
int a = 10;
int c = a + 2 * 3;
```

Open **Intermediate code** first. It should include `t1 = 2 * 3`. Then open **Optimization**. The optimized IR should show `t2 = a + 6` and remove the unused `t1` instruction. The notes explain the constant-folding and dead-temporary-removal passes.

Explain that optimization preserves the supported program's behaviour while simplifying its intermediate representation. CompilerLens currently performs local constant folding, temporary propagation, algebraic simplification, and unused-temporary removal.

## Demonstration 7: Code generation

Open **Code generation** for the same example. The panel displays readable register-machine pseudo-assembly, including instructions such as `MOV`, `LOAD`, `ADD`, and `STORE`. Explain that phase 6 lowers optimized TAC into target-style instructions. Be clear that this is educational pseudo-assembly, not native x86/ARM output or an executable file.

## Demonstration 8: booleans in C++ / Java

C++:

```cpp
bool ready = true;
bool finished = false;
```

Java:

```java
boolean active = true;
boolean done = false;
```

Expected: valid symbol-table entries and TAC assignments for the boolean literals. Boolean values are rejected as arithmetic operands.

## Suggested explanation

“CompilerLens makes six compiler phases visible. Lexical Analysis produces tokens, Syntax Analysis builds an AST, Semantic Analysis checks identifiers and types using a symbol table, and Intermediate Code Generation emits three-address code. The Optimization phase simplifies that code using constant folding and temporary cleanup. Finally, Code Generation translates the optimised IR into educational register-machine pseudo-assembly. This is a teaching prototype for a supported subset of C, C++ and Java-like declarations and arithmetic expressions; it does not claim to be a full production compiler or emit a native executable.”
