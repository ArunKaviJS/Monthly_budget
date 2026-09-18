"""
api/index.py — Vercel serverless entrypoint.

Vercel's Python runtime looks for an ASGI-compatible `app` object in this
file. It re-exports the real FastAPI app defined in app/main.py.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: E402
