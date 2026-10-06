import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import TransformerError
from core.repos.transformed_strings import TransformedStringRepository
from core.services.hashing import HashingService
from core.services.transform_cache import TransformCache
from core.services.transformer import Transformer, UpperCaseTransformer


@pytest.fixture
def cache(db_session: AsyncSession, transformer: UpperCaseTransformer) -> TransformCache:
    return build_cache(db_session, transformer)


async def test_repeated_string_is_transformed_once(
    cache: TransformCache, transformer: UpperCaseTransformer
) -> None:
    outputs = await cache.transform_all(["a", "a", "a"])

    assert outputs == {"a": "A"}
    assert transformer.calls == 1


async def test_second_call_transforms_only_new_strings(
    cache: TransformCache, transformer: UpperCaseTransformer
) -> None:
    await cache.transform_all(["a", "b", "c"])
    outputs = await cache.transform_all(["a", "b", "d"])

    assert outputs == {"a": "A", "b": "B", "d": "D"}
    assert transformer.calls == 4


async def test_misses_are_transformed_concurrently(db_session: AsyncSession) -> None:
    cache = build_cache(db_session, UpperCaseTransformer(delay_seconds=0.2))

    started = time.perf_counter()
    await cache.transform_all(["a", "b", "c", "d", "e"])

    assert time.perf_counter() - started < 0.5


async def test_transformer_failure_is_translated_and_stores_nothing(
    db_session: AsyncSession,
) -> None:
    cache = build_cache(db_session, FailingTransformer())

    with pytest.raises(TransformerError):
        await cache.transform_all(["a", "b"])

    assert (
        await TransformedStringRepository(db_session).get_outputs(
            [HashingService("v1").string_key("a")]
        )
        == {}
    )


class FailingTransformer:
    version = "v1"
    calls = 0

    async def transform(self, text: str) -> str:
        raise ConnectionError("external service down")


def build_cache(session: AsyncSession, transformer: Transformer) -> TransformCache:
    return TransformCache(
        repo=TransformedStringRepository(session),
        transformer=transformer,
        hashing=HashingService(transformer.version),
        concurrency=10,
    )
