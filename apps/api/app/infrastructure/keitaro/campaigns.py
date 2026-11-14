from typing import Any, cast

from app.domain.keitaro.snapshots import CampaignSummary, CatalogItem
from app.infrastructure.keitaro.client import KeitaroClient

PAGE_SIZE = 100


class KeitaroCampaignGateway:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def list_campaigns(self) -> list[CampaignSummary]:
        campaigns: list[CampaignSummary] = []
        offset = 0
        while True:
            page = await self._client.get(
                "/campaigns", params={"offset": offset, "limit": PAGE_SIZE}
            )
            campaigns.extend(
                CampaignSummary(
                    id=item["id"],
                    name=item["name"],
                    state=item.get("state", "active"),
                    alias=item.get("alias", ""),
                )
                for item in page
            )
            if len(page) < PAGE_SIZE:
                return campaigns
            offset += PAGE_SIZE

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], await self._client.post("/campaigns", json=payload))

    async def list_domains(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/domains")
        ]

    async def list_groups(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/groups", params={"type": "campaigns"})
        ]

    async def list_traffic_sources(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/traffic_sources")
        ]

    async def list_offers(self) -> list[CatalogItem]:
        # Keitaro has no documented server-side name search; consumers filter locally.
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/offers")
        ]

    async def get_offer(self, offer_id: int) -> CatalogItem:
        item = await self._client.get(f"/offers/{offer_id}")
        return CatalogItem(id=item["id"], name=item["name"])
