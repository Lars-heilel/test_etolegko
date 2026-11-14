from dataclasses import dataclass


@dataclass(frozen=True)
class CountryCode:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("Country code must be ISO-3166 alpha-2")
        object.__setattr__(self, "value", normalized)
