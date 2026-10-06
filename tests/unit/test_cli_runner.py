import io
import json
from pathlib import Path

import httpx
import pytest
import respx

from cli.main import EXIT_OK, EXIT_SERVER, EXIT_USAGE, run

HOST = "http://api:9000"
BODY = '{"list_1":["a"],"list_2":["b"]}'
PAYLOAD_ID = "11111111-1111-1111-1111-111111111111"


def created(status: int) -> httpx.Response:
    return httpx.Response(status, json={"id": PAYLOAD_ID, "created": status == 201, "message": ""})


def lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


@respx.mock(base_url=HOST)
def test_repeat_records_every_round_trip(
    respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    respx_mock.post("/payload").mock(side_effect=[created(201), created(200)])
    respx_mock.get(f"/payload/{PAYLOAD_ID}").respond(200, json={"output": "A, B"})

    code = run(["-H", HOST, "-r", "2", "-j", BODY])

    first, second = lines(capsys)
    assert code == EXIT_OK
    assert (first["post_status"], second["post_status"]) == (201, 200)
    assert first["id"] == second["id"] == PAYLOAD_ID
    assert first["get_status"] == 200 and first["body"] == {"output": "A, B"}
    assert isinstance(first["post_ms"], float) and isinstance(first["get_ms"], float)


@respx.mock(base_url=HOST)
def test_rejected_payload_is_recorded_and_fails(
    respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    respx_mock.post("/payload").respond(422, json={"detail": "list_2: too short"})

    code = run(["-H", HOST, "-j", '{"list_1":["a"],"list_2":[]}'])

    (line,) = lines(capsys)
    assert code == EXIT_SERVER
    assert line["post_status"] == 422
    assert line["body"] == {"detail": "list_2: too short"}
    assert line["get_status"] is None and line["get_ms"] is None


@respx.mock(base_url=HOST, assert_all_called=False)
def test_unparseable_body_is_a_usage_error_without_requests(
    respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    route = respx_mock.post("/payload")

    code = run(["-H", HOST, "-j", "{not json"])

    assert code == EXIT_USAGE
    assert not route.called
    assert "cache-cli:" in capsys.readouterr().err


@respx.mock(base_url=HOST)
def test_unreachable_server_fails(
    respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    respx_mock.post("/payload").mock(side_effect=httpx.ConnectError("refused"))

    code = run(["-H", HOST, "-j", BODY])

    assert code == EXIT_SERVER
    assert "unreachable" in capsys.readouterr().err


@respx.mock(base_url=HOST)
def test_body_from_stdin_and_output_to_file(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    respx_mock.post("/payload").mock(return_value=created(201))
    respx_mock.get(f"/payload/{PAYLOAD_ID}").respond(200, json={"output": "A, B"})
    monkeypatch.setattr("sys.stdin", io.StringIO(BODY))
    out = tmp_path / "out.jsonl"

    code = run(["-H", HOST, "-i", "-", "-o", str(out)])

    assert code == EXIT_OK
    assert json.loads(out.read_text())["body"] == {"output": "A, B"}
