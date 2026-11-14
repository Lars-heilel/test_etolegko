from dataclasses import dataclass

from app.domain.keitaro.value_objects.identifiers import OfferId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


@dataclass
class CampaignOffer:
    offer_id: OfferId
    name: str
    share: OfferShare
    state: OfferState = OfferState.ACTIVE
    locked: bool = False

    @property
    def is_active(self) -> bool:
        return self.state is OfferState.ACTIVE
