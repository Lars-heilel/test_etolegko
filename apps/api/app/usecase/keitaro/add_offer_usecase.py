from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import FlowNotFoundError, OfferAlreadyExistsError
from app.domain.keitaro.repositories import CampaignOfferRepository, CatalogGateway
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId


def find_flow(flows: list[FlowOffers], stream_id: int) -> FlowOffers:
    for flow in flows:
        if flow.stream_id.value == stream_id:
            return flow
    raise FlowNotFoundError(f"Flow {stream_id} is not loaded for this campaign")


class AddOfferUseCase:
    def __init__(self, repository: CampaignOfferRepository, catalog: CatalogGateway) -> None:
        self._repository = repository
        self._catalog = catalog

    async def execute(self, campaign_id: int, stream_id: int, offer_id: int) -> list[FlowOffers]:
        campaign = CampaignId(campaign_id)
        identifier = OfferId(offer_id)
        flow = find_flow(await self._repository.list_by_campaign(campaign), stream_id)
        # Reject active and deleted duplicates before contacting the catalog.
        if any(item.offer_id == identifier for item in flow.offers):
            raise OfferAlreadyExistsError(f"Offer {offer_id} already exists in the flow")
        offer = await self._catalog.get_offer(offer_id)
        flow.add_offer(identifier, offer.name)
        await self._repository.save(campaign, flow)
        return await self._repository.list_by_campaign(campaign)
