from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot, KeitaroOfferSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)
from app.infrastructure.persistence.models import CampaignOfferModel


def flow(stream_id: int = 7) -> FlowOffers:
    return FlowOffers.rehydrate(
        StreamId(stream_id),
        "Main",
        [
            CampaignOffer(OfferId(1), "One", OfferShare(70), OfferState.ACTIVE, True),
            CampaignOffer(OfferId(2), "Two", OfferShare(0), OfferState.DELETED, False),
        ],
    )


async def test_save_round_trip_and_campaign_isolation(db_session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    await repository.save(CampaignId(3), flow())
    await repository.save(CampaignId(4), flow())
    await db_session.commit()
    db_session.expunge_all()

    assert await repository.list_by_campaign(CampaignId(3)) == [flow()]
    assert await repository.list_by_campaign(CampaignId(4)) == [flow()]
    assert await repository.list_by_campaign(CampaignId(99)) == []
    states = await db_session.scalars(
        select(CampaignOfferModel.state).order_by(CampaignOfferModel.id)
    )
    assert list(states) == [
        "active",
        "deleted",
        "active",
        "deleted",
    ]


async def test_save_updates_removes_stale_rows_and_orders_flows(db_session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    await repository.save(CampaignId(3), flow(9))
    await repository.save(CampaignId(3), flow())
    changed = FlowOffers.rehydrate(
        StreamId(7),
        "Renamed",
        [CampaignOffer(OfferId(2), "New name", OfferShare(100), OfferState.ACTIVE, True)],
    )
    await repository.save(CampaignId(3), changed)
    await repository.save(CampaignId(3), changed)
    await db_session.commit()
    db_session.expunge_all()
    assert await repository.list_by_campaign(CampaignId(3)) == [changed, flow(9)]


async def test_save_leaves_transaction_to_caller(db_session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    await repository.save(CampaignId(3), flow())
    await db_session.flush()
    await db_session.rollback()
    assert await repository.list_by_campaign(CampaignId(3)) == []


async def test_sync_reconciles_remote_shares_names_locks_and_missing_offers(
    db_session: AsyncSession,
) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    await repository.save(CampaignId(3), flow())
    await repository.save(CampaignId(4), flow())
    snapshots = [
        KeitaroFlowSnapshot(
            7,
            "Remote",
            [
                KeitaroOfferSnapshot(1, 20),
                KeitaroOfferSnapshot(2, 30),
                KeitaroOfferSnapshot(3, 50),
            ],
        )
    ]
    await repository.sync_from_keitaro(CampaignId(3), snapshots, [7], {1: "Updated"})
    await repository.sync_from_keitaro(CampaignId(3), snapshots, [7], {1: "Updated"})
    await db_session.commit()
    db_session.expunge_all()
    loaded = (await repository.list_by_campaign(CampaignId(3)))[0]
    assert loaded.name == "Remote"
    assert [
        (o.offer_id.value, o.name, o.share.value, o.state.value, o.locked) for o in loaded.offers
    ] == [
        (1, "Updated", 20, "active", True),
        (2, "Two", 30, "active", False),
        (3, "Offer 3", 50, "active", False),
    ]
    await repository.sync_from_keitaro(
        CampaignId(3),
        [KeitaroFlowSnapshot(7, "Newest", [KeitaroOfferSnapshot(3, 100)])],
        [7],
        {},
    )
    await db_session.commit()
    db_session.expunge_all()
    loaded = (await repository.list_by_campaign(CampaignId(3)))[0]
    assert loaded.name == "Newest"
    assert [(o.offer_id.value, o.share.value, o.state.value, o.locked) for o in loaded.offers] == [
        (1, 0, "deleted", False),
        (2, 0, "deleted", False),
        (3, 100, "active", False),
    ]
    assert await repository.list_by_campaign(CampaignId(4)) == [flow()]


async def test_sync_skips_empty_flow_contents_and_removes_obsolete_flows(
    db_session: AsyncSession,
) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    for stream in (7, 8, 9):
        await repository.save(CampaignId(3), flow(stream))

    class EmptyFlow:
        offers: list[KeitaroOfferSnapshot] = []

        @property
        def stream_id(self) -> int:
            raise AssertionError("Empty flow contents must not be parsed")

        @property
        def name(self) -> str:
            raise AssertionError("Empty flow contents must not be parsed")

    await repository.sync_from_keitaro(
        CampaignId(3),
        [
            cast(KeitaroFlowSnapshot, EmptyFlow()),
            KeitaroFlowSnapshot(9, "Retained", [KeitaroOfferSnapshot(1, 100)]),
        ],
        [7, 9],
        {},
    )
    await db_session.commit()
    assert [f.stream_id.value for f in await repository.list_by_campaign(CampaignId(3))] == [9]
    await repository.sync_from_keitaro(CampaignId(3), [], [], {})
    await db_session.commit()
    assert await repository.list_by_campaign(CampaignId(3)) == []


async def test_unique_campaign_stream_offer_constraint(db_session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(db_session)
    await repository.save(CampaignId(3), flow())
    await db_session.flush()
    db_session.add(
        CampaignOfferModel(
            campaign_id=3,
            stream_id=7,
            stream_name="Main",
            offer_id=1,
            offer_name="Duplicate",
            share=0,
            state="active",
            locked=False,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
