/* Two problems the lexer catches before the parser ever runs:
   '@' is not a valid character, and 12abc is not a valid number. */
int a = 10;
int b@ = 5;
int c = 12abc;
