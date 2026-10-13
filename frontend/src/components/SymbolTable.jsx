/** A readable view of the variables discovered by semantic analysis. */
export default function SymbolTable({ symbols }) {
  if (!symbols || symbols.length === 0) {
    return (
      <p className="empty">
        No symbol-table entries yet. Run a syntactically valid program containing variable declarations.
      </p>
    );
  }

  return (
    <div className="data-table-wrap">
      <p className="panel-explanation">
        Each row represents a declared variable. Initialisation status is updated as assignments are analysed.
      </p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Scope</th>
            <th>Declared at</th>
            <th>Initialised</th>
          </tr>
        </thead>
        <tbody>
          {symbols.map((symbol) => (
            <tr key={`${symbol.name}-${symbol.line}-${symbol.column}`}>
              <td className="lexeme">{symbol.name}</td>
              <td><span className="type-chip">{symbol.type}</span></td>
              <td>{symbol.scope}</td>
              <td className="num">{symbol.line}:{symbol.column}</td>
              <td>
                <span className={`initialised-chip ${symbol.initialised ? "is-yes" : "is-no"}`}>
                  {symbol.initialised ? "Yes" : "No"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
