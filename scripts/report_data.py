#!/usr/bin/env python3
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import get_report_data

print(json.dumps(get_report_data(), indent=2))
