"""Convenient ASGI entry point: uvicorn app:app --reload."""

from backend.main import app

__all__ = ["app"]
