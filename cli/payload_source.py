import json
import sys
from pathlib import Path
from typing import Any


class PayloadSource:
    def __init__(self, inline: str | None, path: str | None) -> None:
        self._inline = inline
        self._path = path

    def read(self) -> Any:
        return json.loads(self._text())

    def _text(self) -> str:
        if self._inline is not None:
            return self._inline
        if self._path in (None, "-"):
            return sys.stdin.read()
        return Path(self._path).read_text(encoding="utf-8")
