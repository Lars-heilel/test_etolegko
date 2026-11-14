from app.domain.keitaro.services.share_distribution import distribute


def test_even_split() -> None:
    assert distribute(100, 4) == [25, 25, 25, 25]


def test_remainder_goes_to_first_offers() -> None:
    assert distribute(100, 3) == [34, 33, 33]


def test_zero_count_returns_empty_list() -> None:
    assert distribute(100, 0) == []


def test_negative_count_returns_empty_list() -> None:
    assert distribute(100, -1) == []


def test_negative_total_is_clamped_to_zero() -> None:
    assert distribute(-10, 3) == [0, 0, 0]


def test_split_preserves_the_total() -> None:
    assert sum(distribute(100, 7)) == 100
