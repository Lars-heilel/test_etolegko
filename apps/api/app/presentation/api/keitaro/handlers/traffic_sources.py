from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.presentation.api.keitaro.dependencies import get_create_traffic_source_usecase
from app.presentation.api.keitaro.schemas import CatalogItemResponse, CreateTrafficSourceRequest
from app.usecase.keitaro.create_traffic_source_usecase import CreateTrafficSourceUseCase

router = APIRouter(prefix="/traffic-sources", tags=["traffic-sources"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_traffic_source(
    payload: CreateTrafficSourceRequest,
    usecase: Annotated[CreateTrafficSourceUseCase, Depends(get_create_traffic_source_usecase)],
) -> CatalogItemResponse:
    source = await usecase.execute(payload.name)
    return CatalogItemResponse(id=source.id, name=source.name)
