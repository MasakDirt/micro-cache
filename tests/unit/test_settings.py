import pytest
from pydantic import ValidationError

from core.settings import Settings, get_settings

ASYNC_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/micro_cache"


@pytest.fixture(autouse=True)
def database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", ASYNC_URL)
    get_settings.cache_clear()


def test_defaults_load_from_env() -> None:
    settings = Settings(_env_file=None)

    assert str(settings.database_url) == ASYNC_URL
    assert settings.transformer_delay_seconds == 0.1
    assert settings.transformer_concurrency == 10
    assert settings.max_list_length == 100
    assert settings.max_string_length == 1000


def test_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSFORMER_DELAY_SECONDS", "0")
    monkeypatch.setenv("MAX_LIST_LENGTH", "5")

    settings = Settings(_env_file=None)

    assert settings.transformer_delay_seconds == 0
    assert settings.max_list_length == 5


def test_negative_delay_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSFORMER_DELAY_SECONDS", "-1")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_sync_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/micro_cache")

    with pytest.raises(ValidationError, match=r"must use the 'postgresql\+asyncpg' scheme"):
        Settings(_env_file=None)


def test_get_settings_returns_one_instance() -> None:
    assert get_settings() is get_settings()
