/* Shows that * binds tighter than +, and that brackets change the tree shape.
   Compare the two syntax trees these produce. */
int x = 2 + 3 * 4;
int y = (2 + 3) * 4;
