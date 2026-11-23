export default function FollowUpCard({ question, onSelect }) {
  return (
    <button className="follow-up-card" type="button" onClick={() => onSelect(question)}>
      <span>Suggested follow-up</span>
      <strong>{question}</strong>
    </button>
  );
}
