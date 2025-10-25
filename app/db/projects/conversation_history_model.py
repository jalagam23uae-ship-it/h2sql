"""
Conversation History database model for storing query context per project
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class ConversationHistoryModel(Base):
    """
    Conversation History Model

    Stores each question asked by users for a project to provide context
    for future queries. This allows the LLM to generate better SQL by
    understanding the conversation flow.
    """
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)

    # The user's question
    question = Column(Text, nullable=False)

    # The generated SQL (optional - for reference)
    generated_sql = Column(Text, nullable=True)

    # Response summary (optional - for reference)
    response_summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<ConversationHistoryModel(id={self.id}, project_id={self.project_id}, question='{self.question[:50]}...')>"
