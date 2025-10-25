from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from core.settings import settings

engine = create_async_engine(f"postgresql+asyncpg://{settings.POSTGRES_URI}",echo=True, future=True)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,       # <--- MISSING in your version
    expire_on_commit=False,    # <--- Recommended for async work
    autoflush=False
)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def database_health(db) -> bool:
    try:
        await db.execute(select(1))
        return True
    except Exception:
        return False
