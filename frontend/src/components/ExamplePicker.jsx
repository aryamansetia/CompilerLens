/** One-click programs, including two that deliberately contain errors. */
export default function ExamplePicker({ examples, onPick }) {
  if (!examples.length) return null;

  return (
    <section className="panel examples-panel">
      <header className="panel-head">
        <h2>Example programs</h2>
      </header>
      <ul className="example-list">
        {examples.map((example) => (
          <li key={example.id}>
            <button className="example" onClick={() => onPick(example)}>
              <span className="example-title">{example.title}</span>
              <span className="example-description">{example.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
