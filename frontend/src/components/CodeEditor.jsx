import { useMemo, useRef } from "react";

/**
 * The source code editor: a textarea with a line-number gutter beside it.
 *
 * A plain textarea is deliberate. A syntax-highlighting editor would hide the
 * fact that the backend, not the browser, is doing the analysis.
 */
export default function CodeEditor({ value, onChange, language, onLanguageChange, languages, onAnalyze, busy }) {
  const gutterRef = useRef(null);

  const lineNumbers = useMemo(() => {
    const total = value.split("\n").length;
    return Array.from({ length: total }, (_, index) => index + 1);
  }, [value]);

  // Keep the gutter aligned when the textarea scrolls.
  function handleScroll(event) {
    if (gutterRef.current) gutterRef.current.scrollTop = event.target.scrollTop;
  }

  // Ctrl/Cmd + Enter runs the analysis without reaching for the mouse.
  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      onAnalyze();
    }
  }

  return (
    <section className="panel editor-panel">
      <header className="panel-head">
        <h2>Source code</h2>
        <label className="language-picker">
          <span className="visually-hidden">Language</span>
          <select value={language} onChange={(event) => onLanguageChange(event.target.value)}>
            {languages.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      <div className="editor">
        <div className="gutter" ref={gutterRef} aria-hidden="true">
          {lineNumbers.map((number) => (
            <span key={number}>{number}</span>
          ))}
        </div>
        <textarea
          className="code-input"
          value={value}
          spellCheck="false"
          autoComplete="off"
          aria-label="Source code"
          onChange={(event) => onChange(event.target.value)}
          onScroll={handleScroll}
          onKeyDown={handleKeyDown}
        />
      </div>

      <div className="editor-actions">
        <button className="run-button" onClick={onAnalyze} disabled={busy}>
          {busy ? "Analysing…" : "Compile / Analyze"}
        </button>
        <span className="shortcut-hint">or press Ctrl + Enter</span>
      </div>
    </section>
  );
}
