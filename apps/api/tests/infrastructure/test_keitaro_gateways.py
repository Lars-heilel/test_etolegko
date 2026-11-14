import json

import pytest
import respx

from app.domain.keitaro.snapshots import (
    CampaignSummary,
    CatalogItem,
    KeitaroFlowSnapshot,
    KeitaroOfferSnapshot,
)
from app.infrastructure.keitaro.campaigns import KeitaroCampaignGateway
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.flows import KeitaroFlowGateway

BASE = "https://tracker.example.com/admin_api/v1"


@pytest.mark.parametrize("tail", [[], [{"id": 101, "name": "Last"}]])
@respx.mock
async def test_campaigns_paginate_until_short_page(tail: list[dict[str, object]]) -> None:
    respx.get(f"{BASE}/campaigns", params={"offset": 0, "limit": 100}).respond(
        200, json=[{"id": i, "name": str(i)} for i in range(100)]
    )
    respx.get(f"{BASE}/campaigns", params={"offset": 100, "limit": 100}).respond(200, json=tail)
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        result = await KeitaroCampaignGateway(client).list_campaigns()
    assert len(result) == 100 + len(tail)
    assert result[0] == CampaignSummary(0, "0", "active", "")
    if tail:
        assert result[-1] == CampaignSummary(101, "Last", "active", "")


@respx.mock
async def test_catalog_routes_and_campaign_creation() -> None:
    for path in ["domains", "traffic_sources", "offers"]:
        respx.get(f"{BASE}/{path}", params={}).respond(200, json=[{"id": 7, "name": path}])
    respx.get(f"{BASE}/groups", params={"type": "campaigns"}).respond(
        200, json=[{"id": 7, "name": "groups"}]
    )
    respx.get(f"{BASE}/offers/7").respond(200, json={"id": 7, "name": "offers"})
    create = respx.post(f"{BASE}/campaigns").respond(200, json={"id": 9})
    payload = {"name": "Campaign", "domain_id": 1, "group_id": 2, "traffic_source_id": 3}
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        gateway = KeitaroCampaignGateway(client)
        assert await gateway.list_domains() == [CatalogItem(7, "domains")]
        assert await gateway.list_groups() == [CatalogItem(7, "groups")]
        assert await gateway.list_traffic_sources() == [CatalogItem(7, "traffic_sources")]
        assert await gateway.list_offers() == [CatalogItem(7, "offers")]
        assert await gateway.get_offer(7) == CatalogItem(7, "offers")
        assert await gateway.create_campaign(payload) == {"id": 9}
    assert json.loads(create.calls[0].request.content) == payload


@respx.mock
async def test_empty_offer_streams_are_skipped_before_any_other_fields() -> None:
    respx.get(f"{BASE}/campaigns/3/streams").respond(
        200,
        json=[
            {"offers": [], "filters": "invalid", "name": {"invalid": True}},
            {"offers": None},
            {},
            {"id": 5, "name": "Main", "offers": [{"offer_id": 7, "share": "100"}]},
            {"id": 6, "offers": [{"offer_id": 8}]},
        ],
    )
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        result = await KeitaroFlowGateway(client).list_flows(3)
    assert result == [
        KeitaroFlowSnapshot(5, "Main", [KeitaroOfferSnapshot(7, 100)]),
        KeitaroFlowSnapshot(6, "Flow 6", [KeitaroOfferSnapshot(8, 0)]),
    ]


@respx.mock
async def test_creates_verified_google_and_offer_stream_payloads() -> None:
    route = respx.post(f"{BASE}/streams").respond(200, json={"id": 5})
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        gateway = KeitaroFlowGateway(client)
        await gateway.create_google_flow(3, "US")
        await gateway.create_offer_flow(3, 7)
    assert json.loads(route.calls[0].request.content) == {
        "campaign_id": 3,
        "type": "regular",
        "name": "Google",
        "position": 1,
        "weight": 50,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://www.google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["US"]}],
    }
    assert json.loads(route.calls[1].request.content) == {
        "campaign_id": 3,
        "type": "regular",
        "name": "Offer",
        "position": 2,
        "weight": 50,
        "state": "active",
        "schema": "landings",
        "action_type": "http",
        "action_payload": "",
        "offers": [{"offer_id": 7, "share": 100, "state": "active"}],
    }


@pytest.mark.parametrize("offers", [[(7, 100), (8, 0)], []])
@respx.mock
async def test_update_replaces_offers_preserving_other_stream_configuration(
    offers: list[tuple[int, int]],
) -> None:
    settings = {
        "campaign_id": 3,
        "name": "Main",
        "type": "regular",
        "schema": "landings",
        "action_type": "http",
        "action_payload": "",
        "weight": 30,
        "position": 4,
        "state": "disabled",
        "filter_or": True,
        "collect_clicks": True,
        "filters": [{"name": "country", "mode": "accept", "payload": ["US"]}],
        "triggers": [],
        "landings": [{"landing_id": 9, "share": 100}],
        "comments": "keep",
    }
    stream = {
        **settings,
        "id": 5,
        "created_at": "yesterday",
        "updated_at": "today",
        "offers": [{"offer_id": 99, "share": 100}],
    }
    respx.get(f"{BASE}/streams/5").respond(200, json=stream)
    route = respx.put(f"{BASE}/streams/5").respond(200, json=stream)
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        await KeitaroFlowGateway(client).update_offers(5, offers)
    body = json.loads(route.calls[0].request.content)
    expected_offers = (
        [
            {"offer_id": 7, "share": 100, "state": "active"},
            {"offer_id": 8, "share": 0, "state": "active"},
        ]
        if offers
        else []
    )
    assert body == {**settings, "offers": expected_offers}
