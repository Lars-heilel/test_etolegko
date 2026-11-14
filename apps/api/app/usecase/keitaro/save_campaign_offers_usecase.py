from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import CampaignOffersSaveError, GatewayError
from app.domain.keitaro.repositories import CampaignOfferRepository, FlowGateway
from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.domain.keitaro.value_objects.offer_share import OfferState


class SaveCampaignOffersUseCase:
    def __init__(self, repository: CampaignOfferRepository, flows: FlowGateway) -> None:
        self._repository = repository
        self._flows = flows

    async def execute(self, campaign_id: int) -> list[FlowOffers]:
        flows = await self._repository.list_by_campaign(CampaignId(campaign_id))
        confirmed: list[int] = []
        for flow in flows:
            active = [
                (item.offer_id.value, item.share.value)
                for item in flow.offers
                if item.state is OfferState.ACTIVE
            ]
            try:
                await self._flows.update_offers(
                    flow.stream_id.value, active, campaign_id=campaign_id
                )
            except GatewayError as error:
                raise CampaignOffersSaveError(flow.stream_id.value, confirmed) from error
            confirmed.append(flow.stream_id.value)
        return flows
