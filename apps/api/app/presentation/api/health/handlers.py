from fastapi import APIRouter
from pydantic import BaseModel

from app.infrastructure.config import get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


@router.get("/health")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )
