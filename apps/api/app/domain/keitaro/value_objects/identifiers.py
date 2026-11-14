from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Campaign id must be positive")


@dataclass(frozen=True)
class StreamId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Stream id must be positive")


@dataclass(frozen=True)
class OfferId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Offer id must be positive")
