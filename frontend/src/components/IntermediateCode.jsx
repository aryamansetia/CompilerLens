/** Three-address intermediate representation emitted from a valid AST. */
export default function IntermediateCode({ instructions, codeText, temporaryCount }) {
  if (!instructions || instructions.length === 0) {
    return (
      <p className="empty">
        No intermediate code was generated. Make sure the source passes lexical, syntax, and semantic analysis.
      </p>
    );
  }

  return (
    <div className="ir-view">
      <div className="ir-summary">
        <span><strong>{instructions.length}</strong> instructions</span>
        <span><strong>{temporaryCount}</strong> temporary variables</span>
        <button
          type="button"
          className="link-button"
          onClick={() => navigator.clipboard?.writeText(codeText || "")}
          title="Copy the three-address code"
        >
          Copy code
        </button>
      </div>
      <pre className="ir-code" aria-label="Three-address intermediate code">
        {instructions.map((item) => (
          <span className="ir-line" key={item.index}>
            <span className="ir-number">{String(item.index).padStart(2, "0")}</span>
            <code>{item.instruction}</code>
            <span className="ir-source-line">line {item.line}</span>
          </span>
        ))}
      </pre>
      <p className="panel-explanation">
        Temporary variables (t1, t2, …) store intermediate expression results. Each instruction performs one simple operation.
      </p>
    </div>
  );
}
