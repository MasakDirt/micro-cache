from uuid import UUID


class MicroCacheError(Exception):
    pass


class PayloadNotFoundError(MicroCacheError):
    def __init__(self, payload_id: UUID) -> None:
        super().__init__(f"Payload {payload_id} not found")
        self.payload_id = payload_id


class PayloadTooLargeError(MicroCacheError):
    def __init__(self, what: str, limit: int, actual: int) -> None:
        super().__init__(f"{what} exceeds the limit of {limit} (got {actual})")
        self.what = what
        self.limit = limit
        self.actual = actual


class StorageError(MicroCacheError):
    def __init__(self) -> None:
        super().__init__("Storage is unavailable")


class TransformerError(MicroCacheError):
    def __init__(self) -> None:
        super().__init__("Transformer failed")
