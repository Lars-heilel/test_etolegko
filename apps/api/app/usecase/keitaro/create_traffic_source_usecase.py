from app.domain.keitaro.exceptions import DomainError, GatewayError, TrafficSourceCreationError
from app.domain.keitaro.repositories import TrafficSourceGateway
from app.domain.keitaro.snapshots import CatalogItem


class CreateTrafficSourceUseCase:
    def __init__(self, gateway: TrafficSourceGateway) -> None:
        self._gateway = gateway

    async def execute(self, name: str) -> CatalogItem:
        name = name.strip()
        if not name:
            raise DomainError("Traffic source name is required")
        try:
            return await self._gateway.create_traffic_source(name)
        except GatewayError as error:
            raise TrafficSourceCreationError(error) from None
