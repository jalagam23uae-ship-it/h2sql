"""
Create conversation_history table directly
"""
import sys
import asyncio
sys.path.append("D:\\h2sql\\app")

from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from core.database import Base, engine
from core.settings import settings

print("=" * 80)
print("CREATE CONVERSATION_HISTORY TABLE")
print("=" * 80)
print(f"Database: PostgreSQL ({settings.POSTGRES_URI})")
print("=" * 80)

# Define table
class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    question = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    response_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

# Create table
async def create_table():
    print("\n[CREATING TABLE]")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("[SUCCESS] conversation_history table created!")

        # Verify table exists
        async with engine.connect() as conn:
            result = await conn.execute(
                sqlalchemy.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'conversation_history'"
                )
            )
            rows = result.fetchall()

            if rows:
                print(f"[VERIFIED] Table 'conversation_history' exists in database")

                # Show columns
                result = await conn.execute(
                    sqlalchemy.text(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_name = 'conversation_history' "
                        "ORDER BY ordinal_position"
                    )
                )
                columns = result.fetchall()
                print(f"\nColumns ({len(columns)}):")
                for col in columns:
                    nullable = 'NULL' if col[2] == 'YES' else 'NOT NULL'
                    print(f"  - {col[0]:20s} {col[1]:20s} {nullable}")

                # Show indexes
                result = await conn.execute(
                    sqlalchemy.text(
                        "SELECT indexname, indexdef "
                        "FROM pg_indexes "
                        "WHERE tablename = 'conversation_history'"
                    )
                )
                indexes = result.fetchall()
                print(f"\nIndexes ({len(indexes)}):")
                for idx in indexes:
                    print(f"  - {idx[0]}")
            else:
                print("[ERROR] Table not found after creation")

    except Exception as e:
        print(f"[ERROR] Failed to create table: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)

# Run async function
import sqlalchemy
asyncio.run(create_table())
