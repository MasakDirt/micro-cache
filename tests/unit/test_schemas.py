import pytest
from pydantic import ValidationError

from core.schemas import ErrorResponse, PayloadRequest


def test_valid_payload_passes() -> None:
    request = PayloadRequest(list_1=["a", "b"], list_2=["c", "d"])

    assert request.list_1 == ["a", "b"]
    assert request.list_2 == ["c", "d"]


def test_mismatched_lengths_fail_with_counts() -> None:
    with pytest.raises(ValidationError) as excinfo:
        PayloadRequest(list_1=["a", "b", "c"], list_2=["d", "e"])

    assert "list_1 and list_2 must have the same length (got 3 and 2)" in str(excinfo.value)


@pytest.mark.parametrize("payload", [{"list_1": [], "list_2": []}, {"list_1": [], "list_2": ["a"]}])
def test_empty_lists_fail(payload: dict[str, list[str]]) -> None:
    with pytest.raises(ValidationError):
        PayloadRequest.model_validate(payload)


def test_empty_string_inside_list_passes() -> None:
    request = PayloadRequest(list_1=[""], list_2=["a"])

    assert request.list_1 == [""]


def test_unknown_field_fails() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        PayloadRequest.model_validate({"list_1": ["a"], "list_2": ["b"], "list_3": ["c"]})


def test_non_string_items_fail() -> None:
    with pytest.raises(ValidationError):
        PayloadRequest.model_validate({"list_1": [1], "list_2": ["b"]})


def test_error_response_serialises_detail() -> None:
    assert ErrorResponse(detail="payload not found").model_dump() == {"detail": "payload not found"}
