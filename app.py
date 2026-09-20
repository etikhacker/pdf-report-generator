from __future__ import annotations

import html
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('REPORT_DB', BASE_DIR / 'report.db'))
REPORT_DIR = Path(os.getenv('REPORT_DIR', BASE_DIR / 'reports'))

app = FastAPI(title='PDF Report Generator', version='1.0.0')


class ReportRequest(BaseModel):
    force: bool = False


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                product TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        ''')


def get_report_data() -> dict[str, Any]:
    with connect() as db:
        totals = db.execute('''
            SELECT COUNT(*) AS total_orders, COALESCE(SUM(amount), 0) AS total_revenue
            FROM orders
        ''').fetchone()
        top_products = db.execute('''
            SELECT product, COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS revenue
            FROM orders
            GROUP BY product
            ORDER BY revenue DESC
            LIMIT 5
        ''').fetchall()
        daily_orders = db.execute('''
            SELECT created_at, COUNT(*) AS order_count
            FROM orders
            WHERE date(created_at) >= date('now', '-6 day')
            GROUP BY created_at
            ORDER BY created_at
        ''').fetchall()
        orders = db.execute('''
            SELECT id, customer, product, amount, created_at
            FROM orders
            ORDER BY created_at DESC, id DESC
        ''').fetchall()
    return {
        'total_orders': totals['total_orders'],
        'total_revenue': round(totals['total_revenue'], 2),
        'top_products': [dict(row) for row in top_products],
        'daily_orders': [dict(row) for row in daily_orders],
        'orders': [dict(row) for row in orders],
    }


def _money(value: float) -> str:
    return f'${value:,.2f}'


def build_html(data: dict[str, Any]) -> str:
    product_rows = ''.join(
        f"<tr><td>{html.escape(row['product'])}</td><td>{row['order_count']}</td><td>{_money(row['revenue'])}</td></tr>"
        for row in data['top_products']
    )
    daily_rows = ''.join(
        f"<tr><td>{html.escape(row['created_at'])}</td><td>{row['order_count']}</td></tr>"
        for row in data['daily_orders']
    )
    order_rows = ''.join(
        f"<tr><td>{row['id']}</td><td>{html.escape(row['customer'])}</td><td>{html.escape(row['product'])}</td>"
        f"<td>{_money(row['amount'])}</td><td>{html.escape(row['created_at'])}</td></tr>"
        for row in data['orders']
    )
    today = date.today().isoformat()
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Sales Report — {today}</title>
<style>
@page {{ size: A4; margin: 16mm 12mm 18mm; }}
* {{ box-sizing: border-box; }} body {{ font-family: Arial, sans-serif; color: #172033; font-size: 10px; }}
h1 {{ color: #123b67; margin: 0 0 4px; font-size: 25px; }} h2 {{ color: #123b67; margin: 22px 0 8px; font-size: 15px; }}
.subtitle {{ color: #64748b; margin-bottom: 18px; }} .cards {{ display: flex; gap: 12px; }}
.card {{ flex: 1; border: 1px solid #dbe4ee; border-radius: 8px; padding: 12px; background: #f8fbff; }}
.label {{ color: #64748b; text-transform: uppercase; letter-spacing: .06em; font-size: 8px; }} .value {{ font-weight: bold; font-size: 18px; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 5px; }} th {{ background: #123b67; color: white; text-align: left; }} th, td {{ padding: 6px 7px; border-bottom: 1px solid #dbe4ee; }}
thead {{ display: table-header-group; }} tr {{ break-inside: avoid; page-break-inside: avoid; }} .section {{ break-inside: avoid; }}
footer {{ position: fixed; bottom: -10mm; left: 0; right: 0; text-align: center; color: #94a3b8; font-size: 8px; }}
</style></head><body>
<h1>Sales Report</h1><div class="subtitle">Generated on {today} · Order performance overview</div>
<div class="cards"><div class="card"><div class="label">Total orders</div><div class="value">{data['total_orders']}</div></div>
<div class="card"><div class="label">Total revenue</div><div class="value">{_money(data['total_revenue'])}</div></div></div>
<div class="section"><h2>Top products by revenue</h2><table><thead><tr><th>Product</th><th>Orders</th><th>Revenue</th></tr></thead><tbody>{product_rows}</tbody></table></div>
<div class="section"><h2>Orders per day — last 7 days</h2><table><thead><tr><th>Date</th><th>Orders</th></tr></thead><tbody>{daily_rows}</tbody></table></div>
<h2>All orders</h2><table><thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead><tbody>{order_rows}</tbody></table>
<footer>PDF Report Generator · FlyRank Backend Track</footer></body></html>'''


async def render_pdf(path: Path) -> None:
    data = get_report_data()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.set_content(build_html(data), wait_until='networkidle')
        await page.pdf(path=str(path), format='A4', print_background=True)
        await browser.close()


async def create_report(force: bool = False) -> tuple[int, bool]:
    init_db()
    today = date.today().isoformat()
    with connect() as db:
        if not force:
            existing = db.execute(
                'SELECT id FROM reports WHERE date(created_at) = ? ORDER BY id DESC LIMIT 1', (today,)
            ).fetchone()
            if existing:
                return existing['id'], False
        created_at = datetime.now().isoformat(timespec='seconds')
        cursor = db.execute('INSERT INTO reports(path, created_at) VALUES (?, ?)', ('', created_at))
        report_id = cursor.lastrowid
        relative_path = f'reports/{report_id}.pdf'
        db.execute('UPDATE reports SET path = ? WHERE id = ?', (relative_path, report_id))
    await render_pdf(REPORT_DIR / f'{report_id}.pdf')
    return report_id, True


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/reports')
async def generate_report(request: ReportRequest = ReportRequest()) -> dict[str, Any]:
    report_id, created = await create_report(request.force)
    payload = {'id': report_id, 'file': f'/reports/{report_id}/file'}
    return JSONResponse(status_code=201 if created else 200, content=payload)


@app.get('/reports')
def list_reports() -> list[dict[str, Any]]:
    init_db()
    with connect() as db:
        rows = db.execute('SELECT id, path, created_at FROM reports ORDER BY id DESC').fetchall()
    return [
        {**dict(row), 'file': f"/reports/{row['id']}/file"}
        for row in rows
    ]


@app.get('/reports/{report_id}')
def report_status(report_id: int) -> dict[str, Any]:
    init_db()
    with connect() as db:
        row = db.execute('SELECT id, path, created_at FROM reports WHERE id = ?', (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Report not found')
    return {'id': row['id'], 'path': row['path'], 'created_at': row['created_at'], 'file': f'/reports/{report_id}/file'}


@app.get('/reports/{report_id}/file', response_class=FileResponse)
def report_file(report_id: int) -> FileResponse:
    init_db()
    with connect() as db:
        row = db.execute('SELECT path FROM reports WHERE id = ?', (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Report not found')
    path = (REPORT_DIR / Path(row['path']).name).resolve()
    if not path.is_file() or REPORT_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail='Report file not found')
    return FileResponse(path, media_type='application/pdf', filename=f'sales-report-{report_id}.pdf')
