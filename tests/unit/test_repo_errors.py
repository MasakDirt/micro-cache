import logging

import pytest
from sqlalchemy.exc import OperationalError

from core.exceptions import StorageError
from utils.decorators import translate_storage_errors


@translate_storage_errors
async def failing(reason: str) -> str:
    raise OperationalError("SELECT 1", {}, Exception(reason))


@translate_storage_errors
async def refused() -> None:
    raise ConnectionRefusedError("connection refused")


@translate_storage_errors
async def working(value: str) -> str:
    return value


async def test_sqlalchemy_errors_become_storage_errors(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR), pytest.raises(StorageError) as excinfo:
        await failing("connection refused")

    assert isinstance(excinfo.value.__cause__, OperationalError)
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "failing failed"
    assert caplog.records[0].exc_info is not None


async def test_connection_failures_become_storage_errors() -> None:
    with pytest.raises(StorageError) as excinfo:
        await refused()

    assert isinstance(excinfo.value.__cause__, ConnectionRefusedError)


async def test_results_pass_through() -> None:
    assert await working("ok") == "ok"
