from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.repos.payloads import PayloadRepository
from core.repos.transformed_strings import TransformedStringRepository
from db.models import TransformedString

HASH_A = "a" * 64
HASH_B = "b" * 64
REQUEST = {"list_1": ["a"], "list_2": ["b"]}


@pytest.fixture
def payloads(db_session: AsyncSession) -> PayloadRepository:
    return PayloadRepository(db_session)


@pytest.fixture
def strings(db_session: AsyncSession) -> TransformedStringRepository:
    return TransformedStringRepository(db_session)


async def test_payload_add_is_created_once_then_reused(payloads: PayloadRepository) -> None:
    first_id, created = await payloads.add(input_hash=HASH_A, output="A, B", request=REQUEST)
    second_id, created_again = await payloads.add(input_hash=HASH_A, output="A, B", request=REQUEST)

    assert created is True
    assert created_again is False
    assert first_id == second_id


async def test_payload_is_readable_by_id_and_hash(payloads: PayloadRepository) -> None:
    payload_id, _ = await payloads.add(input_hash=HASH_A, output="A, B", request=REQUEST)

    by_id = await payloads.get_by_id(payload_id)
    by_hash = await payloads.get_by_hash(HASH_A)

    assert by_id is not None and by_id.output == "A, B"
    assert by_hash is not None and by_hash.id == payload_id
    assert by_id.request == REQUEST


async def test_unknown_payload_id_returns_none(payloads: PayloadRepository) -> None:
    assert await payloads.get_by_id(uuid4()) is None


async def test_duplicate_string_keeps_first_row(strings: TransformedStringRepository) -> None:
    await strings.add([row(HASH_A, "first")])
    await strings.add([row(HASH_A, "second")])

    assert await strings.get_outputs([HASH_A]) == {HASH_A: "FIRST"}


async def test_get_outputs_returns_only_existing_hashes(
    strings: TransformedStringRepository,
) -> None:
    await strings.add([row(HASH_A, "a")])

    assert await strings.get_outputs([HASH_A, HASH_B]) == {HASH_A: "A"}


async def test_empty_inputs_are_no_ops(strings: TransformedStringRepository) -> None:
    await strings.add([])

    assert await strings.get_outputs([]) == {}


def row(hash_: str, text: str) -> TransformedString:
    return TransformedString(hash=hash_, input=text, output=text.upper(), transformer_version="v1")
