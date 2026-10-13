/**
 * The token stream produced by lexical analysis.
 *
 * The category colour used here is reused in the AST, so a student can trace a
 * lexeme from the table into the tree by colour alone.
 */
export default function TokenTable({ tokens }) {
  if (!tokens.length) {
    return <p className="empty">No tokens yet. Enter a program and run the analysis.</p>;
  }

  const counts = tokens.reduce((totals, token) => {
    totals[token.category] = (totals[token.category] || 0) + 1;
    return totals;
  }, {});

  return (
    <div className="token-view">
      <div className="legend">
        {Object.entries(counts).map(([category, count]) => (
          <span className={`chip chip--${category}`} key={category}>
            {category} <strong>{count}</strong>
          </span>
        ))}
      </div>

      <table className="token-table">
        <thead>
          <tr>
            <th className="col-index">#</th>
            <th>Lexeme</th>
            <th>Token type</th>
            <th className="col-pos">Line</th>
            <th className="col-pos">Col</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => (
            <tr key={token.position} className={token.category === "invalid" ? "row-invalid" : ""}>
              <td className="col-index">{token.position}</td>
              <td className="lexeme">{token.lexeme}</td>
              <td>
                <span className={`chip chip--${token.category}`}>{token.type}</span>
              </td>
              <td className="col-pos">{token.line}</td>
              <td className="col-pos">{token.column}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
