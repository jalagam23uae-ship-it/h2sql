from sqlalchemy import Column, String, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from core.database import Base


class ResponseLogsModel(Base):
    """Model for storing query execution responses and analytics."""
    __tablename__ = "response_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    response_id = Column(String, index=True, nullable=False, unique=True)
    project_id = Column(String, index=True, nullable=False)
    llm_generated_sql = Column(Text, nullable=True)
    question = Column(Text, nullable=False)
    query_filter_data = Column(Text, nullable=True)  # JSON as string
    human_readable_answer = Column(Text, nullable=True)
    response_metadata = Column(Text, nullable=True, name='metadata')  # JSON as string - use column name 'metadata'
    quotation = Column(Text, nullable=True)
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    update_date = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
