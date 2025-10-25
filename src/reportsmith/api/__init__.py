"""ReportSmith API package."""

from .server import app  # re-export FastAPI app

__all__ = ["app"]
