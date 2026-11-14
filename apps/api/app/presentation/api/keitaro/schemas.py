from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.domain.keitaro.value_objects.country import CountryCode


class CreateCampaignRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    country_code: str
    offer_id: Annotated[int, Field(strict=True, gt=0)]
    domain_id: Annotated[int | None, Field(strict=True, gt=0)] = None
    group_id: Annotated[int, Field(strict=True, gt=0)]
    traffic_source_id: Annotated[int | None, Field(strict=True, gt=0)] = None

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str) -> str:
        return CountryCode(value).value


class CampaignSummaryResponse(BaseModel):
    id: int
    name: str
    state: str
    alias: str


class CreateTrafficSourceRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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


class AddOfferRequest(BaseModel):
    offer_id: Annotated[int, Field(strict=True, gt=0)]


class LockOfferRequest(BaseModel):
    locked: Annotated[bool, Field(strict=True)]
