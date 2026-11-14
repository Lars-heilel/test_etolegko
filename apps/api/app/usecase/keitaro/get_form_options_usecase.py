from app.domain.keitaro.repositories import CatalogGateway
from app.domain.keitaro.snapshots import CatalogItem


class GetFormOptionsUseCase:
    def __init__(self, gateway: CatalogGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> tuple[list[CatalogItem], list[CatalogItem], list[CatalogItem]]:
        return (
            await self._gateway.list_domains(),
            await self._gateway.list_groups(),
            await self._gateway.list_traffic_sources(),
        )
