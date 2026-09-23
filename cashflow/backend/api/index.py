"""Vercel serverless entry point for FastAPI."""
from app.main import app  # noqa: F401 — Vercel looks for `app`
