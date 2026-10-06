from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TransformedString
from utils.decorators import translate_storage_errors


class TransformedStringRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @translate_storage_errors
    async def get_outputs(self, hashes: Sequence[str]) -> dict[str, str]:
        if not hashes:
            return {}

        rows = await self._session.execute(
            select(TransformedString.hash, TransformedString.output).where(
                TransformedString.hash.in_(hashes)
            )
        )
        return {hash_: output for hash_, output in rows}

    @translate_storage_errors
    async def add(self, rows: Sequence[TransformedString]) -> None:
        if not rows:
            return

        values = [
            {
                "hash": row.hash,
                "input": row.input,
                "output": row.output,
                "transformer_version": row.transformer_version,
            }
            for row in rows
        ]
        await self._session.execute(
            insert(TransformedString).values(values).on_conflict_do_nothing(index_elements=["hash"])
        )
        await self._session.commit()
