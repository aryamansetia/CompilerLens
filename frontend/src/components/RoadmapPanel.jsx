/** Shows the implementation status of the six educational compiler phases. */
export default function RoadmapPanel({ phases }) {
  const built = phases.filter((phase) => phase.status === "implemented");
  const planned = phases.filter((phase) => phase.status === "planned");

  return (
    <div className="roadmap">
      <section>
        <h3>Implemented phases</h3>
        <ul className="roadmap-list">
          {built.map((phase) => (
            <li key={phase.id}>
              <span className="roadmap-name">{phase.name}</span>
              <span className="roadmap-produces">produces {phase.produces}</span>
              <p>{phase.summary}</p>
              <code>{phase.module}</code>
            </li>
          ))}
        </ul>
      </section>
      {planned.length > 0 && (
        <section>
          <h3>Planned phases</h3>
          <ul className="roadmap-list roadmap-list--planned">
            {planned.map((phase) => (
              <li key={phase.id}>
                <span className="roadmap-name">{phase.name}</span>
                <span className="roadmap-produces">will produce {phase.produces}</span>
                <p>{phase.summary}</p>
                <code>{phase.module}</code>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
