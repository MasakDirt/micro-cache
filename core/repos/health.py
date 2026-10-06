from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from utils.decorators import translate_storage_errors


class HealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @translate_storage_errors
    async def ping(self) -> None:
        await self._session.execute(text("SELECT 1"))
