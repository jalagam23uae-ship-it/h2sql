"""
Local Project Management Service

Provides CRUD operations for projects stored in local PostgreSQL database.
This eliminates the dependency on external /h2s/db/projects API.
"""
import json
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from db.projects.models import ProjectModel
from projects.models import Project, ConnectionProfile, TableSchema

logger = logging.getLogger(__name__)


class LocalProjects:
    """Local project management using PostgreSQL database"""

    @staticmethod
    async def get_project(db: AsyncSession, project_id: int) -> Optional[Project]:
        """
        Get project by ID from local database

        Args:
            db: Database session
            project_id: Project ID

        Returns:
            Project object or None if not found
        """
        try:
            stmt = select(ProjectModel).where(ProjectModel.id == project_id)
            result = await db.execute(stmt)
            project_model = result.scalar_one_or_none()

            if not project_model:
                return None

            # Convert database model to Project object
            return Project(
                id=project_model.id,
                name=project_model.name,
                train_id=project_model.train_id,
                connection=project_model.connection,  # JSON string
                db_metadata=project_model.db_metadata  # JSON string
            )

        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}")
            return None

    @staticmethod
    async def get_project_by_name(db: AsyncSession, name: str) -> Optional[Project]:
        """
        Get project by name from local database

        Args:
            db: Database session
            name: Project name

        Returns:
            Project object or None if not found
        """
        try:
            stmt = select(ProjectModel).where(ProjectModel.name == name)
            result = await db.execute(stmt)
            project_model = result.scalar_one_or_none()

            if not project_model:
                return None

            return Project(
                id=project_model.id,
                name=project_model.name,
                train_id=project_model.train_id,
                connection=project_model.connection,
                db_metadata=project_model.db_metadata
            )

        except Exception as e:
            logger.error(f"Error fetching project '{name}': {e}")
            return None

    @staticmethod
    async def get_all_projects(db: AsyncSession) -> List[Project]:
        """
        Get all projects from local database

        Args:
            db: Database session

        Returns:
            List of Project objects
        """
        try:
            stmt = select(ProjectModel)
            result = await db.execute(stmt)
            project_models = result.scalars().all()

            projects = []
            for pm in project_models:
                projects.append(Project(
                    id=pm.id,
                    name=pm.name,
                    train_id=pm.train_id,
                    connection=pm.connection,
                    db_metadata=pm.db_metadata
                ))

            return projects

        except Exception as e:
            logger.error(f"Error fetching all projects: {e}")
            return []

    @staticmethod
    async def create_project(
        db: AsyncSession,
        name: str,
        connection: ConnectionProfile,
        db_metadata: Optional[List[TableSchema]] = None,
        train_id: Optional[str] = None
    ) -> Project:
        """
        Create a new project in local database

        Args:
            db: Database session
            name: Project name (must be unique)
            connection: Database connection profile
            db_metadata: Optional table schema metadata
            train_id: Optional training ID

        Returns:
            Created Project object

        Raises:
            HTTPException: If project with name already exists
        """
        try:
            # Check if project with this name already exists
            existing = await LocalProjects.get_project_by_name(db, name)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Project with name '{name}' already exists"
                )

            # Serialize connection and metadata
            from projects.utils import serialize
            connection_json = serialize(connection)
            metadata_json = json.dumps([t.to_dict() for t in db_metadata]) if db_metadata else "[]"

            # Create database model
            project_model = ProjectModel(
                name=name,
                train_id=train_id,
                connection=connection_json,
                db_metadata=metadata_json
            )

            db.add(project_model)
            await db.commit()
            await db.refresh(project_model)

            logger.info(f"Created project: id={project_model.id}, name='{name}'")

            # Return Project object
            return Project(
                id=project_model.id,
                name=project_model.name,
                train_id=project_model.train_id,
                connection=connection_json,
                db_metadata=metadata_json
            )

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating project '{name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create project: {str(e)}"
            )

    @staticmethod
    async def update_project(db: AsyncSession, project: Project) -> Project:
        """
        Update an existing project in local database

        Args:
            db: Database session
            project: Project object with updated data

        Returns:
            Updated Project object

        Raises:
            HTTPException: If project not found
        """
        try:
            stmt = select(ProjectModel).where(ProjectModel.id == project.id)
            result = await db.execute(stmt)
            project_model = result.scalar_one_or_none()

            if not project_model:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project with ID {project.id} not found"
                )

            # Update fields
            from projects.utils import serialize
            project_model.name = project.name
            project_model.train_id = project.train_id
            project_model.connection = serialize(project.connection)
            project_model.db_metadata = json.dumps(
                [t.to_dict() for t in project.db_metadata]
            ) if project.db_metadata else "[]"

            await db.commit()
            await db.refresh(project_model)

            logger.info(f"Updated project: id={project.id}, name='{project.name}'")

            return Project(
                id=project_model.id,
                name=project_model.name,
                train_id=project_model.train_id,
                connection=project_model.connection,
                db_metadata=project_model.db_metadata
            )

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating project {project.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update project: {str(e)}"
            )

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: int) -> bool:
        """
        Delete a project from local database

        Args:
            db: Database session
            project_id: Project ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: On database error
        """
        try:
            stmt = select(ProjectModel).where(ProjectModel.id == project_id)
            result = await db.execute(stmt)
            project_model = result.scalar_one_or_none()

            if not project_model:
                return False

            await db.delete(project_model)
            await db.commit()

            logger.info(f"Deleted project: id={project_id}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting project {project_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete project: {str(e)}"
            )
