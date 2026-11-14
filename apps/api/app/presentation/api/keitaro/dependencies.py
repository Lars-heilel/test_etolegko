from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.keitaro.repositories import CampaignOfferRepository
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database import get_session
from app.infrastructure.keitaro.campaigns import KeitaroCampaignGateway
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.errors import KeitaroError
from app.infrastructure.keitaro.flows import KeitaroFlowGateway
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)
from app.usecase.keitaro.get_form_options_usecase import GetFormOptionsUseCase
from app.usecase.keitaro.list_campaigns_usecase import ListCampaignsUseCase
from app.usecase.keitaro.list_offers_usecase import ListOffersUseCase
from app.usecase.keitaro.refresh_campaign_offers_usecase import RefreshCampaignOffersUseCase

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_keitaro_client(settings: SettingsDep) -> AsyncIterator[KeitaroClient]:
    try:
        async with KeitaroClient(settings.keitaro_base_url, settings.keitaro_api_key) as client:
            yield client
    except KeitaroError:
        # Upstream response bodies may echo credentials or other private data.
        raise HTTPException(
            status_code=502,
            detail={"code": "KEITARO_UNAVAILABLE", "message": "Could not load data from Keitaro"},
        ) from None


ClientDep = Annotated[KeitaroClient, Depends(get_keitaro_client)]


def get_campaign_gateway(client: ClientDep) -> KeitaroCampaignGateway:
    return KeitaroCampaignGateway(client)


def get_flow_gateway(client: ClientDep) -> KeitaroFlowGateway:
    return KeitaroFlowGateway(client)


async def get_offer_repository(session: SessionDep) -> AsyncIterator[CampaignOfferRepository]:
    # Repositories only flush; the request boundary owns commit and rollback.
    async with session.begin():
        yield SqlAlchemyCampaignOfferRepository(session)


CampaignGatewayDep = Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)]
FlowGatewayDep = Annotated[KeitaroFlowGateway, Depends(get_flow_gateway)]
OfferRepositoryDep = Annotated[
    CampaignOfferRepository, Depends(get_offer_repository, scope="function")
]


def get_list_campaigns_usecase(gateway: CampaignGatewayDep) -> ListCampaignsUseCase:
    return ListCampaignsUseCase(gateway)


def get_list_offers_usecase(gateway: CampaignGatewayDep) -> ListOffersUseCase:
    return ListOffersUseCase(gateway)


def get_form_options_usecase(gateway: CampaignGatewayDep) -> GetFormOptionsUseCase:
    return GetFormOptionsUseCase(gateway)


def get_refresh_usecase(
    repository: OfferRepositoryDep, flows: FlowGatewayDep, catalog: CampaignGatewayDep
) -> RefreshCampaignOffersUseCase:
    return RefreshCampaignOffersUseCase(repository, flows, catalog)
