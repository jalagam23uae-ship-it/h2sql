"""
Fix Project 22 Connection String

Updates the con_string format from "host:port/database" to "host:port"
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from dotenv import load_dotenv
from db.projects.models import ProjectModel

load_dotenv('.env')

POSTGRES_HOST = os.getenv('APP_POSTGRES_DB_HOST', 'localhost')
POSTGRES_PORT = os.getenv('APP_POSTGRES_DB_PORT', '5432')
POSTGRES_DB = os.getenv('APP_POSTGRES_DB_NAME', 'database')
POSTGRES_USER = os.getenv('APP_POSTGRES_DB_USER', 'user')
POSTGRES_PASSWORD = os.getenv('APP_POSTGRES_DB_PASWD', 'password')

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


async def fix_project():
    """Fix project 22 connection string"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Get project 22
            stmt = select(ProjectModel).where(ProjectModel.id == 22)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                print("ERROR: Project 22 not found")
                return

            # Parse current connection
            conn = json.loads(project.connection)
            print(f"\nCurrent connection:")
            print(f"  con_string: {conn.get('con_string')}")

            # Fix con_string format
            conn['con_string'] = f"{POSTGRES_HOST}:{POSTGRES_PORT}"

            print(f"\nFixed connection:")
            print(f"  con_string: {conn['con_string']}")

            # Update project
            project.connection = json.dumps(conn)
            await session.commit()

            print("\nOK: Project 22 updated successfully!")

        except Exception as e:
            print(f"\nERROR: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Fix Project 22 Connection String")
    print("=" * 60)
    asyncio.run(fix_project())
    print("=" * 60)
