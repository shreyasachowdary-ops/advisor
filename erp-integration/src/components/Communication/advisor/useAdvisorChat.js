import { useCallback, useRef, useState } from "react";
import {
  StreamUnavailableError,
  confirmSafeguarding,
  sendChatMessage,
  streamChatMessage,
  submitFeedback,
} from "./advisorApi";

// Local React keys only. crypto.randomUUID() is unavailable on plain-http ERP pages.
let localIdCounter = 0;
const newLocalId = () => `msg-${Date.now()}-${++localIdCounter}`;

// How often streamed text is drawn. Pieces arrive ~40 times a second; 50 ms keeps it smooth.
const STREAM_FLUSH_MS = 50;

/**
 * Gets one answer, showing text while it is written when the ERP server supports streaming.
 * The assistant message appears with the first words (streamingText) and gets its full
 * response, which replaces the streamed text, once the answer is complete.
 */
async function fetchAnswer(payload, userQuery, setMessages) {
  const localId = newLocalId();
  let streamed = "";
  let shown = false;
  let timer = null;

  // React may run state updaters later, so each one gets fixed values, not live variables.
  const flush = () => {
    timer = null;
    const text = streamed;
    const add = !shown;
    shown = true;
    setMessages((current) =>
      add
        ? [
            ...current,
            { id: localId, role: "assistant", userQuery, streamingText: text, response: null, feedback: null },
          ]
        : current.map((m) => (m.id === localId ? { ...m, streamingText: text } : m)),
    );
  };

  const onDelta = (text) => {
    streamed += text;
    if (!shown) flush(); // first words show immediately
    else if (!timer) timer = setTimeout(flush, STREAM_FLUSH_MS);
  };

  let response;
  try {
    response = await streamChatMessage(payload, { onDelta });
  } catch (err) {
    if (timer) clearTimeout(timer);
    if (shown) setMessages((current) => current.filter((m) => m.id !== localId)); // drop partial answer
    if (!(err instanceof StreamUnavailableError)) throw err;
    response = await sendChatMessage(payload); // ERP server without the streaming route
    shown = false;
  }
  if (timer) clearTimeout(timer);

  const finished = { id: localId, role: "assistant", userQuery, response, feedback: null };
  const replace = shown;
  setMessages((current) =>
    replace ? current.map((m) => (m.id === localId ? finished : m)) : [...current, finished],
  );
  return response;
}

export function useAdvisorChat({ audience, ageBand }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const sessionIdRef = useRef(null);
  const loadingRef = useRef(false);
  const lastPayloadRef = useRef(null);

  const rememberSession = (nextId) => {
    if (!nextId) return;
    sessionIdRef.current = nextId;
    setSessionId(nextId);
  };

  const sendMessage = useCallback(async (message) => {
    const trimmed = message.trim();
    if (!trimmed || loadingRef.current) return;

    const userMessage = {
      id: newLocalId(),
      role: "user",
      content: trimmed,
    };
    const payload = {
      message: trimmed,
      audience,
      age_band: ageBand,
      language: "en",
      session_id: sessionIdRef.current || undefined,
    };

    lastPayloadRef.current = payload;
    loadingRef.current = true;
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const response = await fetchAnswer(payload, trimmed, setMessages);
      rememberSession(response.session_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We couldn't get a response right now. Please try again.",
      );
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [ageBand, audience]);

  const retryLastMessage = useCallback(async () => {
    const payload = lastPayloadRef.current;
    if (!payload || loadingRef.current) return;

    loadingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAnswer(
        { ...payload, session_id: sessionIdRef.current || payload.session_id || undefined },
        payload.message,
        setMessages,
      );
      rememberSession(response.session_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We couldn't get a response right now. Please try again.",
      );
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, []);

  const submitMessageFeedback = useCallback(async (localMessageId, feedbackType, apiMessageId, apiSessionId) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === localMessageId ? { ...message, feedback: feedbackType } : message,
      ),
    );
    try {
      await submitFeedback(apiMessageId, feedbackType, apiSessionId);
    } catch {
      /* PoC: keep local selection even if logging fails */
    }
  }, []);

  const confirmSafeguardingFlag = useCallback(async (localMessageId, response, userSummary) => {
    if (!response?.message_id) return;
    const result = await confirmSafeguarding({
      message_id: response.message_id,
      session_id: response.session_id,
      category: response.safeguarding_category || "urgent_concern",
      severity: "critical",
      user_summary: (userSummary || "").slice(0, 2000),
      user_confirmed: true,
    });
    setMessages((current) =>
      current.map((message) =>
        message.id === localMessageId
          ? {
              ...message,
              response: {
                ...message.response,
                safeguarding_event_id: result?.safeguarding_event_id ?? null,
                requires_confirmation: false,
              },
            }
          : message,
      ),
    );
  }, []);

  return {
    messages,
    loading,
    error,
    sessionId,
    sendMessage,
    retryLastMessage,
    submitMessageFeedback,
    confirmSafeguardingFlag,
  };
}
