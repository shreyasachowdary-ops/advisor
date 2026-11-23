import { useCallback, useRef, useState } from "react";
import { confirmSafeguarding, sendChatMessage, submitFeedback } from "../services/api.js";

export function useChat({ audience, ageBand }) {
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
      id: crypto.randomUUID(),
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
      const response = await sendChatMessage(payload);
      rememberSession(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          userQuery: trimmed,
          response,
          feedback: null,
        },
      ]);
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
      const response = await sendChatMessage({
        ...payload,
        session_id: sessionIdRef.current || payload.session_id || undefined,
      });
      rememberSession(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          userQuery: payload.message,
          response,
          feedback: null,
        },
      ]);
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
