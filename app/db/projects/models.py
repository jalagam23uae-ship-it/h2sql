"""
Project database model for local storage
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from core.database import Base


class ProjectModel(Base):
    """
    Local project storage model

    Stores project metadata including database connection details
    and table schema information.
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    train_id = Column(String(255), nullable=True)

    # Connection profile stored as JSON string
    connection = Column(Text, nullable=False)

    # Database metadata stored as JSON string
    db_metadata = Column(Text, nullable=True)

    # Timestamps (using existing column names)
    create_date = Column(DateTime(timezone=True), server_default=func.now())
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ProjectModel(id={self.id}, name='{self.name}')>"
