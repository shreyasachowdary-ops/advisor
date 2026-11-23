# ERP Integration — Copy Instructions

**Canonical source:** `erp-integration/src/components/Communication/AdvisorPage.js` (same folder as `GenerateNotice.js`).  
It renders the ChildConnect UI from `erp-integration/src/components/Communication/advisor/` — a port of
`reference_frontend/src` with API calls via `getConfig()` + `/api/advisor/*` (`advisor/advisorApi.js`) and CSS scoped
under `.cc-root` (`advisor/childconnect.css`). Copy **both** `AdvisorPage.js` and the `advisor/` folder.  
`Pages/AdvisorPage.js` and `src/Pages/AdvisorPage.js` are old copies of the previous simple page. Run `apply-to-erp.ps1` to copy into the ERP.

## 1. Apply integration (recommended)

```powershell
cd advisor\erp-integration
.\apply-to-erp.ps1 -ErpRoot "D:\path\to\lnpl_erp_dev_v1"
```

## 2. Website proxy routes (`/api/advisor/*`)

`AdvisorPage.js` calls **same-origin** routes only (like Notice Agent’s `/api/notice-agent/...`).

Your ERP **server** must forward:

- `/api/advisor/health` → Advisor `{backend}/api/health`
- `/api/advisor/chat` → `{backend}/api/chat`
- `/api/advisor/chat/stream` → `{backend}/api/chat/stream` (optional, shows the answer word by word — see below)
- `/api/advisor/feedback` → `{backend}/api/feedback`
- `/api/advisor/safeguarding/confirm` → `{backend}/api/safeguarding/confirm`

See [patches/ADVISOR_WEBSITE_PROXY.md](patches/ADVISOR_WEBSITE_PROXY.md). Implement next to your existing Notice Agent proxy routes.

`apply-to-erp.ps1` copies `server/registerAdvisorProxy.js` into the ERP. Wire it in the **same server entry** as `/api/notice-agent/*`:

```js
const { registerAdvisorProxy } = require("./registerAdvisorProxy");
registerAdvisorProxy(app);
```

Set **`ADVISOR_BACKEND_URL`** (or equivalent) on the **server** to the running Advisor service (e.g. `http://127.0.0.1:8787`). The browser must not use port 8787 directly.

### Streaming answers (`/api/advisor/chat/stream`)

The advisor page shows the first words in about 1 second instead of waiting ~10 seconds for the
whole answer, when the ERP Flask server has this route. Paste the block from
[patches/flask_advisor_chat_stream.py.txt](patches/flask_advisor_chat_stream.py.txt) into
`Backend/app.py` right after `advisor_chat()`.

- Same access as `/api/advisor/chat` (public since 2026-10-29); the old route stays.
  Already applied to the ERP `Backend/app.py` on 2026-10-29.
- Order does not matter: until the route exists the page uses `/api/advisor/chat` as before.
  The Advisor backend must be restarted with the new code for streaming to work.
- No nginx or waitress change is needed (tested with waitress 3.0.2; the route sends
  `X-Accel-Buffering: no`, and nginx does not gzip `text/event-stream`).

## 3. Backend CORS

In `advisor/backend/.env`, set `CORS_ORIGINS` to include your ERP origin (scheme + host + port).

## 4. Start services

```bash
cd advisor/backend && uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload
```

Open ERP → **Parent/Teacher Advisor** or `/advisor`.
