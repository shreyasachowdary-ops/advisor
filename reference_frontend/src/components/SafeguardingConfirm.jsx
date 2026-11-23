import { useState } from "react";

export default function SafeguardingConfirm({ response, userSummary, onConfirm }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!response?.requires_confirmation || response.safeguarding_event_id) {
    return null;
  }

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      await onConfirm(userSummary);
    } catch {
      setError("Could not submit the safeguarding log. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="safeguarding-confirm">
      <p>
        Optional PoC log for a safeguarding lead. This does not replace contacting a professional.
      </p>
      {error && <p className="empty-sources">{error}</p>}
      <button type="button" disabled={loading} onClick={handleConfirm}>
        {loading ? "Submitting…" : "I confirm — log concern for safeguarding follow-up"}
      </button>
    </div>
  );
}
