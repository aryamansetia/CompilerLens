/**
 * The compiler pipeline, drawn as a numbered sequence.
 *
 * Implemented phases have a solid outline; only explicitly planned phases use
 * a dashed outline. Run state and implementation state are shown separately.
 */
export default function PipelineStrip({ phases }) {
  if (!phases || phases.length === 0) return null;

  return (
    <section className="pipeline" aria-label="Compiler phases">
      {phases.map((phase, index) => {
        const planned = phase.status === "planned";
        const state = phase.ok === false ? "failed" : phase.ran ? "passed" : "idle";
        return (
          <div className="pipeline-item" key={phase.id}>
            <article
              className={`phase phase--${planned ? "planned" : "built"} phase--${state}`}
              title={phase.summary}
            >
              <span className="phase-order">{phase.order}</span>
              <span className="phase-body">
                <span className="phase-name">{phase.name}</span>
                <span className="phase-produces">{phase.produces}</span>
              </span>
              <span className="phase-state">
                {planned ? "not built yet" : state === "failed" ? "errors found" : state === "passed" ? "completed" : "ready"}
              </span>
            </article>
            {index < phases.length - 1 && <span className="pipeline-arrow" aria-hidden="true" />}
          </div>
        );
      })}
    </section>
  );
}
