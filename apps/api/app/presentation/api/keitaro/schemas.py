from pydantic import BaseModel


class CampaignSummaryResponse(BaseModel):
    id: int
    name: str
    state: str
    alias: str


class CatalogItemResponse(BaseModel):
    id: int
    name: str


class FormOptionsResponse(BaseModel):
    domains: list[CatalogItemResponse]
    groups: list[CatalogItemResponse]
    traffic_sources: list[CatalogItemResponse]


class OfferResponse(BaseModel):
    offer_id: int
    name: str
    share: int
    state: str
    locked: bool


class FlowOffersResponse(BaseModel):
    stream_id: int
    name: str
    offers: list[OfferResponse]


class OfferRotationResponse(BaseModel):
    campaign_id: int
    flows: list[FlowOffersResponse]
