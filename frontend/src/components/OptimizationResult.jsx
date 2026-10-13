/** Displays the input TAC, optimized TAC, and explanations of applied passes. */
export default function OptimizationResult({ originalText, optimizedInstructions, optimizedText, notes }) {
  if (!optimizedInstructions || optimizedInstructions.length === 0) {
    return <p className="empty">No optimised IR is available. Fix lexical, syntax, or semantic errors first.</p>;
  }

  return (
    <div className="stage-result">
      <div className="stage-summary">
        <span><strong>{optimizedInstructions.length}</strong> optimised instructions</span>
        <button type="button" className="link-button" onClick={() => navigator.clipboard?.writeText(optimizedText || "")}>
          Copy optimised code
        </button>
      </div>
      <h3>Original three-address code</h3>
      <pre className="stage-code">{originalText || "(no instructions)"}</pre>
      <h3>Optimised intermediate representation</h3>
      <pre className="stage-code">{optimizedText || "(no instructions)"}</pre>
      <h3>Optimisations applied</h3>
      {notes?.length ? (
        <ol className="optimisation-list">
          {notes.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}
        </ol>
      ) : (
        <p className="empty compact">No rewrite was needed for this program.</p>
      )}
      <p className="panel-explanation">The current educational optimizer performs literal constant folding, temporary propagation, algebraic simplification, and removal of unused temporary assignments. It does not globally replace named variables with constants.</p>
    </div>
  );
}
