from typing import Any

from app.domain.keitaro.constants import (
    COUNTRY_FILTER_NAME,
    GOOGLE_REDIRECT_URL,
    OFFER_FLOW_SCHEMA,
    OFFERS_ACTION_TYPE,
    REDIRECT_ACTION_TYPE,
)
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot, KeitaroOfferSnapshot
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.errors import KeitaroResponseError

# StreamRequestPut references StreamObject, which includes campaign_id.
READ_ONLY_STREAM_FIELDS = {"id", "updated_at", "created_at"}


def _validate_created_stream(payload: Any) -> None:
    stream_id = payload.get("id") if isinstance(payload, dict) else None
    if type(stream_id) is not int or stream_id <= 0:
        raise KeitaroResponseError(200, "Keitaro returned an invalid stream response")


class KeitaroFlowGateway:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def list_flows(self, campaign_id: int) -> list[KeitaroFlowSnapshot]:
        payload = await self._client.get(f"/campaigns/{campaign_id}/streams")
        flows = []
        for item in payload:
            offers = item.get("offers")
            if not offers:
                continue
            flows.append(
                KeitaroFlowSnapshot(
                    stream_id=item["id"],
                    name=item.get("name", f"Flow {item['id']}"),
                    offers=[
                        KeitaroOfferSnapshot(
                            offer_id=offer["offer_id"], share=int(offer.get("share", 0))
                        )
                        for offer in offers
                    ],
                )
            )
        return flows

    async def create_google_flow(self, campaign_id: int, country_code: str) -> None:
        created = await self._client.post(
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Google",
                "position": 1,
                "weight": 50,
                "state": "active",
                "schema": "redirect",
                "action_type": REDIRECT_ACTION_TYPE,
                "action_payload": GOOGLE_REDIRECT_URL,
                "filters": [
                    {"name": COUNTRY_FILTER_NAME, "mode": "accept", "payload": [country_code]}
                ],
            },
        )
        _validate_created_stream(created)

    async def create_offer_flow(self, campaign_id: int, offer_id: int) -> None:
        created = await self._client.post(
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Offer",
                "position": 2,
                "weight": 50,
                "state": "active",
                "schema": OFFER_FLOW_SCHEMA,
                "action_type": OFFERS_ACTION_TYPE,
                "action_payload": "",
                "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}],
            },
        )
        _validate_created_stream(created)

    async def update_offers(self, stream_id: int, offers: list[tuple[int, int]]) -> None:
        stream: dict[str, Any] = await self._client.get(f"/streams/{stream_id}")
        payload = {
            key: value for key, value in stream.items() if key not in READ_ONLY_STREAM_FIELDS
        }
        # The use case supplies active offers, including valid active zero-share offers.
        payload["offers"] = [
            {"offer_id": offer_id, "share": share, "state": "active"} for offer_id, share in offers
        ]
        await self._client.put(f"/streams/{stream_id}", json=payload)
