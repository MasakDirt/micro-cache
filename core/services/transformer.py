import asyncio
from typing import Protocol


class Transformer(Protocol):
    version: str
    calls: int

    async def transform(self, text: str) -> str: ...


class UpperCaseTransformer:
    version = "v1"

    def __init__(self, delay_seconds: float) -> None:
        self._delay = delay_seconds
        self.calls = 0

    async def transform(self, text: str) -> str:
        self.calls += 1
        await asyncio.sleep(self._delay)
        return text.upper()
