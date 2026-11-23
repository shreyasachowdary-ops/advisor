export default function ErrorState({ message, onRetry }) {
  return (
    <div className="error-state" role="alert">
      <div>
        <strong>Something went wrong</strong>
        <p>{message}</p>
      </div>
      <button type="button" onClick={onRetry}>Try again</button>
    </div>
  );
}
