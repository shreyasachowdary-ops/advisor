/**
 * Express-style Advisor API proxy (mirror Notice Agent server integration).
 *
 * Usage in ERP Node server (next to notice-agent routes):
 *   const { registerAdvisorProxy } = require("./registerAdvisorProxy");
 *   registerAdvisorProxy(app);
 *
 * Environment: ADVISOR_BACKEND_URL (server-side only), e.g. http://127.0.0.1:8787
 */

function getBackendBase(options) {
  const fromOpts = options && options.backendUrl;
  const fromEnv = process.env.ADVISOR_BACKEND_URL;
  const base = (fromOpts || fromEnv || "http://127.0.0.1:8787").replace(/\/+$/, "");
  return base;
}

async function forwardJson(req, res, backendPath, base) {
  const url = `${base}${backendPath}`;
  const init = {
    method: req.method,
    headers: { "Content-Type": "application/json" },
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = JSON.stringify(req.body ?? {});
  }
  const upstream = await fetch(url, init);
  const text = await upstream.text();
  res.status(upstream.status);
  const contentType = upstream.headers.get("content-type");
  if (contentType) {
    res.set("Content-Type", contentType);
  }
  res.send(text);
}

// Passes the advisor's Server-Sent Events through piece by piece (no buffering).
async function forwardStream(req, res, backendPath, base) {
  const upstream = await fetch(`${base}${backendPath}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(req.body ?? {}),
  });
  if (!upstream.ok || !upstream.body) {
    res.status(upstream.status);
    const contentType = upstream.headers.get("content-type");
    if (contentType) res.set("Content-Type", contentType);
    res.send(await upstream.text());
    return;
  }
  res.status(200);
  res.set({ "Content-Type": "text/event-stream", "Cache-Control": "no-cache", "X-Accel-Buffering": "no" });
  if (res.flushHeaders) res.flushHeaders();
  const reader = upstream.body.getReader();
  req.on("close", () => reader.cancel().catch(() => {}));
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    res.write(Buffer.from(value));
  }
  res.end();
}

function registerAdvisorProxy(app, options = {}) {
  const base = getBackendBase(options);

  app.get("/api/advisor/health", (req, res) => {
    forwardJson(req, res, "/api/health", base).catch(() => {
      res.status(503).json({ detail: "Advisor backend unavailable" });
    });
  });

  app.post("/api/advisor/chat", (req, res) => {
    forwardJson(req, res, "/api/chat", base).catch(() => {
      res.status(503).json({ detail: "Advisor backend unavailable" });
    });
  });

  app.post("/api/advisor/chat/stream", (req, res) => {
    forwardStream(req, res, "/api/chat/stream", base).catch(() => {
      if (!res.headersSent) res.status(503).json({ detail: "Advisor backend unavailable" });
      else res.end();
    });
  });

  app.post("/api/advisor/feedback", (req, res) => {
    forwardJson(req, res, "/api/feedback", base).catch(() => {
      res.status(503).json({ detail: "Advisor backend unavailable" });
    });
  });

  app.post("/api/advisor/safeguarding/confirm", (req, res) => {
    forwardJson(req, res, "/api/safeguarding/confirm", base).catch(() => {
      res.status(503).json({ detail: "Advisor backend unavailable" });
    });
  });
}

module.exports = { registerAdvisorProxy, getBackendBase };
