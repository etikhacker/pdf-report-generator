# Checkpoint Evidence

The local verification run used the shop dataset and FastAPI server on port 8000.

| Check | Result |
|---|---|
| `GET /health` | HTTP 200, `{"status":"ok"}` |
| First `POST /reports` | HTTP 201, id `1` |
| Second `POST /reports` | HTTP 200, same id `1` |
| Order count after two seed runs | 200 |
| Report count after duplicate POST | 1 |
| Downloaded artifact | PDF 1.4, A4, 6 pages |
| Automated tests | 5 passed |
