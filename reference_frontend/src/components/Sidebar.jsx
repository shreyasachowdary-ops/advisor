import ModeSelector from "./ModeSelector.jsx";

export default function Sidebar({
  ageOptions,
  selectedAge,
  selectedAgeLabel,
  audience,
  quickTopics,
  isOpen,
  isCollapsed,
  onAgeChange,
  onAudienceChange,
  onTopicSelect,
  onClose,
  onCollapseToggle,
}) {
  return (
    <aside className={`sidebar ${isOpen ? "open" : ""} ${isCollapsed ? "collapsed" : ""}`} aria-label="Advisor controls">
      <div className="mobile-side-head">
        <strong>Advisor controls</strong>
        <button type="button" onClick={onClose}>Close</button>
      </div>

      <button
        className="collapse-button"
        type="button"
        onClick={onCollapseToggle}
        aria-label={isCollapsed ? "Expand sidebar" : "Minimize sidebar"}
        title={isCollapsed ? "Expand sidebar" : "Minimize sidebar"}
      >
        {isCollapsed ? ">" : "<"}
      </button>

      <section className="identity-panel">
        <h1>ChildConnect</h1>
        <p>
          AI guidance for preschool parents and teachers. Use it for routines, play-based learning,
          early behaviour support, and parent-teacher communication.
        </p>
      </section>

      <section className="control-section sidebar-mode">
        <h2>Mode</h2>
        <ModeSelector value={audience} onChange={onAudienceChange} compact />
      </section>

      <section className="control-section">
        <label className="field-label" htmlFor="child-age">Child age</label>
        <select id="child-age" value={selectedAge} onChange={(event) => onAgeChange(event.target.value)}>
          {ageOptions.map((age) => (
            <option key={age.value} value={age.value}>
              {age.label}
            </option>
          ))}
        </select>
        <p className="field-help">Using guidance for {selectedAgeLabel}.</p>
      </section>

      <section className="control-section">
        <h2>Quick starts</h2>
        <div className="topic-list">
          {quickTopics.slice(0, 5).map((topic) => (
            <button key={topic.label} type="button" onClick={() => onTopicSelect(topic.question)}>
              {topic.label}
            </button>
          ))}
        </div>
      </section>

      <section className="privacy-notice compact">
        <h2>Scope</h2>
        <p>General educational guidance only. No diagnosis, therapy, medical advice, or student records.</p>
      </section>
    </aside>
  );
}
