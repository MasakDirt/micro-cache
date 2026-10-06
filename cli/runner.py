import json
import time
from collections.abc import Callable
from typing import Any, TextIO

import httpx


class Runner:
    def __init__(self, client: httpx.Client, body: Any, repeat: int, output: TextIO) -> None:
        self._client = client
        self._body = body
        self._repeat = repeat
        self._output = output

    def run(self) -> bool:
        succeeded = True
        for iteration in range(1, self._repeat + 1):
            line = self._iteration(iteration)
            succeeded &= line["get_status"] == 200
            self._output.write(json.dumps(line) + "\n")
        return succeeded

    def _iteration(self, iteration: int) -> dict[str, Any]:
        created, post_ms = self._timed(lambda: self._client.post("/payload", json=self._body))
        line: dict[str, Any] = {
            "iteration": iteration,
            "post_status": created.status_code,
            "post_ms": post_ms,
            "id": None,
            "get_status": None,
            "get_ms": None,
            "body": created.json(),
        }
        if not created.is_success:
            return line
        payload_id = created.json()["id"]
        read, get_ms = self._timed(lambda: self._client.get(f"/payload/{payload_id}"))
        line.update(id=payload_id, get_status=read.status_code, get_ms=get_ms, body=read.json())
        return line

    @staticmethod
    def _timed[T](call: Callable[[], T]) -> tuple[T, float]:
        started = time.perf_counter()
        result = call()
        return result, round((time.perf_counter() - started) * 1000, 1)
