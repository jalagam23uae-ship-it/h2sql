"""
Seed Script to Create Sample Project

Creates a test project (ID 18) in the local database for testing purposes.
Run this after running database migrations.

Usage:
    python seed_project.py
"""
import asyncio
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

from db.projects.models import ProjectModel
import json

# Load environment variables
load_dotenv('.env')

# Database configuration
POSTGRES_HOST = os.getenv('APP_POSTGRES_DB_HOST', 'localhost')
POSTGRES_PORT = os.getenv('APP_POSTGRES_DB_PORT', '5432')
POSTGRES_DB = os.getenv('APP_POSTGRES_DB_NAME', 'database')
POSTGRES_USER = os.getenv('APP_POSTGRES_DB_USER', 'user')
POSTGRES_PASSWORD = os.getenv('APP_POSTGRES_DB_PASWD', 'password')

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


async def seed_project():
    """Create sample project in database"""

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if project already exists
            from sqlalchemy import select
            stmt = select(ProjectModel).where(ProjectModel.name == "test_project")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"\nOK: Project already exists: ID={existing.id}, name='{existing.name}'")
                return

            # Create connection profile
            connection_profile = {
                "db_type": "postgres",
                "con_string": f"{POSTGRES_HOST}:{POSTGRES_PORT}",  # host:port only, database passed separately
                "database": POSTGRES_DB,
                "username": POSTGRES_USER,
                "password": POSTGRES_PASSWORD
            }

            # Create project
            project = ProjectModel(
                name="test_project",
                train_id="test_train_001",
                connection=json.dumps(connection_profile),
                db_metadata="[]"  # Empty metadata initially
            )

            session.add(project)
            await session.commit()
            await session.refresh(project)

            print(f"\nOK: Created project successfully!")
            print(f"   ID: {project.id}")
            print(f"   Name: {project.name}")
            print(f"   Connection: PostgreSQL @ {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
            print(f"\nYou can now use this project_id={project.id} in your API calls.")

        except Exception as e:
            print(f"\nERROR: Error creating project: {e}")
            await session.rollback()
            raise

        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("H2SQL Project Seed Script")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DB}")
    print()

    asyncio.run(seed_project())

    print("\n" + "=" * 60)
    print("Seed complete!")
    print("=" * 60)
