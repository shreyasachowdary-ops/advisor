import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";

// True while the newest answer is showing text but is not complete yet.
function isStreaming(messages) {
  const last = messages[messages.length - 1];
  return Boolean(last && last.role === "assistant" && !last.response && last.streamingText);
}

export default function ChatWindow({
  audience,
  selectedAgeLabel,
  messages,
  loading,
  error,
  draft,
  onDraftChange,
  onSubmit,
  onRetry,
  onSidebarToggle,
  onFollowUpSelect,
  onFeedback,
  onSafeguardingConfirm,
}) {
  return (
    <main className="chat-column">
      <button
        type="button"
        className="menu-button"
        onClick={onSidebarToggle}
        aria-label="Open advisor controls"
      >
        Menu
      </button>
      <div className="chat-header">
        <div>
          <p className="eyebrow">{audience} mode • {selectedAgeLabel}</p>
          <h2>How can I help you today?</h2>
        </div>
      </div>

      <div className="message-area" aria-live="polite">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            onFollowUpSelect={onFollowUpSelect}
            onFeedback={onFeedback}
            onSafeguardingConfirm={onSafeguardingConfirm}
          />
        ))}

        {loading && !isStreaming(messages) && <LoadingState />}
        {error && <ErrorState message={error} onRetry={onRetry} />}
      </div>

      <ChatInput audience={audience} value={draft} onChange={onDraftChange} onSubmit={onSubmit} loading={loading} />
    </main>
  );
}
