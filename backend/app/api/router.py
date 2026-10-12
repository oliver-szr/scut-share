from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.items import router as items_router
from app.api.routes.trades import router as trades_router
from app.api.routes.borrows import router as borrows_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.reports import router as reports_router
from app.api.routes.gifts import router as gifts_router
from app.api.routes.prices import router as prices_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(items_router)
api_router.include_router(trades_router)
api_router.include_router(borrows_router)
api_router.include_router(conversations_router)
api_router.include_router(reports_router)
api_router.include_router(gifts_router)
api_router.include_router(prices_router)
