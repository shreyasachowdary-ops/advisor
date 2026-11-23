const feedbackOptions = [
  { label: "Helpful", value: "helpful" },
  { label: "Not helpful", value: "not_helpful" },
  { label: "Report unsafe", value: "unsafe" },
];

export default function FeedbackControls({ messageId, value, onFeedback }) {
  return (
    <div className="feedback-controls" aria-label="Response feedback">
      <span>Was this helpful?</span>
      <div>
        {feedbackOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            className={value === option.value ? "selected" : ""}
            onClick={() => onFeedback(messageId, option.value)}
            aria-pressed={value === option.value}
          >
            {value === option.value ? "Selected: " : ""}
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
