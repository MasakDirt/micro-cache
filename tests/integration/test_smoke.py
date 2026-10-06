from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_answers(db_session: AsyncSession) -> None:
    assert (await db_session.execute(text("SELECT 1"))).scalar_one() == 1


async def test_migration_created_both_tables(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    assert {"transformed_strings", "payloads"} <= set(rows.scalars())
