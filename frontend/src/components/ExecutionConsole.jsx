export default function ExecutionConsole({ input, onInputChange, onRun, running, result, error }) {
  return (
    <section className="panel execution-console">
      <header className="panel-head">
        <h2>Program input and output</h2>
        <button className="run-button" onClick={onRun} disabled={running}>
          {running ? "Running…" : "Run program"}
        </button>
      </header>
      <label className="console-field">
        <span>Input (one value per line)</span>
        <textarea value={input} onChange={(event) => onInputChange(event.target.value)} placeholder="Optional program input" />
      </label>
      <div className="console-field">
        <span>Output</span>
        <pre className={error ? "console-output console-output--error" : "console-output"}>
          {error || (result ? result.stdout || "(no output)" : "Run a supported program to see its output.")}
        </pre>
        {result?.success && <small>{result.steps} interpreter steps</small>}
      </div>
    </section>
  );
}
