# Make `/advisor` public (no login)

> **Status (2026-11-05): reverted.** `/advisor` is back inside the dashboard and needs login
> (roles: Parent, Teacher, SchoolAdmin, principal, lms_super). Keep this file only as a record
> of how to make it public again.

Goal: anyone can open `https://smartstems.in:3443/advisor` and chat, without logging in.

Login is enforced in three places. All three must change, then rebuild the React app and restart Flask.

## 1. `src/components/App.js` — session check (`SecurityWrapper`)

Add `/advisor` to `publicRoutes` so unauthenticated visitors are not redirected to `/login`:

```js
  const publicRoutes = [
  "/",
  "/login",
  "/forgot-password",
  "/verify",
  "/api/verify",
  "/developer-firewall-access",
  "/advisor" // Parent/Teacher Advisor is public (no login)
];
```

## 2. `src/components/App.js` — move the route out of the dashboard

**Remove** this block (it is inside the `<RoleRoute> <DashboardLayout />` group, near the end of `<Routes>`):

```jsx
                <Route
                  path="/advisor"
                  element={
                    <RoleRoute
                      allowedRoles={["Parent", "Teacher", "SchoolAdmin", "principal", "lms_super"]}
                    >
                      <AdvisorPage />
                    </RoleRoute>
                  }
                />
```

**Add** it as a top-level public route, next to `<Route path="/" element={<LilyMontessori />} />`:

```jsx
              {/* Parent/Teacher Advisor: public page, no login or role check */}
              <Route path="/advisor" element={<AdvisorPage />} />
```

(The page is no longer shown inside the dashboard sidebar layout, because that layout needs a logged-in user.)

## 3. `Backend/app.py` — API proxy routes

On each of these four routes, delete the two lines `@login_required` and `@role_required(ADVISOR_API_ROLES)`:

- `/api/advisor/health` (`advisor_health`)
- `/api/advisor/chat` (`advisor_chat`)
- `/api/advisor/feedback` (`advisor_feedback`)
- `/api/advisor/safeguarding/confirm` (`advisor_safeguarding_confirm`)

Example result:

```python
@app.route("/api/advisor/chat", methods=["POST"])
def advisor_chat():
    ...
```

If `/api/advisor/chat/stream` has been added (see `flask_advisor_chat_stream.py.txt`), remove the same two decorators there too.

Nginx (`location /api/advisor`) needs no change.

## Caveat

With no login, anyone on the internet can send messages, and every message uses the advisor's LLM.
Consider a simple per-IP rate limit on `/api/advisor/chat` (for example Flask-Limiter, ~20 requests/minute).
