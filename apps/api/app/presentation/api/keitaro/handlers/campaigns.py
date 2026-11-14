from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.presentation.api.keitaro.dependencies import (
    get_add_offer_usecase,
    get_create_campaign_usecase,
    get_delete_offer_usecase,
    get_form_options_usecase,
    get_list_campaigns_usecase,
    get_refresh_usecase,
    get_restore_offer_usecase,
    get_save_offers_usecase,
    get_set_lock_usecase,
)
from app.presentation.api.keitaro.responses import to_rotation_response
from app.presentation.api.keitaro.schemas import (
    AddOfferRequest,
    CampaignSummaryResponse,
    CatalogItemResponse,
    CreateCampaignRequest,
    FormOptionsResponse,
    LockOfferRequest,
    OfferRotationResponse,
)
from app.usecase.keitaro.add_offer_usecase import AddOfferUseCase
from app.usecase.keitaro.create_campaign_usecase import CreateCampaignUseCase
from app.usecase.keitaro.delete_offer_usecase import DeleteOfferUseCase
from app.usecase.keitaro.get_form_options_usecase import GetFormOptionsUseCase
from app.usecase.keitaro.list_campaigns_usecase import ListCampaignsUseCase
from app.usecase.keitaro.refresh_campaign_offers_usecase import RefreshCampaignOffersUseCase
from app.usecase.keitaro.restore_offer_usecase import RestoreOfferUseCase
from app.usecase.keitaro.save_campaign_offers_usecase import SaveCampaignOffersUseCase
from app.usecase.keitaro.set_offer_lock_usecase import SetOfferLockUseCase

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.put("/{campaign_id}/offers", response_model=OfferRotationResponse)
async def save_offers(
    campaign_id: Annotated[int, Path(gt=0)],
    usecase: Annotated[SaveCampaignOffersUseCase, Depends(get_save_offers_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(campaign_id)
    return to_rotation_response(campaign_id, flows)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CreateCampaignRequest,
    usecase: Annotated[CreateCampaignUseCase, Depends(get_create_campaign_usecase)],
) -> CampaignSummaryResponse:
    created = await usecase.execute(
        payload.name,
        payload.country_code,
        payload.offer_id,
        domain_id=payload.domain_id,
        group_id=payload.group_id,
        traffic_source_id=payload.traffic_source_id,
    )
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


@router.post("/{campaign_id}/flows/{stream_id}/offers")
async def add_offer(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    payload: AddOfferRequest,
    usecase: Annotated[AddOfferUseCase, Depends(get_add_offer_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(campaign_id, stream_id, payload.offer_id)
    return to_rotation_response(campaign_id, flows)


@router.delete("/{campaign_id}/flows/{stream_id}/offers/{offer_id}")
async def delete_offer(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    offer_id: Annotated[int, Path(gt=0)],
    usecase: Annotated[DeleteOfferUseCase, Depends(get_delete_offer_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(campaign_id, stream_id, offer_id)
    return to_rotation_response(campaign_id, flows)


@router.post("/{campaign_id}/flows/{stream_id}/offers/{offer_id}/restore")
async def restore_offer(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    offer_id: Annotated[int, Path(gt=0)],
    usecase: Annotated[RestoreOfferUseCase, Depends(get_restore_offer_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(campaign_id, stream_id, offer_id)
    return to_rotation_response(campaign_id, flows)


@router.patch("/{campaign_id}/flows/{stream_id}/offers/{offer_id}/lock")
async def set_offer_lock(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    offer_id: Annotated[int, Path(gt=0)],
    payload: LockOfferRequest,
    usecase: Annotated[SetOfferLockUseCase, Depends(get_set_lock_usecase)],
) -> OfferRotationResponse:
    flows = await usecase.execute(campaign_id, stream_id, offer_id, payload.locked)
    return to_rotation_response(campaign_id, flows)
