from app.domain.keitaro.repositories import CatalogGateway
from app.domain.keitaro.snapshots import CatalogItem


class ListOffersUseCase:
    def __init__(self, gateway: CatalogGateway) -> None:
        self._gateway = gateway

    async def execute(self, search: str = "") -> list[CatalogItem]:
        offers = await self._gateway.list_offers()
        term = search.strip().lower()
        return [offer for offer in offers if term in offer.name.lower()]
