from collections.abc import Iterable
from dataclasses import dataclass, field

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.exceptions import (
    OfferAlreadyExistsError,
    OfferNotFoundError,
    ShareTotalError,
)
from app.domain.keitaro.services.share_distribution import distribute
from app.domain.keitaro.value_objects.identifiers import OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


@dataclass(frozen=True)
class _ShareSnapshot:
    """Immutable view of one active offer used to plan a rebalance."""

    offer_id: OfferId
    share: int
    locked: bool


def _snapshot(offer: CampaignOffer) -> _ShareSnapshot:
    return _ShareSnapshot(offer_id=offer.offer_id, share=offer.share.value, locked=offer.locked)


def _snapshots(offers: Iterable[CampaignOffer]) -> list[_ShareSnapshot]:
    return [_snapshot(item) for item in offers]


@dataclass
class FlowOffers:
    stream_id: StreamId
    name: str
    offers: list[CampaignOffer] = field(default_factory=list)

    @classmethod
    def empty(cls, stream_id: StreamId, name: str) -> "FlowOffers":
        return cls(stream_id=stream_id, name=name)

    @classmethod
    def rehydrate(
        cls,
        stream_id: StreamId,
        name: str,
        offers: list[CampaignOffer],
    ) -> "FlowOffers":
        ids = [item.offer_id.value for item in offers]
        if len(ids) != len(set(ids)):
            raise OfferAlreadyExistsError("Flow contains duplicate offers")
        return cls(stream_id=stream_id, name=name, offers=list(offers))

    def _find(self, offer_id: OfferId) -> CampaignOffer:
        for item in self.offers:
            if item.offer_id == offer_id:
                return item
        raise OfferNotFoundError(f"Offer {offer_id.value} is not in the flow")

    def add_offer(self, offer_id: OfferId, name: str) -> None:
        if any(item.offer_id == offer_id for item in self.offers):
            raise OfferAlreadyExistsError(f"Offer {offer_id.value} already exists in the flow")
        new_offer = CampaignOffer(
            offer_id=offer_id,
            name=name,
            share=OfferShare(0),
            state=OfferState.ACTIVE,
            locked=False,
        )
        existing_active = [item for item in self.offers if item.is_active]
        pinned = (
            offer_id if existing_active and all(item.locked for item in existing_active) else None
        )
        plan = self._plan_shares([*_snapshots(existing_active), _snapshot(new_offer)], pinned)
        self.offers.append(new_offer)
        self._apply_shares(plan)

    def delete_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        plan = self._plan_shares(
            [
                _snapshot(current)
                for current in self.offers
                if current.is_active and current.offer_id != offer_id
            ]
        )
        item.state = OfferState.DELETED
        item.locked = False
        item.share = OfferShare(0)
        self._apply_shares(plan)

    def restore_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        active = [
            _ShareSnapshot(offer_id=offer_id, share=0, locked=False)
            if current.offer_id == offer_id
            else _snapshot(current)
            for current in self.offers
            if current.is_active or current.offer_id == offer_id
        ]
        plan = self._plan_shares(active)
        item.state = OfferState.ACTIVE
        item.locked = False
        self._apply_shares(plan)

    def set_locked(self, offer_id: OfferId, locked: bool) -> None:
        item = self._find(offer_id)
        if item.state is OfferState.DELETED:
            raise OfferNotFoundError(f"Offer {offer_id.value} is deleted")
        active = [
            _ShareSnapshot(
                offer_id=current.offer_id,
                share=current.share.value,
                locked=locked,
            )
            if current.offer_id == offer_id
            else _snapshot(current)
            for current in self.offers
            if current.is_active
        ]
        plan = self._plan_shares(active)
        item.locked = locked
        self._apply_shares(plan)

    def active_offers(self) -> list[CampaignOffer]:
        return [item for item in self.offers if item.is_active]

    def _plan_shares(
        self,
        active: list[_ShareSnapshot],
        pinned: OfferId | None = None,
    ) -> dict[OfferId, int]:
        """Compute the new share of every active offer without touching the aggregate."""
        fixed = sum(item.share for item in active if item.locked)
        if fixed > 100:
            raise ShareTotalError("Locked shares exceed 100 percent")

        plan: dict[OfferId, int] = {}
        unlocked: list[_ShareSnapshot] = []
        for item in active:
            if item.locked:
                plan[item.offer_id] = item.share
            elif item.offer_id == pinned:
                plan[item.offer_id] = 0
            else:
                unlocked.append(item)

        if unlocked:
            available = 100 - fixed
            shares = distribute(available, len(unlocked))
            if fixed + sum(shares) != 100:
                raise ShareTotalError("Shares must add up to 100 percent")
            for share, item in zip(shares, unlocked, strict=True):
                plan[item.offer_id] = share
        return plan

    def _apply_shares(self, plan: dict[OfferId, int]) -> None:
        for item in self.offers:
            if item.offer_id in plan:
                item.share = OfferShare(plan[item.offer_id])
            elif not item.is_active:
                item.share = OfferShare(0)
