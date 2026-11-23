import ChatInput from "./ChatInput.jsx";
import ChatMessage from "./ChatMessage.jsx";
import ErrorState from "./ErrorState.jsx";
import LoadingState from "./LoadingState.jsx";

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

        {loading && <LoadingState />}
        {error && <ErrorState message={error} onRetry={onRetry} />}
      </div>

      <ChatInput audience={audience} value={draft} onChange={onDraftChange} onSubmit={onSubmit} loading={loading} />
    </main>
  );
}
