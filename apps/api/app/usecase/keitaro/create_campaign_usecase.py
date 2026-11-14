import re
import uuid

from app.domain.keitaro.exceptions import (
    CampaignCreationError,
    DomainError,
    GatewayError,
    InvalidCountryCodeError,
)
from app.domain.keitaro.repositories import CampaignGateway, FlowGateway
from app.domain.keitaro.snapshots import CampaignSummary
from app.domain.keitaro.value_objects.country import CountryCode


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "campaign"
    return f"{base}-{uuid.uuid4().hex[:8]}"


class CreateCampaignUseCase:
    def __init__(self, campaigns: CampaignGateway, flows: FlowGateway) -> None:
        self._campaigns = campaigns
        self._flows = flows

    async def execute(
        self,
        name: str,
        country_code: str,
        offer_id: int,
        domain_id: int,
        group_id: int,
        traffic_source_id: int,
    ) -> CampaignSummary:
        name = name.strip()
        if not name:
            raise DomainError("Campaign name is required")
        try:
            country = CountryCode(country_code)
        except ValueError as error:
            raise InvalidCountryCodeError(str(error)) from error
        if any(
            type(value) is not int or value <= 0
            for value in (offer_id, domain_id, group_id, traffic_source_id)
        ):
            raise DomainError("Offer, domain, group and traffic source are required")

        alias = _slug(name)
        campaign_id = None
        step = "campaign"
        confirmed_flows = 0
        try:
            created = await self._campaigns.create_campaign(
                {
                    "name": name,
                    "alias": alias,
                    "type": "position",
                    "state": "active",
                    "domain_id": domain_id,
                    "group_id": str(group_id),
                    "traffic_source_id": traffic_source_id,
                }
            )
            # Do not guess an ID or proceed with writes after a malformed response.
            raw_id = created.get("id") if isinstance(created, dict) else None
            if type(raw_id) is not int or raw_id <= 0:
                raise GatewayError("Invalid campaign response")
            campaign_id = raw_id
            step = "google_flow"
            await self._flows.create_google_flow(campaign_id, country.value)
            confirmed_flows = 1
            step = "offer_flow"
            await self._flows.create_offer_flow(campaign_id, offer_id)
        except GatewayError:
            # No retry or rollback: a failed POST can already have taken effect.
            raise CampaignCreationError(campaign_id, step, confirmed_flows) from None

        return CampaignSummary(
            id=campaign_id,
            name=str(created.get("name", name)),
            state=str(created.get("state", "active")),
            alias=str(created.get("alias", alias)),
        )
