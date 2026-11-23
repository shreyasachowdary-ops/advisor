/**
 * Advisor API client — same-origin /api/* (Vite proxy → FastAPI).
 * Never invents citations or session IDs.
 */

function friendlyHttpError(status) {
  if (status === 422) {
    return "That request could not be processed. Please check your message and try again.";
  }
  if (status === 503) {
    return "The advisor is temporarily unavailable. Please try again shortly.";
  }
  if (status >= 500) {
    return "The advisor service encountered an error. Please try again.";
  }
  return "The advisor request failed. Please try again.";
}

async function advisorFetch(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error(
      "Could not reach the advisor. Check your connection and that the backend is running.",
    );
  }
  if (!res.ok) {
    throw new Error(friendlyHttpError(res.status));
  }
  if (res.status === 204) return null;
  try {
    return await res.json();
  } catch {
    throw new Error("The advisor returned an unexpected response. Please try again.");
  }
}

export async function sendChatMessage(payload) {
  const data = await advisorFetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!data || typeof data.answer !== "string" || typeof data.session_id !== "string") {
    throw new Error("The advisor returned an unexpected response. Please try again.");
  }
  return data;
}

export async function submitFeedback(messageId, feedbackType, sessionId) {
  return advisorFetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rating: feedbackType,
      message_id: messageId,
      session_id: sessionId ?? null,
    }),
  });
}

export async function confirmSafeguarding(body) {
  return advisorFetch("/api/safeguarding/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
