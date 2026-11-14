from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.presentation.api.keitaro.dependencies import (
    get_form_options_usecase,
    get_list_campaigns_usecase,
    get_refresh_usecase,
)
from app.presentation.api.keitaro.responses import to_rotation_response
from app.presentation.api.keitaro.schemas import (
    CampaignSummaryResponse,
    CatalogItemResponse,
    FormOptionsResponse,
    OfferRotationResponse,
)
from app.usecase.keitaro.get_form_options_usecase import GetFormOptionsUseCase
from app.usecase.keitaro.list_campaigns_usecase import ListCampaignsUseCase
from app.usecase.keitaro.refresh_campaign_offers_usecase import RefreshCampaignOffersUseCase

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
async def list_campaigns(
    usecase: Annotated[ListCampaignsUseCase, Depends(get_list_campaigns_usecase)],
) -> list[CampaignSummaryResponse]:
    return [
        CampaignSummaryResponse(id=item.id, name=item.name, state=item.state, alias=item.alias)
        for item in await usecase.execute()
    ]


@router.get("/form-options")
async def form_options(
    usecase: Annotated[GetFormOptionsUseCase, Depends(get_form_options_usecase)],
) -> FormOptionsResponse:
    domains, groups, sources = await usecase.execute()
    return FormOptionsResponse(
        domains=[CatalogItemResponse(id=item.id, name=item.name) for item in domains],
        groups=[CatalogItemResponse(id=item.id, name=item.name) for item in groups],
        traffic_sources=[CatalogItemResponse(id=item.id, name=item.name) for item in sources],
    )


@router.get("/{campaign_id}/offers")
async def refresh_offers(
    campaign_id: Annotated[int, Path(gt=0)],
    usecase: Annotated[RefreshCampaignOffersUseCase, Depends(get_refresh_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(CampaignId(campaign_id))
    return to_rotation_response(campaign_id, flows)
