import json
import sys
from collections.abc import Sequence
from contextlib import nullcontext

import httpx
from pydantic import ValidationError
from pydantic_settings import SettingsError

from cli.payload_source import PayloadSource
from cli.runner import Runner
from cli.settings import CliSettings

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_SERVER = 2


def run(argv: Sequence[str] | None = None) -> int:
    try:
        settings = CliSettings(_cli_parse_args=list(argv) if argv is not None else True)
        body = PayloadSource(settings.json_, settings.input).read()
    except (SettingsError, ValidationError, json.JSONDecodeError, OSError) as error:
        print(f"cache-cli: {error}", file=sys.stderr)
        return EXIT_USAGE

    output = (
        nullcontext(sys.stdout)
        if settings.output == "-"
        else open(settings.output, "w", encoding="utf-8")  # noqa: SIM115
    )
    try:
        with output as stream, httpx.Client(base_url=str(settings.host), timeout=30) as client:
            succeeded = Runner(client, body, settings.repeat, stream).run()
    except httpx.HTTPError as error:
        print(f"cache-cli: {settings.host} unreachable: {error}", file=sys.stderr)
        return EXIT_SERVER
    return EXIT_OK if succeeded else EXIT_SERVER


def main() -> None:
    sys.exit(run())
