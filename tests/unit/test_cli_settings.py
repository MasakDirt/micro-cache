import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from cli.settings import CliSettings


def parse(*argv: str) -> CliSettings:
    return CliSettings(_cli_parse_args=list(argv))


def test_defaults() -> None:
    settings = parse()

    assert str(settings.host) == "http://localhost:8000/"
    assert settings.repeat == 1
    assert settings.input is None
    assert settings.json_ is None
    assert settings.output == "-"


def test_short_flags() -> None:
    settings = parse("-H", "http://api:9000", "-r", "3", "-j", "{}", "-o", "out.jsonl")

    assert str(settings.host) == "http://api:9000/"
    assert settings.repeat == 3
    assert settings.json_ == "{}"
    assert settings.output == "out.jsonl"


def test_long_flags() -> None:
    settings = parse("--host", "http://api:9000", "--repeat", "2", "--input", "-")

    assert str(settings.host) == "http://api:9000/"
    assert settings.repeat == 2
    assert settings.input == "-"


def test_repeat_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        parse("-r", "0")


def test_input_and_json_are_exclusive() -> None:
    with pytest.raises(ValidationError, match="cannot be combined"):
        parse("-i", "body.json", "-j", "{}")


def test_unknown_flag_is_an_error_not_an_exit() -> None:
    with pytest.raises(SettingsError):
        parse("--bogus")


def test_environment_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "http://hijacked:1")
    monkeypatch.setenv("host", "http://hijacked:1")

    assert str(parse().host) == "http://localhost:8000/"
