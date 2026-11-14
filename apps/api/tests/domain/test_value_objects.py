import dataclasses

import pytest

from app.domain.keitaro.value_objects.country import CountryCode
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


def test_campaign_id_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError):
        CampaignId(0)
    with pytest.raises(ValueError):
        CampaignId(-1)


def test_stream_id_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError):
        StreamId(0)
    with pytest.raises(ValueError):
        StreamId(-1)


def test_offer_id_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError):
        OfferId(0)
    with pytest.raises(ValueError):
        OfferId(-1)


def test_identifiers_are_compared_by_value() -> None:
    assert OfferId(5) == OfferId(5)
    assert OfferId(5) != OfferId(6)


def test_offer_share_accepts_the_percentage_range() -> None:
    assert OfferShare(0).value == 0
    assert OfferShare(100).value == 100


def test_offer_share_rejects_values_outside_the_percentage_range() -> None:
    with pytest.raises(ValueError):
        OfferShare(-1)
    with pytest.raises(ValueError):
        OfferShare(101)


def test_offer_share_is_immutable() -> None:
    share = OfferShare(50)

    with pytest.raises(dataclasses.FrozenInstanceError):
        share.value = 10  # type: ignore[misc]


def test_offer_state_values() -> None:
    assert OfferState.ACTIVE.value == "active"
    assert OfferState.DELETED.value == "deleted"


def test_country_code_is_normalized_to_upper_case() -> None:
    assert CountryCode("us").value == "US"
    assert CountryCode(" us ").value == "US"


def test_country_code_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError):
        CountryCode("USA")
    with pytest.raises(ValueError):
        CountryCode("1A")
    with pytest.raises(ValueError):
        CountryCode("")
