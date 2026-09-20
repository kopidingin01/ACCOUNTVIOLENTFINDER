"""Entrypoint for Vercel's Python runtime (see vercel.json at the backend
root). Vercel needs an importable ASGI `app` object at this path; the
real application lives in main.py one directory up, unchanged, so the
exact same code path is used whether you run `uvicorn main:app` locally
or deploy this to Vercel — this file is a thin re-export, not a fork.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402
