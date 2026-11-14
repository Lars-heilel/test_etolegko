import json
import re
from collections.abc import Iterator

import httpx
import pytest
import respx
from httpx import AsyncClient

from app.infrastructure.config import get_settings

BASE = "https://tracker.example.com/admin_api/v1"
PAYLOAD = {
    "name": " MX Campaign ",
    "country_code": " mx ",
    "offer_id": 7,
    "domain_id": 1,
    "group_id": 2,
    "traffic_source_id": 3,
}


@pytest.fixture(autouse=True)
def tracker_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@respx.mock
async def test_create_campaign_builds_two_flows(client: AsyncClient) -> None:
    campaign = respx.post(f"{BASE}/campaigns").respond(200, json={"id": 42})
    flows = respx.post(f"{BASE}/streams").mock(
        side_effect=[
            httpx.Response(200, json={"id": 100}),
            httpx.Response(200, json={"id": 101}),
        ]
    )
    response = await client.post("/api/v1/campaigns", json=PAYLOAD)
    assert response.status_code == 201
    body = json.loads(campaign.calls[0].request.content)
    assert re.fullmatch(r"mx-campaign-[a-f0-9]{8}", body.pop("alias"))
    assert body == {
        "name": "MX Campaign",
        "type": "position",
        "state": "active",
        "domain_id": 1,
        "group_id": "2",
        "traffic_source_id": 3,
    }
    assert response.json()["id"] == 42
    assert response.json()["name"] == "MX Campaign"
    assert response.json()["state"] == "active"
    assert response.json()["alias"]
    assert campaign.call_count == 1
    assert flows.call_count == 2
    google, offer = [json.loads(call.request.content) for call in flows.calls]
    assert google == {
        "campaign_id": 42,
        "type": "regular",
        "name": "Google",
        "position": 1,
        "weight": 50,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://www.google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["MX"]}],
    }
    assert offer == {
        "campaign_id": 42,
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


@pytest.mark.parametrize("field", list(PAYLOAD))
@respx.mock
async def test_all_creator_fields_required(client: AsyncClient, field: str) -> None:
    payload = {key: value for key, value in PAYLOAD.items() if key != field}
    response = await client.post("/api/v1/campaigns", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert not respx.calls


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", " \t"),
        ("country_code", ""),
        ("country_code", "ZZ"),
        ("country_code", "éé"),
        ("country_code", "ß"),
        ("country_code", "USA"),
        ("country_code", "US,MX"),
        ("country_code", "U1"),
        *[
            (field, value)
            for field in ("offer_id", "domain_id", "group_id", "traffic_source_id")
            for value in (0, -1, True, 1.5)
        ],
    ],
)
@respx.mock
async def test_invalid_creator_input_never_writes(
    client: AsyncClient,
    field: str,
    value: object,
) -> None:
    response = await client.post("/api/v1/campaigns", json={**PAYLOAD, field: value})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert not respx.calls


@pytest.mark.parametrize("stage", ["campaign", "google_flow", "offer_flow"])
@pytest.mark.parametrize("failure", ["timeout", "500", "400", "invalid_json", "missing_id"])
@respx.mock
async def test_creation_failure_is_truthful_and_never_retried(
    client: AsyncClient,
    stage: str,
    failure: str,
) -> None:
    error = {
        "timeout": httpx.ReadTimeout("test-only-key"),
        "500": httpx.Response(500, text="test-only-key"),
        "400": httpx.Response(400, json={"message": "test-only-key"}),
        "invalid_json": httpx.Response(200, text="test-only-key"),
        "missing_id": httpx.Response(200, json={}),
    }[failure]
    campaign = respx.post(f"{BASE}/campaigns").mock(
        side_effect=[error] if stage == "campaign" else [httpx.Response(200, json={"id": 42})]
    )
    if stage != "campaign":
        respx.post(f"{BASE}/streams").mock(
            side_effect=(
                [error]
                if stage == "google_flow"
                else [httpx.Response(200, json={"id": 100}), error]
            )
        )
    response = await client.post("/api/v1/campaigns", json=PAYLOAD)
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["code"] == "KEITARO_UNAVAILABLE"
    assert detail["campaign_id"] == (None if stage == "campaign" else 42)
    assert detail["failed_step"] == stage
    assert detail["confirmed_flows"] == (1 if stage == "offer_flow" else 0)
    assert "test-only-key" not in response.text
    assert campaign.call_count == 1
    assert len(respx.calls) == {"campaign": 1, "google_flow": 2, "offer_flow": 3}[stage]


@pytest.mark.parametrize("created", [{}, {"id": None}, {"id": True}, {"id": 0}, {"id": 1.5}, []])
@respx.mock
async def test_malformed_creation_response_reports_unknown_outcome(
    client: AsyncClient,
    created: object,
) -> None:
    respx.post(f"{BASE}/campaigns").respond(200, json=created)
    response = await client.post("/api/v1/campaigns", json=PAYLOAD)
    assert response.status_code == 502
    assert response.json()["detail"]["campaign_id"] is None
    assert len(respx.calls) == 1
