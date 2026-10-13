/** The short numeric summary shown above the result tabs. */
export default function StatBar({ statistics, success }) {
  if (!statistics) return null;

  const items = [
    { label: "lines", value: statistics.line_count },
    { label: "tokens", value: statistics.token_count },
    { label: "AST nodes", value: statistics.ast_node_count },
    { label: "tree depth", value: statistics.ast_depth },
  ];

  return (
    <div className="statbar">
      <span className={`verdict ${success ? "is-ok" : "is-bad"}`}>
        {success ? "Analysis completed" : "Problems found"}
      </span>
      {items.map((item) => (
        <span className="stat" key={item.label}>
          <strong>{item.value}</strong> {item.label}
        </span>
      ))}
    </div>
  );
}
