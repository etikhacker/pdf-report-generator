.PHONY: seed test data render

seed:
	.venv/bin/python seed.py

test:
	.venv/bin/pytest -q

data:
	.venv/bin/python scripts/report_data.py

render:
	.venv/bin/python scripts/render_report.py
