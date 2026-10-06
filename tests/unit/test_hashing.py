import re

import pytest

from core.schemas import PayloadRequest
from core.services.hashing import HashingService

HEX_64 = re.compile(r"^[0-9a-f]{64}$")
payload_key = HashingService.payload_key


@pytest.fixture
def hashing() -> HashingService:
    return HashingService(transformer_version="v1")


def request(list_1: list[str], list_2: list[str]) -> PayloadRequest:
    return PayloadRequest(list_1=list_1, list_2=list_2)


def test_same_request_gives_same_payload_key() -> None:
    assert payload_key(request(["a", "b"], ["c", "d"])) == HashingService.payload_key(
        request(["a", "b"], ["c", "d"])
    )


def test_swapped_lists_give_different_payload_key() -> None:
    assert payload_key(request(["a"], ["b"])) != payload_key(request(["b"], ["a"]))


def test_reordered_items_give_different_payload_key() -> None:
    assert payload_key(request(["a", "b"], ["c", "d"])) != HashingService.payload_key(
        request(["b", "a"], ["c", "d"])
    )


def test_item_boundaries_are_part_of_payload_key() -> None:
    assert payload_key(request(["ab", "c"], ["x", "y"])) != HashingService.payload_key(
        request(["a", "bc"], ["x", "y"])
    )


def test_string_key_is_case_sensitive(hashing: HashingService) -> None:
    assert hashing.string_key("abc") != hashing.string_key("ABC")


def test_string_key_changes_with_version(hashing: HashingService) -> None:
    assert hashing.string_key("abc") != HashingService(transformer_version="v2").string_key("abc")


def test_string_key_is_stable(hashing: HashingService) -> None:
    assert hashing.string_key("abc") == hashing.string_key("abc")


def test_keys_are_64_lowercase_hex_characters(hashing: HashingService) -> None:
    assert HEX_64.match(hashing.string_key("abc"))
    assert HEX_64.match(payload_key(request(["a"], ["b"])))
