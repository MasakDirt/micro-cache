import pytest
from sqlalchemy.exc import OperationalError

from core.exceptions import StorageError
from utils.decorators import translate_storage_errors


@translate_storage_errors
async def failing(reason: str) -> str:
    raise OperationalError("SELECT 1", {}, Exception(reason))


@translate_storage_errors
async def working(value: str) -> str:
    return value


async def test_sqlalchemy_errors_become_storage_errors() -> None:
    with pytest.raises(StorageError) as excinfo:
        await failing("connection refused")

    assert isinstance(excinfo.value.__cause__, OperationalError)


async def test_results_pass_through() -> None:
    assert await working("ok") == "ok"
