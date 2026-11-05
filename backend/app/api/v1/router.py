
from fastapi import APIRouter

from app.api.v1 import health
from app.api.v1.content import router as content_router
from app.api.v1.assets import router as assets_router
from app.api.v1.scripts import router as scripts_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(content_router)
api_router.include_router(assets_router)
api_router.include_router(scripts_router)