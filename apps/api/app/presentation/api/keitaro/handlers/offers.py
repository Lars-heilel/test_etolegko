from typing import Annotated

from fastapi import APIRouter, Depends

from app.presentation.api.keitaro.dependencies import get_list_offers_usecase
from app.presentation.api.keitaro.schemas import CatalogItemResponse
from app.usecase.keitaro.list_offers_usecase import ListOffersUseCase

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("")
async def list_offers(
    usecase: Annotated[ListOffersUseCase, Depends(get_list_offers_usecase)], search: str = ""
) -> list[CatalogItemResponse]:
    return [
        CatalogItemResponse(id=item.id, name=item.name) for item in await usecase.execute(search)
    ]
