from fastapi import APIRouter

from app.presentation.api.health.handlers import router as health_router
from app.presentation.api.keitaro.handlers.campaigns import router as campaigns_router
from app.presentation.api.keitaro.handlers.offers import router as offers_router
from app.presentation.api.keitaro.handlers.traffic_sources import router as traffic_sources_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(campaigns_router)
api_router.include_router(offers_router)
api_router.include_router(traffic_sources_router)
