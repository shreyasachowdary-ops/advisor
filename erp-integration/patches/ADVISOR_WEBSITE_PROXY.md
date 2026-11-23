# Advisor website proxy (required for `AdvisorPage.js`)

The React page calls **same-origin** routes only:

| Website route (browser) | Forward to Advisor Agent backend |
|-------------------------|----------------------------------|
| `GET /api/advisor/health` | `GET {ADVISOR_BACKEND_URL}/api/health` |
| `POST /api/advisor/chat` | `POST {ADVISOR_BACKEND_URL}/api/chat` |
| `POST /api/advisor/chat/stream` (optional) | `POST {ADVISOR_BACKEND_URL}/api/chat/stream` — Server-Sent Events; forward without buffering |
| `POST /api/advisor/feedback` | `POST {ADVISOR_BACKEND_URL}/api/feedback` |
| `POST /api/advisor/safeguarding/confirm` | `POST {ADVISOR_BACKEND_URL}/api/safeguarding/confirm` |

`ADVISOR_BACKEND_URL` is **server-side only** (e.g. `http://127.0.0.1:8787` or an internal hostname). The browser must never use this URL.

**Streaming route:** the page tries `/api/advisor/chat/stream` first and falls back to
`/api/advisor/chat` on 404/405, so it is safe to add later. The proxy must pass the response
through as it arrives (no reading the whole body first) and send `X-Accel-Buffering: no` so
nginx does not hold it back. The ERP's Flask version is in
[flask_advisor_chat_stream.py.txt](flask_advisor_chat_stream.py.txt); the Express version is
in `server/registerAdvisorProxy.js`.

## Notice Agent pattern

This repository does **not** include the ERP server or Notice Agent source. On `lnpl_erp_dev_v1`, locate where `/api/notice-agent/message` (and related routes) are defined—typically:

- `setupProxy.js` / `package.json` `proxy` (Create React App dev server), or
- Express/Node API routes under `server/`, `api/`, or similar, or
- nginx / IIS reverse proxy rules in production.

Add Advisor routes **in the same place**, using the same forwarding style (http proxy, `fetch`, `axios`, etc.).

## Example: Express-style forwarder (adapt to your stack)

```js
const ADVISOR_BACKEND = process.env.ADVISOR_BACKEND_URL || "http://127.0.0.1:8787";

async function proxyAdvisor(req, res, backendPath) {
  const url = `${ADVISOR_BACKEND}${backendPath}`;
  const init = {
    method: req.method,
    headers: { "Content-Type": "application/json" },
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = JSON.stringify(req.body);
  }
  const upstream = await fetch(url, init);
  const text = await upstream.text();
  res.status(upstream.status).type(upstream.headers.get("content-type") || "application/json").send(text);
}

// app.get("/api/advisor/health", (req, res) => proxyAdvisor(req, res, "/api/health"));
// app.post("/api/advisor/chat", (req, res) => proxyAdvisor(req, res, "/api/chat"));
// app.post("/api/advisor/feedback", (req, res) => proxyAdvisor(req, res, "/api/feedback"));
// app.post("/api/advisor/safeguarding/confirm", (req, res) => proxyAdvisor(req, res, "/api/safeguarding/confirm"));
```

## Example: CRA `setupProxy.js` (dev only)

```js
const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  const target = process.env.ADVISOR_BACKEND_URL || "http://127.0.0.1:8787";
  app.use(
    "/api/advisor/health",
    createProxyMiddleware({ target, pathRewrite: { "^/api/advisor/health": "/api/health" } }),
  );
  app.use(
    "/api/advisor/chat",
    createProxyMiddleware({ target, pathRewrite: { "^/api/advisor/chat": "/api/chat" } }),
  );
  app.use(
    "/api/advisor/feedback",
    createProxyMiddleware({ target, pathRewrite: { "^/api/advisor/feedback": "/api/feedback" } }),
  );
  app.use(
    "/api/advisor/safeguarding/confirm",
    createProxyMiddleware({
      target,
      pathRewrite: { "^/api/advisor/safeguarding/confirm": "/api/safeguarding/confirm" },
    }),
  );
};
```

## Advisor backend (unchanged)

Keep running the existing Python service, e.g.:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Set `CORS_ORIGINS` on the Advisor backend to include the **ERP website origin** if the proxy does not strip origin (many server-side proxies avoid CORS entirely).

## Config note

`config_web.json` `advisor_base_url` is **no longer read by `AdvisorPage.js`**. Use `ADVISOR_BACKEND_URL` (or equivalent) on the **website server** for forwarding only.
