from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.domain.keitaro.exceptions import CampaignCreationError, DomainError
from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.presentation.api.keitaro.dependencies import (
    get_create_campaign_usecase,
    get_form_options_usecase,
    get_list_campaigns_usecase,
    get_refresh_usecase,
)
from app.presentation.api.keitaro.responses import to_rotation_response
from app.presentation.api.keitaro.schemas import (
    CampaignSummaryResponse,
    CatalogItemResponse,
    CreateCampaignRequest,
    FormOptionsResponse,
    OfferRotationResponse,
)
from app.usecase.keitaro.create_campaign_usecase import CreateCampaignUseCase
from app.usecase.keitaro.get_form_options_usecase import GetFormOptionsUseCase
from app.usecase.keitaro.list_campaigns_usecase import ListCampaignsUseCase
from app.usecase.keitaro.refresh_campaign_offers_usecase import RefreshCampaignOffersUseCase

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CreateCampaignRequest,
    usecase: Annotated[CreateCampaignUseCase, Depends(get_create_campaign_usecase)],
) -> CampaignSummaryResponse:
    try:
        created = await usecase.execute(
            payload.name,
            payload.country_code,
            payload.offer_id,
            payload.domain_id,
            payload.group_id,
            payload.traffic_source_id,
        )
    except CampaignCreationError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": error.code,
                "message": error.message,
                "campaign_id": error.campaign_id,
                "failed_step": error.failed_step,
                "confirmed_flows": error.confirmed_flows,
            },
        ) from None
    except DomainError as error:
        raise HTTPException(
            status_code=422, detail={"code": error.code, "message": error.message}
        ) from None
    return CampaignSummaryResponse(
        id=created.id, name=created.name, state=created.state, alias=created.alias
    )


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
