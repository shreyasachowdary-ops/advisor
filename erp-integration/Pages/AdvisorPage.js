/**
 * Parent/Teacher Agentic Advisor — canonical ERP page (same folder pattern as GenerateNotice.js).
 * Deploy: copy to lnpl_erp_dev_v1/src/components/Communication/AdvisorPage.js
 * App.js: import AdvisorPage from "./Communication/AdvisorPage.js";
 *
 * Browser: same-origin /api/advisor/* only (website server proxies to Advisor backend).
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import Navbar from "../navbar";

/** Same-origin advisor API (website server forwards to Advisor Agent backend). */
const ADVISOR_ROUTES = {
  health: "/api/advisor/health",
  chat: "/api/advisor/chat",
  feedback: "/api/advisor/feedback",
  safeguardingConfirm: "/api/advisor/safeguarding/confirm",
};

const AGE_OPTIONS = [
  { value: "2_years", label: "2 years" },
  { value: "3_years", label: "3 years" },
  { value: "4_years", label: "4 years" },
  { value: "5_years", label: "5 years" },
];

class AdvisorApiError extends Error {
  constructor(kind, message, status = 0) {
    super(message);
    this.name = "AdvisorApiError";
    this.kind = kind;
    this.status = status;
  }
}

async function readErrorDetail(res) {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    }
    if (body.message) return String(body.message);
    return JSON.stringify(body);
  } catch {
    return res.statusText || "Unknown error";
  }
}

function httpErrorFromResponse(res, detail) {
  const status = res.status;
  if (status === 422) {
    return new AdvisorApiError(
      "validation",
      `The advisor could not process that request (validation error 422). ${detail}`,
      status,
    );
  }
  if (status === 503) {
    return new AdvisorApiError(
      "unavailable",
      `The advisor service is temporarily unavailable (503). Try again shortly.`,
      status,
    );
  }
  if (status >= 500) {
    return new AdvisorApiError(
      "server",
      `The advisor service encountered an error (${status}). ${detail}`,
      status,
    );
  }
  return new AdvisorApiError(
    "http",
    `Advisor request failed (${status}). ${detail}`,
    status,
  );
}

async function advisorFetch(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new AdvisorApiError(
      "network",
      "Could not reach the advisor service. Check network connectivity and that /api/advisor routes are configured on the website server.",
      0,
    );
  }
  return res;
}

async function sendChat(payload) {
  const res = await advisorFetch(ADVISOR_ROUTES.chat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw httpErrorFromResponse(res, detail);
  }
  return res.json();
}

async function sendFeedback(rating, messageId, sessionId) {
  const res = await advisorFetch(ADVISOR_ROUTES.feedback, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, message_id: messageId, session_id: sessionId }),
  });
  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw httpErrorFromResponse(res, detail);
  }
}

async function confirmSafeguarding(body) {
  const res = await advisorFetch(ADVISOR_ROUTES.safeguardingConfirm, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw httpErrorFromResponse(res, detail);
  }
  return res.json();
}

function chatErrorMessage(err) {
  if (err instanceof AdvisorApiError) {
    return err.message;
  }
  return "An unexpected error occurred while contacting the advisor.";
}

function RiskBanner({ riskLevel }) {
  if (!riskLevel || riskLevel === "normal") return null;
  const urgent = riskLevel === "urgent";
  return (
    <div
      className={`p-3 rounded mb-2 text-sm ${
        urgent
          ? "bg-red-50 border border-red-300 text-red-900"
          : "bg-yellow-50 border border-yellow-300 text-yellow-900"
      }`}
    >
      <strong>{urgent ? "Urgent — Safeguarding" : "Referral Recommended"}</strong>
      <p className="mt-1">
        Please contact your school safeguarding lead or a trained professional.
      </p>
    </div>
  );
}

function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-2 text-xs text-gray-600 text-left">
      <strong>Sources:</strong>
      <ul className="list-disc pl-4">
        {sources.map((s) => (
          <li key={s.chunk_id}>
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 underline"
            >
              {s.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FeedbackControls({ messageId, sessionId }) {
  const rate = (rating) => {
    sendFeedback(rating, messageId, sessionId).catch(() => {
      /* PoC: silent fail on feedback */
    });
  };

  return (
    <div className="mt-2 flex gap-2 text-xs">
      <span className="text-gray-500">Helpful?</span>
      <button type="button" onClick={() => rate("helpful")} className="text-green-700">
        Yes
      </button>
      <button type="button" onClick={() => rate("not_helpful")} className="text-gray-700">
        No
      </button>
      <button type="button" onClick={() => rate("unsafe")} className="text-red-700">
        Unsafe
      </button>
    </div>
  );
}

function SafeguardingConfirmation({ response, userQuery, onConfirmed }) {
  const { risk_level, requires_confirmation, safeguarding_event_id } = response;
  if (risk_level !== "urgent" || !requires_confirmation || safeguarding_event_id) {
    return null;
  }

  const handleConfirm = async () => {
    try {
      const result = await confirmSafeguarding({
        message_id: response.message_id,
        session_id: response.session_id,
        category: response.safeguarding_category || "urgent_concern",
        severity: "critical",
        user_summary: (userQuery || "").slice(0, 2000),
        user_confirmed: true,
      });
      onConfirmed(result);
    } catch (err) {
      const msg =
        err instanceof AdvisorApiError
          ? err.message
          : "Could not submit safeguarding log";
      alert(msg);
    }
  };

  return (
    <div className="mt-2 p-2 border border-red-200 rounded text-sm">
      <p>
        Optional PoC log for safeguarding lead (does not replace contacting a professional):
      </p>
      <button type="button" className="mt-1 text-red-800 underline" onClick={handleConfirm}>
        I confirm — log concern for safeguarding follow-up
      </button>
    </div>
  );
}

function ChatMessage({ message, messageIndex, onUseFollowUp, onSafeguardingConfirmed }) {
  const { role, content, response, userQuery } = message;
  const isUser = role === "user";

  return (
    <div className={`mb-4 ${isUser ? "text-right" : ""}`}>
      {response && <RiskBanner riskLevel={response.risk_level} />}
      <div
        className={`inline-block p-3 rounded max-w-[85%] text-left whitespace-pre-wrap ${
          isUser ? "bg-indigo-100" : "bg-gray-50"
        }`}
      >
        {content}
      </div>
      {response && <SourceList sources={response.sources} />}
      {response?.suggested_follow_up && response.risk_level === "normal" && (
        <button
          type="button"
          onClick={() => onUseFollowUp(response.suggested_follow_up)}
          className="mt-2 text-xs text-indigo-600 underline block"
        >
          {response.suggested_follow_up}
        </button>
      )}
      {response && (
        <SafeguardingConfirmation
          response={response}
          userQuery={userQuery}
          onConfirmed={(result) => onSafeguardingConfirmed(messageIndex, result)}
        />
      )}
      {response && response.risk_level === "normal" && (
        <FeedbackControls
          messageId={response.message_id}
          sessionId={response.session_id}
        />
      )}
    </div>
  );
}

function AdvisorChat() {
  const [audience, setAudience] = useState("parent");
  const [ageBand, setAgeBand] = useState("4_years");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");
  const bottomRef = useRef(null);

  useEffect(() => {
    advisorFetch(ADVISOR_ROUTES.health)
      .then((r) => r.json())
      .then((d) => setApiStatus(d.status === "ok" ? "online" : "offline"))
      .catch(() => setApiStatus("offline"));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSafeguardingConfirmed = useCallback((index, result) => {
    setMessages((prev) =>
      prev.map((m, idx) =>
        idx === index
          ? {
              ...m,
              response: {
                ...m.response,
                safeguarding_event_id: result.safeguarding_event_id,
                requires_confirmation: false,
              },
            }
          : m,
      ),
    );
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const response = await sendChat({
        message: userMsg,
        audience,
        age_band: ageBand,
        language: "en",
        session_id: sessionId,
      });
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, response, userQuery: userMsg },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: chatErrorMessage(err) },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const audienceButtonClass = (value) =>
    `px-4 py-1 rounded ${
      audience === value ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-700"
    }`;

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-indigo-800">Parent / Teacher Advisor</h2>
        <p className="text-sm text-gray-600">
          Practical guidance for preschool children (ages 2–5). General educational advice only
          — not diagnosis or counselling.
        </p>
        <p className="text-xs text-gray-500 mt-1">
          API:{" "}
          {apiStatus === "online"
            ? "Connected (via /api/advisor)"
            : "Offline — configure website /api/advisor proxy to Advisor backend"}
        </p>
      </div>

      <div className="flex flex-wrap gap-4 mb-4 p-3 bg-white rounded shadow">
        <div className="flex gap-2">
          <button type="button" onClick={() => setAudience("parent")} className={audienceButtonClass("parent")}>
            Parent
          </button>
          <button type="button" onClick={() => setAudience("teacher")} className={audienceButtonClass("teacher")}>
            Teacher
          </button>
        </div>
        <select
          value={ageBand}
          onChange={(e) => setAgeBand(e.target.value)}
          className="border rounded px-2 py-1"
        >
          {AGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded shadow min-h-[320px] max-h-[480px] overflow-y-auto p-4 mb-4">
        {messages.length === 0 && (
          <p className="text-gray-400 text-center mt-8">
            Ask about routines, behaviour, play-based learning, or parent–teacher communication.
          </p>
        )}
        {messages.map((msg, i) => (
          <ChatMessage
            key={`${msg.role}-${i}-${msg.response?.message_id || ""}`}
            message={msg}
            messageIndex={i}
            onUseFollowUp={setInput}
            onSafeguardingConfirmed={handleSafeguardingConfirmed}
          />
        ))}
        {loading && <p className="text-gray-400 italic">Thinking...</p>}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question..."
          disabled={loading}
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-indigo-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}

function AdvisorPage() {
  return (
    <>
      <Navbar />
      <AdvisorChat />
    </>
  );
}

export default AdvisorPage;
