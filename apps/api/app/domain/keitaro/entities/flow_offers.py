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
        flow = cls(stream_id=stream_id, name=name, offers=offers)
        ids = [item.offer_id.value for item in offers]
        if len(ids) != len(set(ids)):
            raise OfferAlreadyExistsError("Flow contains duplicate offers")
        return flow

    def _find(self, offer_id: OfferId) -> CampaignOffer:
        for item in self.offers:
            if item.offer_id == offer_id:
                return item
        raise OfferNotFoundError(f"Offer {offer_id.value} is not in the flow")

    def add_offer(self, offer_id: OfferId, name: str) -> None:
        if any(item.offer_id == offer_id for item in self.offers):
            raise OfferAlreadyExistsError(f"Offer {offer_id.value} already exists in the flow")
        self.offers.append(
            CampaignOffer(
                offer_id=offer_id,
                name=name,
                share=OfferShare(0),
                state=OfferState.ACTIVE,
                locked=False,
            )
        )
        self._rebalance()

    def delete_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        item.state = OfferState.DELETED
        item.locked = False
        item.share = OfferShare(0)
        self._rebalance()

    def restore_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        item.state = OfferState.ACTIVE
        item.locked = False
        item.share = OfferShare(0)
        self._rebalance()

    def set_locked(self, offer_id: OfferId, locked: bool) -> None:
        item = self._find(offer_id)
        if item.state is OfferState.DELETED:
            raise OfferNotFoundError(f"Offer {offer_id.value} is deleted")
        item.locked = locked
        self._rebalance()

    def active_offers(self) -> list[CampaignOffer]:
        return [item for item in self.offers if item.is_active]

    def _rebalance(self) -> None:
        for item in self.offers:
            if not item.is_active:
                item.share = OfferShare(0)

        active = self.active_offers()
        if not active:
            return

        fixed = sum(item.share.value for item in active if item.locked)
        if fixed > 100:
            raise ShareTotalError("Locked shares exceed 100 percent")

        unlocked = [item for item in active if not item.locked]
        for share, item in zip(distribute(100 - fixed, len(unlocked)), unlocked, strict=True):
            item.share = OfferShare(share)
