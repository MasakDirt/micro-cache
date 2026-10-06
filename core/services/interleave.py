class InterleaveService:
    SEPARATOR = ", "

    def __init__(self, separator: str = SEPARATOR) -> None:
        self._separator = separator

    def interleave(self, first: list[str], second: list[str]) -> str:
        return self._separator.join(
            item for pair in zip(first, second, strict=True) for item in pair
        )
