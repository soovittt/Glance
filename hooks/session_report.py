#!/usr/bin/env python3
"""Print the glance-cua session efficiency report from telemetry.

Same output as the `session_report` MCP tool, but from the command line:
  python hooks/session_report.py                 (default ~/.glance/session_telemetry.jsonl)
  python hooks/session_report.py FILE.jsonl
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from glance.telemetry import load, summarize  # noqa: E402

print(summarize(load(sys.argv[1] if len(sys.argv) > 1 else None)))
