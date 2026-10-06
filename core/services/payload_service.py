from uuid import UUID

from core.exceptions import PayloadNotFoundError
from core.repos.payloads import PayloadRepository
from core.schemas import PayloadCreated, PayloadRead, PayloadRequest
from core.services.hashing import HashingService
from core.services.interleave import InterleaveService
from core.services.transform_cache import TransformCache


class PayloadService:
    def __init__(
        self,
        payloads: PayloadRepository,
        cache: TransformCache,
        hashing: HashingService,
        interleaver: InterleaveService,
    ) -> None:
        self._payloads = payloads
        self._cache = cache
        self._hashing = hashing
        self._interleaver = interleaver

    async def create(self, request: PayloadRequest) -> PayloadCreated:
        input_hash = self._hashing.payload_key(request)
        if (existing := await self._payloads.get_by_hash(input_hash)) is not None:
            return self._created(existing.id, created=False)

        outputs = await self._cache.transform_all(request.list_1 + request.list_2)
        output = self._interleaver.interleave(
            [outputs[text] for text in request.list_1],
            [outputs[text] for text in request.list_2],
        )
        payload_id, created = await self._payloads.add(
            input_hash=input_hash, output=output, request=request.model_dump()
        )
        return self._created(payload_id, created)

    async def get(self, payload_id: UUID) -> PayloadRead:
        payload = await self._payloads.get_by_id(payload_id)
        if payload is None:
            raise PayloadNotFoundError(payload_id)

        return PayloadRead(output=payload.output)

    @staticmethod
    def _created(payload_id: UUID, created: bool) -> PayloadCreated:
        message = "Payload created" if created else "Payload already exists"
        return PayloadCreated(id=payload_id, created=created, message=message)
