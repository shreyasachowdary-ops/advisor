/**
 * Advisor API client for the ERP — ChildConnect UI.
 * Calls {api.base_url}/api/advisor/* (same pattern as GenerateNotice.js);
 * the ERP Flask server checks login/role and forwards to the Advisor backend.
 * Never invents citations or session IDs.
 */
import { getConfig } from "../../contexts/config";

const { api } = getConfig();
const API_BASE = (api?.base_url || "").replace(/\/+$/, "");

const ADVISOR_ROUTES = {
  health: `${API_BASE}/api/advisor/health`,
  chat: `${API_BASE}/api/advisor/chat`,
  chatStream: `${API_BASE}/api/advisor/chat/stream`,
  feedback: `${API_BASE}/api/advisor/feedback`,
  safeguardingConfirm: `${API_BASE}/api/advisor/safeguarding/confirm`,
};

function friendlyHttpError(status) {
  if (status === 401) {
    return "Your ERP session has expired. Please log in again.";
  }
  if (status === 403) {
    return "Your role does not have access to the advisor.";
  }
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

async function advisorFetch(url, options) {
  let res;
  try {
    res = await fetch(url, { credentials: "include", ...options });
  } catch {
    throw new Error(
      "Could not reach the advisor. Check your connection and that the advisor service is running.",
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
  const data = await advisorFetch(ADVISOR_ROUTES.chat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!data || typeof data.answer !== "string" || typeof data.session_id !== "string") {
    throw new Error("The advisor returned an unexpected response. Please try again.");
  }
  return data;
}

/** The ERP server has no streaming route yet; the caller should use sendChatMessage. */
export class StreamUnavailableError extends Error {}

function validChatResponse(data) {
  return Boolean(data && typeof data.answer === "string" && typeof data.session_id === "string");
}

/**
 * Same request as sendChatMessage, but the answer arrives while it is written.
 * onDelta(text) is called for each piece of text; resolves with the full final response,
 * whose answer replaces the streamed text. Throws StreamUnavailableError before anything
 * is sent to the model when the ERP server has no streaming route (404/405).
 */
export async function streamChatMessage(payload, { onDelta } = {}) {
  let res;
  try {
    res = await fetch(ADVISOR_ROUTES.chatStream, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(
      "Could not reach the advisor. Check your connection and that the advisor service is running.",
    );
  }
  if (res.status === 404 || res.status === 405) {
    throw new StreamUnavailableError("Streaming route not available");
  }
  if (!res.ok) {
    throw new Error(friendlyHttpError(res.status));
  }
  const contentType = res.headers.get("content-type") || "";
  if (!res.body || !contentType.includes("text/event-stream")) {
    throw new StreamUnavailableError("Server did not stream");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Returns the final response for "done", throws for "error", otherwise undefined.
  const handleEvent = (block) => {
    let event = "message";
    const dataLines = [];
    block.split("\n").forEach((line) => {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
    });
    if (!dataLines.length) return undefined;
    let data;
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch {
      return undefined;
    }
    if (event === "delta") {
      if (onDelta && typeof data.text === "string") onDelta(data.text);
      return undefined;
    }
    if (event === "error") {
      throw new Error(data.detail || "The advisor service encountered an error. Please try again.");
    }
    if (event === "done") {
      if (!validChatResponse(data)) {
        throw new Error("The advisor returned an unexpected response. Please try again.");
      }
      return data;
    }
    return undefined;
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      if (done) buffer += decoder.decode();
      buffer = buffer.replace(/\r\n/g, "\n");
      let split = buffer.indexOf("\n\n");
      while (split !== -1) {
        const final = handleEvent(buffer.slice(0, split));
        if (final) return final;
        buffer = buffer.slice(split + 2);
        split = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    const final = buffer.trim() ? handleEvent(buffer) : undefined;
    if (final) return final;
  } finally {
    reader.cancel().catch(() => {});
  }
  throw new Error("The answer was interrupted. Please try again.");
}

export async function submitFeedback(messageId, feedbackType, sessionId) {
  return advisorFetch(ADVISOR_ROUTES.feedback, {
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
  return advisorFetch(ADVISOR_ROUTES.safeguardingConfirm, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
