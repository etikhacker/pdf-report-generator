from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import app as app_module

PRODUCTS = ['Keyboard', 'Mouse', 'Monitor', 'USB Hub', 'Webcam', 'Headset']
CUSTOMERS = ['Aylin', 'Murad', 'Nigar', 'Elvin', 'Leyla', 'Samir', 'Zehra', 'Kamran']


def seed_orders(count: int = 200, seed: int = 2026) -> None:
    app_module.init_db()
    rng = random.Random(seed)
    today = date.today()
    rows = []
    for index in range(count):
        created = today - timedelta(days=rng.randint(0, 29))
        rows.append((
            f'{rng.choice(CUSTOMERS)} #{index + 1:03d}',
            rng.choice(PRODUCTS),
            round(rng.uniform(5, 200), 2),
            created.isoformat(),
        ))
    with sqlite3.connect(app_module.DB_PATH) as db:
        db.execute('DELETE FROM orders')
        db.executemany(
            'INSERT INTO orders(customer, product, amount, created_at) VALUES (?, ?, ?, ?)', rows
        )
    print(f'Seeded {count} orders into {app_module.DB_PATH}')


if __name__ == '__main__':
    seed_orders()
