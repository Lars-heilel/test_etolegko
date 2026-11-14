from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId
from app.usecase.keitaro.add_offer_usecase import find_flow


class DeleteOfferUseCase:
    def __init__(self, repository: CampaignOfferRepository) -> None:
        self._repository = repository

    async def execute(self, campaign_id: int, stream_id: int, offer_id: int) -> list[FlowOffers]:
        campaign = CampaignId(campaign_id)
        flow = find_flow(await self._repository.list_by_campaign(campaign), stream_id)
        flow.delete_offer(OfferId(offer_id))
        await self._repository.save(campaign, flow)
        return await self._repository.list_by_campaign(campaign)
