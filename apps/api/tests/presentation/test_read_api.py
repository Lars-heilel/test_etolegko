from collections.abc import Iterator

import pytest
import respx
from httpx import AsyncClient, ReadTimeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.keitaro.exceptions import DomainError
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.infrastructure.config import get_settings
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)
from app.infrastructure.persistence.models import CampaignOfferModel

BASE = "https://tracker.example.com/admin_api/v1"


@pytest.fixture(autouse=True)
def tracker_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@respx.mock
async def test_read_endpoints(client: AsyncClient) -> None:
    respx.get(f"{BASE}/campaigns", params={"offset": 0, "limit": 100}).respond(
        200, json=[{"id": 4, "name": "Campa", "state": "active", "alias": "campa"}]
    )
    respx.get(f"{BASE}/offers").respond(200, json=[{"id": 7, "name": "Offer Seven"}])
    respx.get(f"{BASE}/domains").respond(200, json=[{"id": 1, "name": "example.com"}])
    respx.get(f"{BASE}/groups", params={"type": "campaigns"}).respond(
        200, json=[{"id": 2, "name": "Group"}]
    )
    respx.get(f"{BASE}/traffic_sources").respond(200, json=[{"id": 3, "name": "Source"}])
    respx.get(f"{BASE}/campaigns/4/streams").respond(
        200,
        json=[
            {"offers": [], "id": "invalid", "name": {}},
            {"id": 11, "name": "Main", "offers": [{"offer_id": 7, "share": 100}]},
        ],
    )
    campaigns = await client.get("/api/v1/campaigns")
    assert campaigns.status_code == 200
    assert campaigns.json() == [{"id": 4, "name": "Campa", "state": "active", "alias": "campa"}]
    offers = await client.get("/api/v1/offers")
    assert offers.status_code == 200
    assert offers.json() == [{"id": 7, "name": "Offer Seven"}]
    options = await client.get("/api/v1/campaigns/form-options")
    assert options.status_code == 200
    assert options.json() == {
        "domains": [{"id": 1, "name": "example.com"}],
        "groups": [{"id": 2, "name": "Group"}],
        "traffic_sources": [{"id": 3, "name": "Source"}],
    }
    rotation = await client.get("/api/v1/campaigns/4/offers")
    assert rotation.status_code == 200
    assert rotation.json() == {
        "campaign_id": 4,
        "flows": [
            {
                "stream_id": 11,
                "name": "Main",
                "offers": [
                    {
                        "offer_id": 7,
                        "name": "Offer Seven",
                        "share": 100,
                        "state": "active",
                        "locked": False,
                    },
                ],
            }
        ],
    }
    assert all(call.request.method == "GET" for call in respx.calls)


@pytest.mark.parametrize(
    ("search", "expected_ids"), [("  sEVen  ", [7]), (" ", [7, 8]), ("absent", [])]
)
@respx.mock
async def test_offer_search(client: AsyncClient, search: str, expected_ids: list[int]) -> None:
    respx.get(f"{BASE}/offers").respond(
        200, json=[{"id": 7, "name": "Offer Seven"}, {"id": 8, "name": "Eight"}]
    )
    response = await client.get("/api/v1/offers", params={"search": search})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == expected_ids


@respx.mock
async def test_refresh_commits_locks_deletions_and_removes_empty_flows(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session, session.begin():
        for campaign, stream, offer, share in [
            (4, 11, 7, 70),
            (4, 11, 8, 30),
            (4, 12, 7, 100),
            (5, 11, 7, 100),
        ]:
            session.add(
                CampaignOfferModel(
                    campaign_id=campaign,
                    stream_id=stream,
                    stream_name="Old",
                    offer_id=offer,
                    offer_name=f"Old {offer}",
                    share=share,
                    state="active",
                    locked=True,
                )
            )
    respx.get(f"{BASE}/offers").respond(200, json=[{"id": 7, "name": "Updated"}])
    streams = respx.get(f"{BASE}/campaigns/4/streams").respond(
        200,
        json=[
            {
                "id": 11,
                "name": "Main",
                "offers": [{"offer_id": 7, "share": 20}, {"offer_id": 9, "share": 80}],
            },
            {"id": 12, "offers": []},
        ],
    )
    response = await client.get("/api/v1/campaigns/4/offers")
    assert response.status_code == 200
    assert response.json()["flows"] == [
        {
            "stream_id": 11,
            "name": "Main",
            "offers": [
                {"offer_id": 7, "name": "Updated", "share": 70, "state": "active", "locked": True},
                {"offer_id": 8, "name": "Old 8", "share": 0, "state": "deleted", "locked": False},
                {"offer_id": 9, "name": "Offer 9", "share": 80, "state": "active", "locked": False},
            ],
        }
    ]
    async with session_factory() as session:
        rows = list(
            await session.scalars(
                select(CampaignOfferModel)
                .where(CampaignOfferModel.campaign_id == 4)
                .order_by(CampaignOfferModel.offer_id)
            )
        )
        assert [(r.stream_id, r.offer_id, r.share, r.locked) for r in rows] == [
            (11, 7, 70, True),
            (11, 8, 0, False),
            (11, 9, 80, False),
        ]
    streams.respond(200, json=[])
    response = await client.get("/api/v1/campaigns/4/offers")
    assert response.json() == {"campaign_id": 4, "flows": []}
    async with session_factory() as session:
        rows = list(await session.scalars(select(CampaignOfferModel)))
        assert [(r.campaign_id, r.share) for r in rows] == [(5, 100)]
    assert all(call.request.method == "GET" for call in respx.calls)


@respx.mock
async def test_failed_refresh_keeps_cache_and_sanitizes_error(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session, session.begin():
        session.add(
            CampaignOfferModel(
                campaign_id=4,
                stream_id=11,
                stream_name="Local",
                offer_id=7,
                offer_name="Local",
                share=70,
                state="active",
                locked=True,
            )
        )
    respx.get(f"{BASE}/campaigns/4/streams").respond(200, json=[])
    respx.get(f"{BASE}/offers").respond(403, json={"message": "test-only-key private details"})
    response = await client.get("/api/v1/campaigns/4/offers")
    assert response.status_code == 502
    assert response.json()["code"] == "KEITARO_UNAVAILABLE"
    assert "test-only-key" not in response.text
    assert "private details" not in response.text
    async with session_factory() as session:
        row = (await session.scalars(select(CampaignOfferModel))).one()
        assert (row.share, row.locked, row.stream_name) == (70, True, "Local")


@pytest.mark.parametrize("campaign_id", ["0", "-1", "invalid"])
@respx.mock
async def test_invalid_campaign_id(client: AsyncClient, campaign_id: str) -> None:
    response = await client.get(f"/api/v1/campaigns/{campaign_id}/offers")
    assert response.status_code == 422
    assert not respx.calls


@respx.mock
async def test_upstream_timeout_returns_sanitized_503(client: AsyncClient) -> None:
    respx.get(f"{BASE}/offers").mock(side_effect=ReadTimeout("private test-only-key"))
    response = await client.get("/api/v1/offers")
    assert response.status_code == 503
    assert response.json()["code"] == "KEITARO_UNAVAILABLE"
    assert "private" not in response.text
    assert "test-only-key" not in response.text
    assert response.headers["x-request-id"]


@respx.mock
async def test_refresh_failure_after_flush_rolls_back_cache(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session, session.begin():
        session.add(
            CampaignOfferModel(
                campaign_id=4,
                stream_id=11,
                stream_name="Local",
                offer_id=7,
                offer_name="Local",
                share=70,
                state="active",
                locked=True,
            )
        )
    respx.get(f"{BASE}/campaigns/4/streams").respond(
        200, json=[{"id": 12, "name": "New", "offers": [{"offer_id": 8, "share": 100}]}]
    )
    respx.get(f"{BASE}/offers").respond(200, json=[{"id": 8, "name": "New"}])
    original_sync = SqlAlchemyCampaignOfferRepository.sync_from_keitaro

    async def failing_sync(
        self: SqlAlchemyCampaignOfferRepository,
        campaign_id: CampaignId,
        flows: list[KeitaroFlowSnapshot],
        seen_stream_ids: list[int],
        offer_names: dict[int, str],
    ) -> None:
        await original_sync(self, campaign_id, flows, seen_stream_ids, offer_names)
        raise DomainError("Injected failure after cache flush")

    monkeypatch.setattr(SqlAlchemyCampaignOfferRepository, "sync_from_keitaro", failing_sync)
    response = await client.get("/api/v1/campaigns/4/offers")
    assert response.status_code == 422
    async with session_factory() as session:
        row = (await session.scalars(select(CampaignOfferModel))).one()
        assert (row.stream_id, row.offer_id, row.share, row.locked, row.stream_name) == (
            11,
            7,
            70,
            True,
            "Local",
        )
