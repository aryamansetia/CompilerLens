/**
 * Every diagnostic from every phase, grouped by the phase that produced it.
 *
 * Errors say what went wrong and how to fix it. They never say
 * "compilation failed" and stop there.
 */
export default function ErrorList({ lexicalErrors, syntaxErrors, semanticErrors = [] }) {
  const total = lexicalErrors.length + syntaxErrors.length + semanticErrors.length;

  if (total === 0) {
    return (
      <p className="empty empty--good">
        No lexical, syntax, or semantic errors. The program passed the implemented compiler checks.
      </p>
    );
  }

  const groups = [
    { title: "Lexical errors", subtitle: "Found while splitting the text into tokens", items: lexicalErrors },
    { title: "Syntax errors", subtitle: "Found while checking the tokens against the grammar", items: syntaxErrors },
    { title: "Semantic errors", subtitle: "Found while checking declarations, initialisation, and type compatibility", items: semanticErrors },
  ].filter((group) => group.items.length > 0);

  return (
    <div className="error-view">
      {groups.map((group) => (
        <section className="error-group" key={group.title}>
          <h3>{group.title}</h3>
          <p className="error-subtitle">{group.subtitle}</p>
          <ul>
            {group.items.map((error, index) => (
              <li className="error-item" key={`${error.line}-${error.column}-${index}`}>
                <span className="error-position">
                  line {error.line}, col {error.column}
                </span>
                <p className="error-message">{error.message}</p>
                {error.hint && <p className="error-hint">{error.hint}</p>}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
