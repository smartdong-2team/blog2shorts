from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
# 추후: content, scripts, videos, assets 라우터를 여기에 추가한다.
