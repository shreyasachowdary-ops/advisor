import AssistantResponse from "./AssistantResponse.jsx";

export default function ChatMessage({ message, onFollowUpSelect, onFeedback, onSafeguardingConfirm }) {
  if (message.role === "user") {
    return (
      <article className="message-row user-row">
        <div className="user-message">
          <span>You</span>
          <p>{message.content}</p>
        </div>
      </article>
    );
  }

  return (
    <article className="message-row assistant-row">
      <AssistantResponse
        messageId={message.id}
        userQuery={message.userQuery}
        response={message.response}
        feedback={message.feedback}
        onFollowUpSelect={onFollowUpSelect}
        onFeedback={onFeedback}
        onSafeguardingConfirm={onSafeguardingConfirm}
      />
    </article>
  );
}
