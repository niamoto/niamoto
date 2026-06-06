# Legacy Feedback Worker

This document records the network feedback system that existed before Niamoto
switched to local diagnostic report generation. The legacy system is kept here
only as restoration context. The active application no longer depends on a
Cloudflare Worker, R2 bucket, GitHub token, or feedback API key.

## Current Active Behavior

The app now generates a local Markdown diagnostic report from the feedback
modal. The report is designed to be readable by a user and copyable into a
GitHub issue.
The report includes:

- feedback type, title, and optional description
- redacted app context
- recent console errors, failed API requests, navigation history, crashes, and
  local state snapshot when available
- optional screenshot embedded as a data URL

No network request is made to submit feedback, and the FastAPI app does not
register `/api/feedback/submit`.

## Legacy Architecture

The previous flow had three parts:

1. React collected the feedback payload and screenshot.
2. FastAPI exposed `POST /api/feedback/submit` and relayed the multipart body
   to a configured public endpoint.
3. The Cloudflare Worker at `workers/niamoto-feedback-proxy` uploaded an
   optional screenshot to R2 and created a GitHub issue.

The worker code is still present under:

```text
workers/niamoto-feedback-proxy/
```

The worker expected:

- `POST /feedback`
- multipart field `payload`, containing JSON
- optional multipart field `screenshot`, normally `image/jpeg`
- header `X-Feedback-Key`

The worker bindings and secrets were:

- `FEEDBACK_BUCKET`: R2 bucket for screenshots
- `R2_PUBLIC_URL`: public base URL for uploaded screenshots
- `GITHUB_REPO`: target repository, for example `owner/repo`
- `GITHUB_TOKEN`: GitHub token allowed to create issues
- `FEEDBACK_API_KEY`: shared secret compared with `X-Feedback-Key`

The app-side build/runtime variables were:

- `NIAMOTO_FEEDBACK_WORKER_URL`
- `NIAMOTO_FEEDBACK_API_KEY`
- legacy aliases: `FEEDBACK_WORKER_URL`, `FEEDBACK_API_KEY`,
  `VITE_FEEDBACK_WORKER_URL`, `VITE_FEEDBACK_API_KEY`

## Legacy Security Model

The old FastAPI proxy existed so the frontend never exposed GitHub or R2
credentials. It also:

- rejected missing feedback configuration
- rejected private or invalid feedback endpoint URLs
- revalidated DNS immediately before forwarding
- pinned the resolved public addresses during the outbound request
- limited screenshots before forwarding them

The worker then validated the shared `X-Feedback-Key` before touching R2 or
GitHub.

## Restoration Checklist

Only restore this system if a maintained public relay exists. Do not point
released builds at personal infrastructure.

To restore the legacy network flow:

1. Reintroduce the FastAPI feedback router at
   `src/niamoto/gui/api/routers/feedback.py` from Git history before the local
   report migration.
2. Register it in `src/niamoto/gui/api/app.py` with:

   ```python
   app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
   ```

3. Change `src/niamoto/gui/ui/src/features/feedback/lib/feedback-api.ts` back
   to posting `FormData` to `/api/feedback/submit`.
4. Restore the build-time normalization in `build_scripts/build_desktop.sh` if
   packaged desktop builds should embed or pass feedback worker settings.
5. Configure a maintained worker-compatible service and secrets:

   ```text
   NIAMOTO_FEEDBACK_WORKER_URL=https://example-feedback-relay.example
   NIAMOTO_FEEDBACK_API_KEY=...
   ```

6. Keep the frontend from sending worker URLs or API keys in form fields. The
   backend should read trusted configuration from its environment only.
7. Restore or recreate tests covering:

   - frontend posts only to `/api/feedback/submit`
   - frontend does not send worker config or secrets
   - backend rejects missing config
   - backend rejects private feedback endpoints
   - backend forwards screenshot and payload to `/feedback`
   - worker rejects bad `X-Feedback-Key`
   - worker creates GitHub issues and handles R2 failures without losing the
     feedback body

## Preferred Future Alternative

If someone wants shared feedback collection later, prefer a neutral,
project-owned endpoint with clear maintainers and documented credentials. The
local report flow should remain available as a no-infrastructure fallback.
