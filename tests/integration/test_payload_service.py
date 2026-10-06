from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PayloadNotFoundError
from core.repos.payloads import PayloadRepository
from core.repos.transformed_strings import TransformedStringRepository
from core.schemas import PayloadRequest
from core.services.hashing import HashingService
from core.services.interleave import InterleaveService
from core.services.payload_service import PayloadService
from core.services.transform_cache import TransformCache
from core.services.transformer import UpperCaseTransformer

SAMPLE = PayloadRequest(
    list_1=["first string", "second string", "third string"],
    list_2=["other string", "another string", "last string"],
)
SAMPLE_OUTPUT = (
    "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
)


@pytest.fixture
def service(db_session: AsyncSession, transformer: UpperCaseTransformer) -> PayloadService:
    hashing = HashingService(transformer.version)
    cache = TransformCache(
        repo=TransformedStringRepository(db_session),
        transformer=transformer,
        hashing=hashing,
        concurrency=10,
    )
    return PayloadService(
        payloads=PayloadRepository(db_session),
        cache=cache,
        hashing=hashing,
        interleaver=InterleaveService(),
    )


async def test_task_sample_produces_expected_output(service: PayloadService) -> None:
    result = await service.create(SAMPLE)

    assert result.created is True
    assert result.message == "Payload created"
    assert (await service.get(result.id)).output == SAMPLE_OUTPUT


async def test_same_request_is_reused_without_transformer_calls(
    service: PayloadService, transformer: UpperCaseTransformer
) -> None:
    first = await service.create(SAMPLE)
    calls_after_first = transformer.calls

    second = await service.create(SAMPLE)

    assert second.id == first.id
    assert second.created is False
    assert second.message == "Payload already exists"
    assert transformer.calls == calls_after_first == 6


async def test_overlapping_request_reuses_cached_strings(
    service: PayloadService, transformer: UpperCaseTransformer
) -> None:
    await service.create(SAMPLE)
    overlapping = PayloadRequest(list_1=["first string", "new"], list_2=["other string", "newer"])

    result = await service.create(overlapping)

    assert result.created is True
    assert (await service.get(result.id)).output == "FIRST STRING, OTHER STRING, NEW, NEWER"
    assert transformer.calls == 8


async def test_unknown_id_raises(service: PayloadService) -> None:
    with pytest.raises(PayloadNotFoundError):
        await service.get(uuid4())
