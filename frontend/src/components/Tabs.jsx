/**
 * A small tab bar. Each tab can carry a count badge, which is how the user sees
 * "3 errors" without switching to the errors tab first.
 */
export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          className={`tab ${active === tab.id ? "is-active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.count > 0 && (
            <span className={`tab-count ${tab.tone === "alert" ? "is-alert" : ""}`}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
