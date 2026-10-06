from hashlib import sha256

from core.schemas import PayloadRequest


class HashingService:
    def __init__(self, transformer_version: str) -> None:
        self._version = transformer_version

    def string_key(self, text: str) -> str:
        return sha256(f"{self._version}\0{text}".encode()).hexdigest()

    @staticmethod
    def payload_key(request: PayloadRequest) -> str:
        """Identity of a request is its canonical JSON"""
        return sha256(request.model_dump_json().encode()).hexdigest()
