import pytest

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import (
    OfferAlreadyExistsError,
    OfferNotFoundError,
    ShareTotalError,
)
from app.domain.keitaro.value_objects.identifiers import OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


def offer(offer_id: int, share: int, state: OfferState = OfferState.ACTIVE, locked: bool = False):
    return CampaignOffer(
        offer_id=OfferId(offer_id),
        name=f"Offer {offer_id}",
        share=OfferShare(share),
        state=state,
        locked=locked,
    )


def shares(flow: FlowOffers) -> dict[int, int]:
    return {item.offer_id.value: item.share.value for item in flow.offers}


def test_add_fourth_offer_splits_25_percent() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")
    for offer_id in (1, 2, 3):
        flow.add_offer(OfferId(offer_id), f"Offer {offer_id}")

    flow.add_offer(OfferId(4), "Offer 4")

    assert shares(flow) == {1: 25, 2: 25, 3: 25, 4: 25}


def test_locked_offer_keeps_share_and_others_split_remainder() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50, locked=True), offer(2, 50)],
    )

    flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 50, 2: 25, 3: 25}


def test_delete_sets_zero_and_redistributes_to_active() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50), offer(2, 50)],
    )

    flow.delete_offer(OfferId(1))

    assert shares(flow) == {1: 0, 2: 100}
    assert flow.offers[0].state is OfferState.DELETED


def test_restore_joins_active_flow_equally() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 0, state=OfferState.DELETED), offer(2, 100)],
    )

    flow.restore_offer(OfferId(1))

    assert shares(flow) == {1: 50, 2: 50}


def test_all_active_locked_new_offer_gets_zero() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 40, locked=True)],
    )

    flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 60, 2: 40, 3: 0}


def test_duplicate_offer_is_rejected() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")
    flow.add_offer(OfferId(1), "Offer 1")

    with pytest.raises(OfferAlreadyExistsError):
        flow.add_offer(OfferId(1), "Offer 1")


def test_missing_offer_is_rejected() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")

    with pytest.raises(OfferNotFoundError):
        flow.delete_offer(OfferId(99))


def test_lock_rebalances_unlocked_offers() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50), offer(2, 50)],
    )

    flow.set_locked(OfferId(1), True)

    assert shares(flow) == {1: 50, 2: 50}


def test_rehydrate_rejects_duplicate_offers() -> None:
    with pytest.raises(OfferAlreadyExistsError):
        FlowOffers.rehydrate(
            StreamId(10),
            "Main",
            [offer(1, 50), offer(1, 50)],
        )


def test_locking_a_deleted_offer_is_rejected() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 0, state=OfferState.DELETED)],
    )

    with pytest.raises(OfferNotFoundError):
        flow.set_locked(OfferId(1), True)


def test_locked_shares_above_one_hundred_are_rejected() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 60, locked=True)],
    )

    with pytest.raises(ShareTotalError):
        flow.add_offer(OfferId(3), "Offer 3")


def test_active_offers_excludes_deleted_offers() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50), offer(2, 0, state=OfferState.DELETED)],
    )

    assert [item.offer_id.value for item in flow.active_offers()] == [1]


def test_failed_add_offer_leaves_the_flow_unchanged() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 60, locked=True)],
    )

    with pytest.raises(ShareTotalError):
        flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 60, 2: 60}
    assert [item.offer_id.value for item in flow.offers] == [1, 2]


def test_failed_delete_offer_leaves_the_flow_unchanged() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 60, locked=True), offer(3, 60, locked=True)],
    )

    with pytest.raises(ShareTotalError):
        flow.delete_offer(OfferId(2))

    assert shares(flow) == {1: 60, 2: 60, 3: 60}
    assert flow.offers[1].state is OfferState.ACTIVE


def test_failed_lock_leaves_the_flow_unchanged() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 60)],
    )

    with pytest.raises(ShareTotalError):
        flow.set_locked(OfferId(2), True)

    assert flow.offers[1].locked is False
    assert shares(flow) == {1: 60, 2: 60}


def test_new_offer_gets_zero_when_every_existing_active_offer_is_locked() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50, locked=True), offer(2, 50)],
    )

    flow.delete_offer(OfferId(2))
    flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 50, 2: 0, 3: 0}


def test_rehydrate_copies_the_offers_list() -> None:
    offers = [offer(1, 50)]
    flow = FlowOffers.rehydrate(StreamId(10), "Main", offers)

    offers.append(offer(2, 50))

    assert [item.offer_id.value for item in flow.offers] == [1]
