from .auth import router as auth_router
from .visitors import router as visitors_router
from .gate import router as gate_router
from .watchlist import router as watchlist_router
from .incidents import router as incidents_router
from .dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "visitors_router",
    "gate_router",
    "watchlist_router",
    "incidents_router",
    "dashboard_router"
]
