"""
Local Projects API Endpoints

Provides REST API for managing projects in local database
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from projects.services.local_projects import LocalProjects
from projects.models import Project, ConnectionProfile, TableSchema
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/h2s/db/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    """Request to create a new project"""
    name: str
    db_type: str
    con_string: str
    database: str
    username: str
    password: str
    train_id: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response model"""
    id: int
    name: str
    train_id: Optional[str]
    connection: dict
    db_metadata: list

    class Config:
        from_attributes = True


@router.get("")
async def get_all_projects(
    size: int = -1,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects from local database

    Args:
        size: Limit number of results (-1 for all)
        db: Database session

    Returns:
        List of projects with metadata
    """
    try:
        import json
        from projects.utils import serialize
        projects = await LocalProjects.get_all_projects(db)

        # Convert to response format
        response = []
        for project in projects:
            # Serialize connection and metadata properly
            if hasattr(project.connection, '__dict__'):
                conn_data = project.connection.__dict__
            elif isinstance(project.connection, str):
                conn_data = json.loads(project.connection)
            else:
                conn_data = {}

            if isinstance(project.db_metadata, list):
                meta_data = [t.to_dict() if hasattr(t, 'to_dict') else t for t in project.db_metadata]
            elif isinstance(project.db_metadata, str):
                meta_data = json.loads(project.db_metadata)
            else:
                meta_data = []

            response.append({
                "id": project.id,
                "name": project.name,
                "train_id": project.train_id,
                "connection": conn_data,
                "db_metadata": meta_data
            })

        if size > 0:
            response = response[:size]

        # Return format expected by original API
        return {"projects": response}

    except Exception as e:
        logger.error(f"Error fetching projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get project by ID from local database

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Project details with connection and metadata
    """
    try:
        import json
        project = await LocalProjects.get_project(db, project_id)

        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )

        # Convert to response format
        if hasattr(project.connection, '__dict__'):
            conn_data = project.connection.__dict__
        elif isinstance(project.connection, str):
            conn_data = json.loads(project.connection)
        else:
            conn_data = {}

        if isinstance(project.db_metadata, list):
            meta_data = [t.to_dict() if hasattr(t, 'to_dict') else t for t in project.db_metadata]
        elif isinstance(project.db_metadata, str):
            meta_data = json.loads(project.db_metadata)
        else:
            meta_data = []

        return {
            "id": project.id,
            "name": project.name,
            "train_id": project.train_id,
            "connection": conn_data,
            "db_metadata": meta_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project in local database

    Args:
        request: Project creation request
        db: Database session

    Returns:
        Created project details
    """
    try:
        import json
        # Create connection profile
        connection = ConnectionProfile(
            db_type=request.db_type,
            con_string=request.con_string,
            database=request.database,
            username=request.username,
            password=request.password
        )

        # Create project
        project = await LocalProjects.create_project(
            db=db,
            name=request.name,
            connection=connection,
            db_metadata=[],
            train_id=request.train_id
        )

        logger.info(f"Created project via API: {project.id}")

        # Convert to response format
        if hasattr(project.connection, '__dict__'):
            conn_data = project.connection.__dict__
        elif isinstance(project.connection, str):
            conn_data = json.loads(project.connection)
        else:
            conn_data = {}

        if isinstance(project.db_metadata, list):
            meta_data = [t.to_dict() if hasattr(t, 'to_dict') else t for t in project.db_metadata]
        elif isinstance(project.db_metadata, str):
            meta_data = json.loads(project.db_metadata)
        else:
            meta_data = []

        return {
            "id": project.id,
            "name": project.name,
            "train_id": project.train_id,
            "connection": conn_data,
            "db_metadata": meta_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a project from local database

    Args:
        project_id: Project ID to delete
        db: Database session

    Returns:
        204 No Content on success
    """
    try:
        deleted = await LocalProjects.delete_project(db, project_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
