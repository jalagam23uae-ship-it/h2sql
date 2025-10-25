"""Check actual table names in PostgreSQL database"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv('.env')

POSTGRES_HOST = os.getenv('APP_POSTGRES_DB_HOST', 'localhost')
POSTGRES_PORT = os.getenv('APP_POSTGRES_DB_PORT', '5432')
POSTGRES_DB = os.getenv('APP_POSTGRES_DB_NAME', 'database')
POSTGRES_USER = os.getenv('APP_POSTGRES_DB_USER', 'user')
POSTGRES_PASSWORD = os.getenv('APP_POSTGRES_DB_PASWD', 'password')

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


async def check_tables():
    """Check table names in database"""
    engine = create_async_engine(DATABASE_URL)

    async with engine.connect() as conn:
        # Query to get all tables with CUSTOMERS, CUSTOMERROLE, or EMPLOYEES in the name
        query = text("""
            SELECT table_name, table_schema
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND (table_name ILIKE '%customers%'
                OR table_name ILIKE '%customerrole%'
                OR table_name ILIKE '%employees%')
            ORDER BY table_name
        """)

        result = await conn.execute(query)
        tables = result.fetchall()

        print("=" * 60)
        print("Tables in database:")
        print("=" * 60)
        for table in tables:
            print(f"  {table[0]} (schema: {table[1]})")

        print(f"\nTotal tables found: {len(tables)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_tables())
