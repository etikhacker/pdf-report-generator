# Implementation Plan

1. **Setup** — create FastAPI app, health endpoint, dependency file, and test harness.
2. **Data** — create schema and safe-to-rerun shop seed script with 200 orders.
3. **Aggregation** — implement one report object backed by four SQL sections.
4. **Rendering** — build printable HTML and Playwright PDF generation.
5. **API** — add report bookkeeping and JSON/file endpoints.
6. **Idempotency** — reuse today's report unless `force` is true.
7. **Documentation/verification** — generate proof PDF and screenshot, write README, run tests and manual curl checks.

Risks: Chromium may not be installed; install it with `playwright install chromium`. SQLite connections are short-lived and safe for this single-process assignment. Generated files remain outside Git.
