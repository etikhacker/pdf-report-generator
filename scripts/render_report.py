#!/usr/bin/env python3
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import REPORT_DIR, render_pdf

output = REPORT_DIR / 'test.pdf'
REPORT_DIR.mkdir(parents=True, exist_ok=True)
asyncio.run(render_pdf(output))
print(f'Rendered {output}')
