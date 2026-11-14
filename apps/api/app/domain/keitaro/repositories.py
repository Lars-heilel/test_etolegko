from typing import Any, Protocol

from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import CampaignSummary, CatalogItem, KeitaroFlowSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId


class CampaignOfferRepository(Protocol):
    async def list_by_campaign(self, campaign_id: CampaignId) -> list[FlowOffers]: ...

    async def save(self, campaign_id: CampaignId, flow: FlowOffers) -> None: ...

    async def sync_from_keitaro(
        self,
        campaign_id: CampaignId,
        flows: list[KeitaroFlowSnapshot],
        seen_stream_ids: list[int],
        offer_names: dict[int, str],
    ) -> None:
        """Replace the cache from a complete refresh; flows without offers are skipped."""
        ...


class CampaignGateway(Protocol):
    async def list_campaigns(self) -> list[CampaignSummary]: ...

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class CatalogGateway(Protocol):
    async def list_domains(self) -> list[CatalogItem]: ...

    async def list_groups(self) -> list[CatalogItem]: ...

    async def list_traffic_sources(self) -> list[CatalogItem]: ...

    async def list_offers(self) -> list[CatalogItem]: ...

    async def get_offer(self, offer_id: int) -> CatalogItem: ...


class FlowGateway(Protocol):
    async def list_flows(self, campaign_id: int) -> list[KeitaroFlowSnapshot]: ...

    async def create_google_flow(self, campaign_id: int, country_code: str) -> None: ...

    async def create_offer_flow(self, campaign_id: int, offer_id: int) -> None: ...

    async def update_offers(self, stream_id: int, offers: list[tuple[int, int]]) -> None: ...
