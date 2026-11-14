import json
from collections.abc import Iterator

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.config import get_settings
from app.infrastructure.persistence.models import CampaignOfferModel
from tests.presentation.test_offer_mutations import rows, seed

BASE = "https://tracker.example.com/admin_api/v1"
URL = "/api/v1/campaigns/42/offers"


@pytest.fixture(autouse=True)
def tracker_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@respx.mock
async def test_save_active_zero_and_preserve_remote_config(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory, locked=True)
    async with session_factory() as session, session.begin():
        for offer_id, state in [(2, "active"), (3, "deleted")]:
            session.add(
                CampaignOfferModel(
                    campaign_id=42,
                    stream_id=10,
                    stream_name="Main",
                    offer_id=offer_id,
                    offer_name=str(offer_id),
                    share=0,
                    state=state,
                    locked=False,
                )
            )
    before = await rows(session_factory)
    config = {
        "campaign_id": 42,
        "name": "Remote name",
        "filters": [{"name": "country"}],
        "landings": [{"landing_id": 9}],
        "weight": 23,
        "schema": "landings",
        "action_type": "http",
        "custom": {"enabled": True},
    }
    respx.get(f"{BASE}/streams/10").respond(200, json={"id": 10, **config, "offers": []})
    put = respx.put(f"{BASE}/streams/10").respond(200, json={})
    response = await client.put(URL)
    assert response.status_code == 200
    assert json.loads(put.calls[0].request.content) == {
        **config,
        "offers": [
            {"offer_id": 1, "share": 100, "state": "active"},
            {"offer_id": 2, "share": 0, "state": "active"},
        ],
    }
    assert len(response.json()["flows"][0]["offers"]) == 3
    assert await rows(session_factory) == before


@respx.mock
async def test_save_last_deleted_offer_sends_empty(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory)
    assert (await client.delete("/api/v1/campaigns/42/flows/10/offers/1")).status_code == 200
    respx.get(f"{BASE}/streams/10").respond(200, json={"campaign_id": 42})
    put = respx.put(f"{BASE}/streams/10").respond(200, json={})
    response = await client.put(URL)
    assert response.status_code == 200
    assert json.loads(put.calls[0].request.content)["offers"] == []
    assert await rows(session_factory) == [(1, 0, "deleted", False)]


@pytest.mark.parametrize("owner", [99, None, "42", True])
@respx.mock
async def test_save_rejects_unverified_remote_ownership(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession], owner: object
) -> None:
    await seed(session_factory)
    respx.get(f"{BASE}/streams/10").respond(200, json={"campaign_id": owner})
    response = await client.put(URL)
    assert response.status_code == 502
    assert response.json()["confirmed_stream_ids"] == []
    assert all(call.request.method == "GET" for call in respx.calls)
    assert await rows(session_factory) == [(1, 100, "active", False)]


@pytest.mark.parametrize("times_out", [False, True])
@respx.mock
async def test_partial_save_failure_is_truthful(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession], times_out: bool
) -> None:
    await seed(session_factory)
    async with session_factory() as session, session.begin():
        for stream_id in [20, 30]:
            session.add(
                CampaignOfferModel(
                    campaign_id=42,
                    stream_id=stream_id,
                    stream_name="Other",
                    offer_id=stream_id,
                    offer_name="Other",
                    share=100,
                    state="active",
                    locked=False,
                )
            )
    before = await rows(session_factory)
    for stream_id in [10, 20]:
        respx.get(f"{BASE}/streams/{stream_id}").respond(200, json={"campaign_id": 42})
    respx.put(f"{BASE}/streams/10").respond(200, json={})
    failed = respx.put(f"{BASE}/streams/20")
    if times_out:
        failed.mock(side_effect=httpx.ReadTimeout("private-secret"))
    else:
        failed.respond(500, json={"message": "private-secret"})
    response = await client.put(URL)
    assert response.status_code == 502
    detail = response.json()
    assert detail["confirmed_stream_ids"] == [10]
    assert detail["failed_stream_id"] == 20
    assert "Check Keitaro" in detail["message"]
    assert "private-secret" not in response.text
    assert await rows(session_factory) == before


@respx.mock
async def test_save_empty_cache_does_not_refresh(client: AsyncClient) -> None:
    response = await client.put(URL)
    assert response.status_code == 200
    assert response.json() == {"campaign_id": 42, "flows": []}
    assert not respx.calls
