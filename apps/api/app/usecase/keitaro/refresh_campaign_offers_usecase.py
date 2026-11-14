from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository, CatalogGateway, FlowGateway
from app.domain.keitaro.value_objects.identifiers import CampaignId


class RefreshCampaignOffersUseCase:
    def __init__(
        self, repository: CampaignOfferRepository, flows: FlowGateway, catalog: CatalogGateway
    ) -> None:
        self._repository = repository
        self._flows = flows
        self._catalog = catalog

    async def execute(self, campaign_id: CampaignId) -> list[FlowOffers]:
        snapshots = await self._flows.list_flows(campaign_id.value)
        # Empty flow contents must never be inspected, even for their identifiers.
        non_empty = [flow for flow in snapshots if flow.offers]
        offers = await self._catalog.list_offers()
        await self._repository.sync_from_keitaro(
            campaign_id,
            non_empty,
            [flow.stream_id for flow in non_empty],
            {offer.id: offer.name for offer in offers},
        )
        return await self._repository.list_by_campaign(campaign_id)
