import logging
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from api.dependencies import get_payload_service, get_session, get_transformer
from core.schemas import PayloadRequest
from core.settings import Settings
from db.session import build_engine, build_session_factory

SAMPLE = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}
SAMPLE_OUTPUT = (
    "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
)


async def test_sample_payload_is_created_then_read(client: AsyncClient) -> None:
    created = await client.post("/payload", json=SAMPLE)

    assert created.status_code == 201
    body = created.json()
    assert body["created"] is True
    assert body["message"] == "Payload created"
    payload_id = UUID(body["id"])

    read = await client.get(f"/payload/{payload_id}")

    assert read.status_code == 200
    assert read.json() == {"output": SAMPLE_OUTPUT}


async def test_identical_payload_is_reused(client: AsyncClient) -> None:
    first = await client.post("/payload", json=SAMPLE)
    second = await client.post("/payload", json=SAMPLE)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["created"] is False


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ({"list_1": ["a", "b", "c"], "list_2": ["d", "e"]}, "same length (got 3 and 2)"),
        ({"list_1": [], "list_2": []}, "list_1: List should have at least 1 item"),
        ({"list_1": ["a"], "list_2": ["b"], "list_3": ["c"]}, "list_3: Extra inputs"),
    ],
)
async def test_invalid_payload_is_rejected_with_detail(
    client: AsyncClient, payload: dict[str, list[str]], fragment: str
) -> None:
    response = await client.post("/payload", json=payload)

    assert response.status_code == 422
    assert fragment in response.json()["detail"]


async def test_too_many_items_is_rejected(client: AsyncClient) -> None:
    payload = {"list_1": ["a"] * 101, "list_2": ["b"] * 101}

    response = await client.post("/payload", json=payload)

    assert response.status_code == 413
    assert response.json() == {"detail": "list_1 exceeds the limit of 100 (got 101)"}


async def test_too_long_string_is_rejected(client: AsyncClient) -> None:
    payload = {"list_1": ["a" * 1001], "list_2": ["b"]}

    response = await client.post("/payload", json=payload)

    assert response.status_code == 413
    assert response.json() == {"detail": "string length exceeds the limit of 1000 (got 1001)"}


async def test_unknown_payload_is_not_found(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    payload_id = uuid4()

    with caplog.at_level(logging.WARNING, logger="api.errors"):
        response = await client.get(f"/payload/{payload_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Payload {payload_id} not found"}
    assert [record.levelno for record in caplog.records] == [logging.WARNING]


async def test_malformed_payload_id_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/payload/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["detail"].startswith("payload_id: Input should be a valid UUID")


async def test_stats_count_distinct_strings(client: AsyncClient) -> None:
    await client.post("/payload", json=SAMPLE)
    await client.post("/payload", json={"list_1": ["first string", "x"], "list_2": ["y", "z"]})

    response = await client.get("/stats")

    assert response.json() == {"transformer_calls": 9, "transformer_version": "v1"}


async def test_health_is_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_docs_render(client: AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_failing_transformer_is_a_bad_gateway(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_transformer] = lambda: FailingTransformer()

    with caplog.at_level(logging.ERROR):
        response = await client.post("/payload", json=SAMPLE)

    assert response.status_code == 502
    assert response.json() == {"detail": "Transformer failed"}
    assert_logged_once_with_traceback(caplog, "core.services.transform_cache")


async def test_unreachable_database_is_unavailable(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    unreachable = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:1/none", _env_file=None
    )
    factory = build_session_factory(build_engine(unreachable))

    async def broken_session():  # type: ignore[no-untyped-def]
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = broken_session

    with caplog.at_level(logging.ERROR):
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Storage is unavailable"}
    assert_logged_once_with_traceback(caplog, "utils.decorators")


async def test_unexpected_error_is_internal(
    app: FastAPI, client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_payload_service] = lambda: ExplodingService()

    with caplog.at_level(logging.ERROR):
        response = await client.post("/payload", json=SAMPLE)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}
    assert_logged_once_with_traceback(caplog, "api.errors")


def assert_logged_once_with_traceback(caplog: pytest.LogCaptureFixture, boundary: str) -> None:
    """The boundary logs the traceback once; api.errors adds one line without it."""
    with_traceback = [r for r in caplog.records if r.exc_info and r.exc_info[0] is not None]
    assert [r.name for r in with_traceback] == [boundary]
    outcomes = [r for r in caplog.records if r.name == "api.errors"]
    assert len(outcomes) == 1


class FailingTransformer:
    version = "v1"
    calls = 0

    async def transform(self, text: str) -> str:
        raise ConnectionError("external service down")


class ExplodingService:
    async def create(self, request: PayloadRequest) -> None:
        raise RuntimeError("boom")
