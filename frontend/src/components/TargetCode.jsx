/** Displays pseudo-assembly emitted from the optimised intermediate code. */
export default function TargetCode({ lines, text, targetName, instructionCount, note }) {
  if (!lines || lines.length === 0) {
    return <p className="empty">No target code is available. Fix lexical, syntax, or semantic errors first.</p>;
  }

  return (
    <div className="stage-result">
      <div className="stage-summary">
        <span><strong>{instructionCount}</strong> target instructions</span>
        <span>{targetName}</span>
        <button type="button" className="link-button" onClick={() => navigator.clipboard?.writeText(text || "")}>
          Copy target code
        </button>
      </div>
      <pre className="stage-code target-code" aria-label="Generated target code">{text}</pre>
      <p className="panel-explanation">{note}</p>
      <p className="panel-explanation">The generated output is readable pseudo-assembly for a small register machine. It illustrates code generation, but it is not native x86/ARM assembly and does not produce an executable binary.</p>
    </div>
  );
}
