import pytest

from core.services.interleave import InterleaveService


@pytest.fixture
def interleaver() -> InterleaveService:
    return InterleaveService()


def test_task_sample_is_interleaved_pairwise(interleaver: InterleaveService) -> None:
    first = ["FIRST STRING", "SECOND STRING", "THIRD STRING"]
    second = ["OTHER STRING", "ANOTHER STRING", "LAST STRING"]

    assert interleaver.interleave(first, second) == (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )


def test_single_element_lists(interleaver: InterleaveService) -> None:
    assert interleaver.interleave(["A"], ["B"]) == "A, B"


def test_default_separator_is_comma_space() -> None:
    assert InterleaveService.SEPARATOR == ", "
    assert InterleaveService(separator=" | ").interleave(["A"], ["B"]) == "A | B"


def test_length_mismatch_raises(interleaver: InterleaveService) -> None:
    with pytest.raises(ValueError):
        interleaver.interleave(["A", "B"], ["C"])
