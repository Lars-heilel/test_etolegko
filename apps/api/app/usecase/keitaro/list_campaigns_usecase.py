from app.domain.keitaro.repositories import CampaignGateway
from app.domain.keitaro.snapshots import CampaignSummary


class ListCampaignsUseCase:
    def __init__(self, gateway: CampaignGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> list[CampaignSummary]:
        return await self._gateway.list_campaigns()
