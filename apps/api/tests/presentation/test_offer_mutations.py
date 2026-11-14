from collections.abc import Iterator

import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import ShareTotalError
from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.infrastructure.config import get_settings
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)
from app.infrastructure.persistence.models import CampaignOfferModel

BASE = "https://tracker.example.com/admin_api/v1"
URL = "/api/v1/campaigns/42/flows/10/offers"


@pytest.fixture(autouse=True)
def tracker_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def seed(
    factory: async_sessionmaker[AsyncSession], share: int = 100, locked: bool = False
) -> None:
    async with factory() as session, session.begin():
        session.add(
            CampaignOfferModel(
                campaign_id=42,
                stream_id=10,
                stream_name="Main",
                offer_id=1,
                offer_name="One",
                share=share,
                state="active",
                locked=locked,
            )
        )


async def rows(factory: async_sessionmaker[AsyncSession]) -> list[tuple[int, int, str, bool]]:
    async with factory() as session:
        result = await session.scalars(
            select(CampaignOfferModel).order_by(CampaignOfferModel.offer_id)
        )
        return [(r.offer_id, r.share, r.state, r.locked) for r in result]


@respx.mock
async def test_add_delete_restore_and_lock(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory)
    respx.get(f"{BASE}/offers/2").respond(200, json={"id": 2, "name": "Two"})
    added = await client.post(URL, json={"offer_id": 2})
    assert added.status_code == 200
    assert added.json() == {
        "campaign_id": 42,
        "flows": [
            {
                "stream_id": 10,
                "name": "Main",
                "offers": [
                    {"offer_id": 1, "name": "One", "share": 50, "state": "active", "locked": False},
                    {"offer_id": 2, "name": "Two", "share": 50, "state": "active", "locked": False},
                ],
            }
        ],
    }
    duplicate = await client.post(URL, json={"offer_id": 2})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "OFFER_ALREADY_EXISTS"
    assert (await client.patch(f"{URL}/1/lock", json={"locked": True})).status_code == 200
    assert await rows(session_factory) == [(1, 50, "active", True), (2, 50, "active", False)]
    assert (await client.delete(f"{URL}/1")).status_code == 200
    assert await rows(session_factory) == [(1, 0, "deleted", False), (2, 100, "active", False)]
    duplicate = await client.post(URL, json={"offer_id": 1})
    assert duplicate.status_code == 409
    assert (await client.post(f"{URL}/1/restore")).status_code == 200
    assert await rows(session_factory) == [(1, 50, "active", False), (2, 50, "active", False)]
    assert all(call.request.method == "GET" for call in respx.calls)


@pytest.mark.parametrize("share", [70, 100])
@respx.mock
async def test_add_preserves_all_locked_shares(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession], share: int
) -> None:
    await seed(session_factory, share, True)
    respx.get(f"{BASE}/offers/2").respond(200, json={"id": 2, "name": "Two"})
    assert (await client.post(URL, json={"offer_id": 2})).status_code == 200
    assert await rows(session_factory) == [(1, share, "active", True), (2, 0, "active", False)]
    assert (await client.delete(f"{URL}/2")).status_code == 200
    assert await rows(session_factory) == [(1, share, "active", True), (2, 0, "deleted", False)]
    assert (await client.post(f"{URL}/2/restore")).status_code == 200
    assert await rows(session_factory) == [
        (1, share, "active", True),
        (2, 100 - share, "active", False),
    ]
    assert (await client.patch(f"{URL}/1/lock", json={"locked": False})).status_code == 200
    assert await rows(session_factory) == [(1, 50, "active", False), (2, 50, "active", False)]


@respx.mock
async def test_last_active_deletion_and_deleted_lock(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory, locked=True)
    assert (await client.delete(f"{URL}/1")).status_code == 200
    assert await rows(session_factory) == [(1, 0, "deleted", False)]
    assert (await client.patch(f"{URL}/1/lock", json={"locked": True})).status_code == 404
    assert (await client.post(f"{URL}/1/restore")).status_code == 200
    assert await rows(session_factory) == [(1, 100, "active", False)]


@respx.mock
async def test_restore_active_locked_offer_preserves_share(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory, 70, True)
    response = await client.post(f"{URL}/1/restore")
    assert response.status_code == 200
    assert await rows(session_factory) == [(1, 70, "active", True)]


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("DELETE", "/99", None),
        ("POST", "/99/restore", None),
        ("PATCH", "/99/lock", {"locked": True}),
    ],
)
@respx.mock
async def test_missing_offer_leaves_flow_unchanged(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    method: str,
    suffix: str,
    payload: dict[str, object] | None,
) -> None:
    await seed(session_factory)
    response = await client.request(method, URL + suffix, json=payload)
    assert response.status_code == 404
    assert await rows(session_factory) == [(1, 100, "active", False)]


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("POST", "", {"offer_id": 0}),
        ("POST", "", {"offer_id": True}),
        ("PATCH", "/1/lock", {"locked": "false"}),
        ("PATCH", "/1/lock", {}),
    ],
)
@respx.mock
async def test_invalid_mutation_payload(
    client: AsyncClient,
    method: str,
    suffix: str,
    payload: dict[str, object],
) -> None:
    response = await client.request(method, URL + suffix, json=payload)
    assert response.status_code == 422
    assert not respx.calls
    assert not respx.calls


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("POST", "", {"offer_id": 2}),
        ("DELETE", "/1", None),
        ("POST", "/1/restore", None),
        ("PATCH", "/1/lock", {"locked": True}),
    ],
)
@respx.mock
async def test_flow_must_belong_to_campaign(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    method: str,
    suffix: str,
    payload: dict[str, object] | None,
) -> None:
    await seed(session_factory)
    response = await client.request(method, URL.replace("42", "99") + suffix, json=payload)
    assert response.status_code == 404
    assert response.json()["code"] == "CAMPAIGN_NOT_FOUND"
    assert await rows(session_factory) == [(1, 100, "active", False)]
    assert not respx.calls


@respx.mock
async def test_failed_catalog_lookup_does_not_mutate(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await seed(session_factory)
    respx.get(f"{BASE}/offers/2").respond(500, json={"message": "private"})
    response = await client.post(URL, json={"offer_id": 2})
    assert response.status_code == 502
    assert "private" not in response.text
    assert await rows(session_factory) == [(1, 100, "active", False)]


@respx.mock
async def test_failure_after_flush_rolls_back_mutation(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed(session_factory)
    original_save = SqlAlchemyCampaignOfferRepository.save

    async def failing_save(
        self: SqlAlchemyCampaignOfferRepository,
        campaign_id: CampaignId,
        flow: FlowOffers,
    ) -> None:
        await original_save(self, campaign_id, flow)
        raise ShareTotalError("Injected failure after flush")

    monkeypatch.setattr(SqlAlchemyCampaignOfferRepository, "save", failing_save)
    response = await client.delete(f"{URL}/1")
    assert response.status_code == 422
    assert await rows(session_factory) == [(1, 100, "active", False)]
