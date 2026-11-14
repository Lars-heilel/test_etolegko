from dataclasses import dataclass
from enum import Enum


class OfferState(str, Enum):  # noqa: UP042 - kept as (str, Enum) by the domain contract
    ACTIVE = "active"
    DELETED = "deleted"


@dataclass(frozen=True)
class OfferShare:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0 or self.value > 100:
            raise ValueError("Offer share must be between 0 and 100")
