from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Payload
from utils.decorators import translate_storage_errors


class PayloadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @translate_storage_errors
    async def get_by_hash(self, input_hash: str) -> Payload | None:
        return await self._session.scalar(select(Payload).where(Payload.input_hash == input_hash))

    @translate_storage_errors
    async def get_by_id(self, payload_id: UUID) -> Payload | None:
        return await self._session.get(Payload, payload_id)

    @translate_storage_errors
    async def add(
        self, *, input_hash: str, output: str, request: dict[str, Any]
    ) -> tuple[UUID, bool]:
        statement = (
            insert(Payload)
            .values(input_hash=input_hash, output=output, request=request)
            .on_conflict_do_nothing(index_elements=["input_hash"])
            .returning(Payload.id)
        )
        new_id = await self._session.scalar(statement)
        await self._session.commit()
        if new_id is not None:
            return new_id, True

        existing = await self._session.execute(
            select(Payload.id).where(Payload.input_hash == input_hash)
        )
        return existing.scalar_one(), False
