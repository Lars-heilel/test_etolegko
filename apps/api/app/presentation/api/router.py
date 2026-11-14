from fastapi import APIRouter

from app.presentation.api.health.handlers import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
