# Spec: PDF Report Generator

## Objective
Build a Python/FastAPI service that seeds a small SQLite orders dataset, aggregates it with SQL, renders a multi-page PDF through Playwright, stores the artifact on disk, and serves it by link. Repeated generation on the same day must reuse the existing report unless `force: true` is requested.

## Tech Stack
Python 3.11+, FastAPI, Uvicorn, SQLite (`sqlite3`), Playwright Chromium, pytest.

## Commands
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python seed.py
uvicorn app:app --reload --port 8000
pytest -q
```

## Project Structure
- `app.py`: database helpers, aggregation, HTML rendering, PDF generation, API routes.
- `seed.py`: deterministic-safe random seed generator for approximately 200 orders.
- `tests/`: unit and API tests.
- `reports/`: generated PDFs, ignored by Git.
- `tasks/`: implementation plan and checklist.

## Success Criteria
1. `GET /health` returns HTTP 200 and `{ "status": "ok" }`.
2. Running `seed.py` twice leaves exactly 200 orders.
3. `get_report_data()` returns totals, top products, last-seven-day daily counts, and all orders.
4. Generated PDF is a real, multi-page A4 PDF with repeated table headers and rows protected from page splitting.
5. `POST /reports` returns 201 for a new report and a file link; `GET /reports/{id}` returns metadata; `GET /reports/{id}/file` returns PDF bytes; unknown IDs return 404.
6. A second same-day POST returns 200 with the same ID and does not create another PDF; `force: true` creates a new report.
7. README contains setup, SQL, endpoint proof, idempotency explanation, screenshot, and background-job boundary sentence.

## Boundaries
- Always: parameterize SQL values, create report directories, validate file paths, and run tests before commits.
- Ask first: public GitHub publishing or any external account change.
- Never: commit `report.db`, generated PDFs, secrets, or browser binaries.
