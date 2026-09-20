import asyncio
import sqlite3

from fastapi.testclient import TestClient

import app as app_module
from app import app, build_html, get_report_data
from seed import seed_orders

client = TestClient(app)


def configure_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, 'DB_PATH', tmp_path / 'report.db')
    monkeypatch.setattr(app_module, 'REPORT_DIR', tmp_path / 'reports')
    app_module.init_db()


def test_health_endpoint_returns_ok():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_seed_is_safe_to_run_twice_and_aggregation_is_real(tmp_path, monkeypatch):
    configure_temp_db(tmp_path, monkeypatch)
    seed_orders()
    seed_orders()
    with sqlite3.connect(app_module.DB_PATH) as db:
        assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 200
    data = get_report_data()
    assert data['total_orders'] == 200
    assert data['total_revenue'] > 0
    assert len(data['top_products']) == 5
    assert len(data['orders']) == 200


def test_html_contains_print_safe_table_rules(tmp_path, monkeypatch):
    configure_temp_db(tmp_path, monkeypatch)
    seed_orders()
    html = build_html(get_report_data())
    assert 'break-inside: avoid' in html
    assert '<thead>' in html
    assert 'All orders' in html


def test_report_endpoints_generate_download_and_reuse_same_day(tmp_path, monkeypatch):
    configure_temp_db(tmp_path, monkeypatch)
    seed_orders()

    first = client.post('/reports')
    assert first.status_code == 201
    report_id = first.json()['id']
    assert first.json()['file'] == f'/reports/{report_id}/file'
    assert (tmp_path / 'reports' / f'{report_id}.pdf').is_file()

    second = client.post('/reports')
    assert second.status_code == 200
    assert second.json()['id'] == report_id

    listing = client.get('/reports')
    assert listing.status_code == 200
    assert listing.json()[0]['file'] == f'/reports/{report_id}/file'

    status = client.get(f'/reports/{report_id}')
    assert status.status_code == 200
    assert status.json()['id'] == report_id

    downloaded = client.get(f'/reports/{report_id}/file')
    assert downloaded.status_code == 200
    assert downloaded.headers['content-type'] == 'application/pdf'
    assert downloaded.content.startswith(b'%PDF')

    forced = client.post('/reports', json={'force': True})
    assert forced.status_code == 201
    assert forced.json()['id'] != report_id


def test_unknown_report_returns_404():
    response = client.get('/reports/999999/file')
    assert response.status_code == 404
