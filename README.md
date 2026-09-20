# PDF Report Generator

A small Python/FastAPI reporting pipeline for the FlyRank Backend Track A8 assignment. It follows the complete **query → render → store → serve** flow: SQLite aggregates 200 shop orders, Playwright prints a real multi-page A4 PDF, the PDF is stored on disk, and the API returns a download link instead of embedding file bytes in JSON.

## Dataset

This implementation uses **Option A — the little shop**. `seed.py` creates 200 invented orders across six products, with amounts from $5 to $200 and dates from the last 30 days. The seed is safe to run repeatedly because it deletes existing orders before inserting the clean dataset.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python seed.py
uvicorn app:app --reload --port 8000
```

In another terminal:

```bash
curl -i http://localhost:8000/health
curl -i -X POST http://localhost:8000/reports
curl -i http://localhost:8000/reports/1
curl -o my-report.pdf http://localhost:8000/reports/1/file
pdfinfo my-report.pdf | grep -E '^(Pages|Page size|Title):'
```

The POST can optionally accept `{"force": true}` to create a fresh report even when one already exists today.

## API

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/health` | Returns `{ "status": "ok" }`. |
| POST | `/reports` | Generates a report synchronously and returns `201` with `{id, file}`. A same-day duplicate returns `200` with the existing report. |
| GET | `/reports/{id}` | Returns report metadata and the file link. Unknown IDs return `404`. |
| GET | `/reports/{id}/file` | Serves the stored PDF from disk as `application/pdf`. |

## Aggregation SQL

The report is driven by these SQL queries inside `get_report_data()`:

```sql
-- Two totals
SELECT COUNT(*) AS total_orders,
       COALESCE(SUM(amount), 0) AS total_revenue
FROM orders;

-- Top five products by revenue
SELECT product,
       COUNT(*) AS order_count,
       ROUND(SUM(amount), 2) AS revenue
FROM orders
GROUP BY product
ORDER BY revenue DESC
LIMIT 5;

-- Orders per day for the last seven days
SELECT created_at,
       COUNT(*) AS order_count
FROM orders
WHERE date(created_at) >= date('now', '-6 day')
GROUP BY created_at
ORDER BY created_at;

-- Full detail table used in the PDF
SELECT id, customer, product, amount, created_at
FROM orders
ORDER BY created_at DESC, id DESC;
```

## Checkpoint proof

A clean run produced the following results:

```text
GET /health                 -> 200 {"status":"ok"}
First POST /reports         -> 201 {"id":1,"file":"/reports/1/file"}
Second POST /reports        -> 200 {"id":1,"file":"/reports/1/file"}
SQLite order count          -> 200
SQLite report count         -> 1
Downloaded file             -> PDF document, version 1.4, 6 page(s)
Page size                   -> A4
```

The generated PDF is deliberately long enough to exercise page breaks. Print CSS uses `thead { display: table-header-group; }` so headers repeat and `tr { break-inside: avoid; page-break-inside: avoid; }` so rows are not cut in half.

![Page 1 of generated sales report](docs/pdf-page-1.png)

## Why synchronous generation is acceptable here

For this assignment, the endpoint intentionally performs query, rendering, and storage inside the request so the visible wait can be observed. In production, I would move generation to a background job when PDF rendering becomes slow enough to risk request timeouts or when multiple users need reports concurrently; the API would then return `202` and expose a pending/done status.

## Idempotency

The same-day check protects against double-clicks, retries, and network clients repeating a request, so one user action creates one report file. A missing check in a billing or email-report workflow could charge a customer twice or send the same customer two paid notifications. `force: true` is available when an intentionally fresh report is needed.

## Tests

```bash
pytest -q
```

The test suite covers health, safe-to-rerun seeding, aggregation, print CSS, PDF generation, file download, 404 handling, same-day reuse, and forced regeneration.
