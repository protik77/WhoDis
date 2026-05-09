"""Routers for WhoDis."""

from whodis.routers.api import router as api_router
from whodis.routers.auth import router as auth_router
from whodis.routers.web import router as web_router

__all__ = ["api_router", "auth_router", "web_router"]
