from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogItem:
    id: int
    name: str


@dataclass(frozen=True)
class CampaignSummary:
    id: int
    name: str
    state: str
    alias: str


@dataclass(frozen=True)
class KeitaroOfferSnapshot:
    offer_id: int
    share: int


@dataclass(frozen=True)
class KeitaroFlowSnapshot:
    stream_id: int
    name: str
    offers: list[KeitaroOfferSnapshot]
