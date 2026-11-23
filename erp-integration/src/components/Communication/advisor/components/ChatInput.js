const CHARACTER_LIMIT = 600;

export default function ChatInput({ audience, value, onChange, onSubmit, loading }) {
  const placeholder =
    audience === "parent"
      ? "Ask about your child's routines, play, behaviour, or learning..."
      : "Ask about classroom behaviour, activities, routines, or communication...";
  const trimmed = value.trim();

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <p>General educational guidance - not a diagnosis or professional counselling.</p>
      <label htmlFor="advisor-message" className="sr-only">Message</label>
      <div className="composer-box">
        <textarea
          id="advisor-message"
          value={value}
          maxLength={CHARACTER_LIMIT}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={3}
          aria-describedby="advisor-char-count"
        />
        <div className="composer-actions">
          <span id="advisor-char-count">{value.length}/{CHARACTER_LIMIT}</span>
          <button type="submit" disabled={!trimmed || loading}>
            {loading ? "Sending" : "Send"}
          </button>
        </div>
      </div>
    </form>
  );
}
