# PDF Report Generator

This project is a complete solution for the **FlyRank Backend Track — Week 4 — Assignment A8**.

The goal is to build a backend reporting pipeline that turns database records into a real PDF report and makes that PDF available through an API link.

The complete pipeline is:

```text
SQLite database
      ↓
SQL aggregation
      ↓
HTML report template
      ↓
Playwright + Chromium
      ↓
PDF file
      ↓
Store the file on disk
      ↓
Serve the file through an API link
```

A client sends `POST /reports`. The server reads the order data, calculates the report statistics, builds an HTML document, renders it as a PDF, stores the PDF on disk, saves the report metadata, and returns a download link.

## Assignment objective

This assignment demonstrates the following backend concepts:

1. Working with a SQLite database;
2. Writing aggregation queries with `COUNT`, `SUM`, `GROUP BY`, `ORDER BY`, and `LIMIT`;
3. Building an HTML report from SQL results;
4. Converting HTML to PDF with a headless browser;
5. Storing generated artifacts on disk;
6. Serving files through an API endpoint;
7. Preventing duplicate reports when the same request is repeated;
8. Publishing a documented project to GitHub.

The main design rule is:

> Store the PDF once and return its address. Do not put PDF bytes inside JSON responses.

## Technology stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Main programming language |
| FastAPI | REST API framework |
| SQLite | Database and report metadata storage |
| Playwright | Headless Chromium PDF rendering |
| Uvicorn | ASGI server |
| Pytest | Automated tests |
| Git/GitHub | Version control and submission |

## Dataset

The assignment offered two dataset options. This implementation uses **Option A — The Little Shop**.

`seed.py` creates:

- 200 invented orders;
- six different products;
- order amounts between `$5` and `$200`;
- order dates from the last 30 days;
- a clean dataset every time the script is run.

The products are:

```text
Keyboard
Mouse
Monitor
USB Hub
Webcam
Headset
```

## Project structure

```text
pdf-report-generator/
├── app.py                    # FastAPI server, SQL, HTML, and PDF logic
├── seed.py                   # Creates the 200-order dataset
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration
├── Makefile                  # Common development commands
├── SPEC.md                   # Project specification
├── CHECKPOINTS.md            # Manual verification results
├── README.md                 # This documentation
├── tasks/
│   ├── plan.md               # Implementation plan
│   └── todo.md               # Stage checklist
├── scripts/
│   ├── report_data.py        # Prints aggregation data as JSON
│   └── render_report.py      # Creates a test PDF
├── tests/
│   └── test_app.py           # Unit and API tests
├── docs/
│   └── pdf-page-1.png        # Screenshot of the generated PDF
├── reports/                  # Generated PDFs; ignored by Git
└── report.db                 # SQLite database; ignored by Git
```

`report.db` and generated PDF files are local artifacts. They are listed in `.gitignore`, so the repository contains the source code and the seed recipe rather than generated data and browser output.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/etikhacker/pdf-report-generator.git
cd pdf-report-generator
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Playwright browser

```bash
playwright install chromium
```

Playwright uses a real Chromium browser to print the HTML page as a PDF. This installation step is required before generating reports.

## Seed the database

The database and tables are created automatically by the `init_db()` function in `app.py`. Create the order dataset with:

```bash
python seed.py
```

Expected output:

```text
Seeded 200 orders into .../report.db
```

The seed script is safe to run more than once:

```bash
python seed.py
python seed.py
```

After the second run, the database still contains 200 orders rather than 400. The script first deletes the existing rows and then inserts a clean set of 200 orders.

## Database schema

### `orders` table

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    product TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT NOT NULL
);
```

This table contains the source data used by the report.

### `reports` table

```sql
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

This table stores metadata for generated reports. The PDF itself is not stored in SQLite. Only its path and creation time are stored in the database.

## SQL aggregation

The report is built from the result of `get_report_data()`. That function runs several SQL queries.

### Total orders and total revenue

```sql
SELECT COUNT(*) AS total_orders,
       COALESCE(SUM(amount), 0) AS total_revenue
FROM orders;
```

This returns:

- `total_orders`: the number of orders;
- `total_revenue`: the sum of all order amounts.

### Top five products by revenue

```sql
SELECT product,
       COUNT(*) AS order_count,
       ROUND(SUM(amount), 2) AS revenue
FROM orders
GROUP BY product
ORDER BY revenue DESC
LIMIT 5;
```

In this query:

- `GROUP BY product` groups rows belonging to the same product;
- `SUM(amount)` calculates revenue per product;
- `ORDER BY revenue DESC` puts the highest revenue first;
- `LIMIT 5` keeps only the top five products.

### Orders per day for the last seven days

```sql
SELECT created_at,
       COUNT(*) AS order_count
FROM orders
WHERE date(created_at) >= date('now', '-6 day')
GROUP BY created_at
ORDER BY created_at;
```

This calculates the number of orders for each date in the last seven days.

### All orders for the detail table

```sql
SELECT id, customer, product, amount, created_at
FROM orders
ORDER BY created_at DESC, id DESC;
```

This query supplies the long detail table at the bottom of the PDF. The table is intentionally long so that the PDF page-break behavior can be tested.

Print the aggregation result as JSON with:

```bash
python scripts/report_data.py
```

or:

```bash
make data
```

## HTML-to-PDF rendering

The PDF is not drawn manually. First, `build_html()` creates an HTML document from the report data. The document contains:

- a report title;
- the generation date;
- a total orders card;
- a total revenue card;
- a top products table;
- a seven-day orders table;
- a full orders table.

Then `render_pdf()` launches Playwright and prints the HTML page:

```python
async with async_playwright() as playwright:
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    await page.set_content(html)
    await page.pdf(
        path=str(path),
        format="A4",
        print_background=True,
    )
    await browser.close()
```

Generated PDFs are stored in the `reports/` directory.

### Preventing broken table rows

Long tables can be split incorrectly by a browser. A row may be cut between two PDF pages, and a table header may disappear on the next page. The project uses print CSS to prevent this:

```css
thead {
    display: table-header-group;
}

tr {
    break-inside: avoid;
    page-break-inside: avoid;
}
```

This ensures that:

- the table header is repeated on new pages;
- table rows are not split across pages;
- the generated report remains readable.

Create a test PDF with:

```bash
python scripts/render_report.py
```

or:

```bash
make render
```

## Start the server

```bash
uvicorn app:app --reload --port 8000
```

The API is available at:

```text
http://localhost:8000
```

Interactive FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

## API endpoints

### `GET /health`

Checks whether the server is running.

Request:

```bash
curl -i http://localhost:8000/health
```

Response:

```http
HTTP/1.1 200 OK
```

```json
{
  "status": "ok"
}
```

### `POST /reports`

Generates a report. The endpoint performs the following steps:

1. Initializes the database if necessary;
2. Checks whether a report already exists for the current day;
3. Runs the aggregation queries when a new report is required;
4. Builds the HTML document;
5. Renders the HTML as a PDF with Playwright;
6. Stores the PDF as `reports/{id}.pdf`;
7. Saves report metadata in the `reports` table;
8. Returns a JSON response containing the file link.

Request:

```bash
curl -i -X POST http://localhost:8000/reports
```

Response for a new report:

```http
HTTP/1.1 201 Created
```

```json
{
  "id": 1,
  "file": "/reports/1/file"
}
```

The endpoint intentionally performs the complete pipeline inside the request. Therefore, the client may wait a few seconds while the browser renders the PDF. This behavior is allowed and expected for this assignment.

### `GET /reports`

Returns metadata for all generated reports.

```bash
curl -i http://localhost:8000/reports
```

Example response:

```json
[
  {
    "id": 1,
    "path": "reports/1.pdf",
    "created_at": "2026-09-20T18:53:34",
    "file": "/reports/1/file"
  }
]
```

This endpoint is an optional control-panel stretch feature.

### `GET /reports/{id}`

Returns metadata for one report.

```bash
curl -i http://localhost:8000/reports/1
```

Example response:

```json
{
  "id": 1,
  "path": "reports/1.pdf",
  "created_at": "2026-09-20T18:53:34",
  "file": "/reports/1/file"
}
```

An unknown report ID returns:

```text
GET /reports/999999 -> 404 Not Found
```

### `GET /reports/{id}/file`

Serves the stored PDF from disk.

```bash
curl -o my-report.pdf http://localhost:8000/reports/1/file
```

Verify that the downloaded file is a real PDF:

```bash
file my-report.pdf
pdfinfo my-report.pdf
```

The response content type is:

```text
application/pdf
```

The JSON endpoints never include the PDF bytes. Only the file endpoint transfers the PDF. This is the assignment's **store and link** principle.

## Idempotency

A user may click the Generate button twice, or a client may retry a request after a network interruption. If every request created a new PDF, duplicate artifacts would be produced unnecessarily.

Before generating a report, `POST /reports` checks whether a report already exists for the current date.

First request:

```bash
curl -i -X POST http://localhost:8000/reports
```

Response:

```text
201 Created
id: 1
```

Second request:

```bash
curl -i -X POST http://localhost:8000/reports
```

Response:

```text
200 OK
id: 1
```

The second request returns the same ID and does not create another PDF.

To intentionally create a fresh report, send `force: true`:

```bash
curl -i -X POST http://localhost:8000/reports \
  -H 'Content-Type: application/json' \
  -d '{"force": true}'
```

The `force` option skips the same-day reuse check and creates a new report ID.

This protects real systems from duplicate billing, duplicate emails, repeated exports, and unnecessary file generation.

## Tests

Run the test suite with:

```bash
pytest -q
```

or:

```bash
make test
```

The tests cover:

- the health endpoint;
- safe-to-repeat seeding;
- real SQL aggregation values;
- top-five product calculation;
- print CSS rules;
- real PDF generation;
- PDF file download;
- report metadata;
- 404 handling for unknown reports;
- same-day report reuse;
- forced regeneration;
- the report listing endpoint.

Verified result:

```text
5 passed
```

## Manual checkpoint evidence

A clean local run produced:

```text
GET /health                 -> 200 {"status":"ok"}
First POST /reports         -> 201 {"id":1,"file":"/reports/1/file"}
Second POST /reports        -> 200 {"id":1,"file":"/reports/1/file"}
SQLite order count          -> 200
SQLite report count         -> 1
Downloaded file             -> PDF document, version 1.4, 6 page(s)
Page size                   -> A4
Git commits                 -> 7 meaningful commits
```

Generated PDF screenshot:

![Generated sales report PDF](docs/pdf-page-1.png)

## When should this become a background job?

For this assignment, report generation is intentionally synchronous so the complete pipeline and the visible request delay can be observed.

A production system should move generation to a background job when:

- PDF rendering becomes slow;
- reports become much larger;
- many users generate reports at the same time;
- HTTP request timeouts become a risk;
- the client should not wait for the complete rendering process.

In a background-job design, `POST /reports` could immediately return `202 Accepted`. A worker would generate the report in the background, while `GET /reports/{id}` would expose a `pending`, `done`, or `failed` status. This improves the user experience but adds queue management, retries, status tracking, and error handling.

## Assignment requirements checklist

| Assignment requirement | Implementation |
|---|---|
| Health endpoint | `GET /health` |
| SQLite dataset | `orders` table with 200 seeded orders |
| Safe-to-run seed | `seed.py` clears old orders before inserting |
| SQL aggregation | Four query sections inside `get_report_data()` |
| HTML-to-PDF | `build_html()` plus Playwright `page.pdf()` |
| Clean page breaks | Repeating `thead` and `break-inside: avoid` |
| Generate report | `POST /reports` |
| Report metadata | `GET /reports/{id}` |
| File serving | `GET /reports/{id}/file` |
| Unknown ID handling | `404 Not Found` |
| Idempotency | Reuses the current day's report |
| Forced regeneration | `{ "force": true }` |
| GitHub submission | Public repository with 7 commits |
| Documentation | This README and PDF screenshot |

## GitHub repository

Public repository:

**https://github.com/etikhacker/pdf-report-generator**

The repository contains the source code, tests, SQL documentation, setup instructions, PDF screenshot, and seven meaningful commits. Generated database files, generated PDFs, and the virtual environment are excluded from Git.
