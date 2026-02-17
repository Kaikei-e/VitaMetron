import logging

import asyncpg

from app.config import Settings

logger = logging.getLogger(__name__)


async def create_pool(settings: Settings) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=2,
        max_size=10,
    )
    logger.info("Database connection pool created")
    return pool


async def ping(pool: asyncpg.Pool) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        logger.exception("Database ping failed")
        return False
