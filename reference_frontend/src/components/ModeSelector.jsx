export default function ModeSelector({ value, onChange, compact = false }) {
  return (
    <div
      className={`segmented ${compact ? "segmented-compact" : ""} ${value === "teacher" ? "teacher-selected" : "parent-selected"}`}
      role="group"
      aria-label="Audience mode"
    >
      <span className="liquid-thumb" aria-hidden="true" />
      {["parent", "teacher"].map((mode) => (
        <button
          key={mode}
          type="button"
          className={value === mode ? "active" : ""}
          onClick={() => onChange(mode)}
          aria-pressed={value === mode}
        >
          {mode === "parent" ? "Parent" : "Teacher"}
        </button>
      ))}
    </div>
  );
}
