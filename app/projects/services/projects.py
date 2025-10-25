import json
from fastapi import HTTPException
import httpx
from projects.utils import serialize
import projects.services.db_metadata as metadata
from h2s.helpers.httpHelper import deleteHttpRequest, getHttpRequest, patchHttpRequest, postHttpRequest
from projects.models import Project
import os

h2s_url = "http://localhost:11901"+"/h2s"


class Projects:
    async def get_projects(self):
        print("get_projects:::::::")
        headers = {
            "Authorization": "apikey",
            "Accept": "application/json"
        }
        print("::::")
        success, response = await getHttpRequest(f"{h2s_url}/db/projects?size=-1",headers=headers)
        print(success)
        print(response)
        if success:
            projects = Project.from_db(response["projects"])
            return projects

        raise response.raise_for_status()

    async def get_project(self, id):
        print("get_projects:::::::id ",id)
        headers = {
            "Authorization": "apikey",
            "Accept": "application/json"
        }
        success, response = await getHttpRequest(f"{h2s_url}/db/projects/{id}",headers=headers)
        if success:
            return response

        raise response.raise_for_status()

    async def get_project_by_name(self, name):
        print("get_projects:::::::name ",name)
        projects = await self.get_projects()
        for project in projects:
            if project.name == name:
                return project
        return None

    def get_connector(self, project: Project):
        connector = metadata.get_connector(project.connection.db_type)
        connector.get_connection(project.connection)
        return connector

    async def get_connector_by_project_name(self, project_name: str):
        project = await self.get_project_by_name(project_name)
        if project is None:
            raise Exception("Project not found")

        return self.get_connector(project)

    async def update_existing_project(self, db_project, project: Project):
        db_project["name"] = project.name
        db_project["connection"] = serialize(project.connection)

        if project.db_metadata is not None and len(project.db_metadata) > 0:
            db_project["db_metadata"] = json.dumps(
                [table.to_dict() for table in project.db_metadata])

        success, response = await patchHttpRequest(
            f'{h2s_url}/db/projects/{db_project["id"]}', db_project)
        if not success:
            raise response.raise_for_status()

        return Project(**response)

    async def update_project(self, project: Project):
        if project.name is None or len(project.name.strip()) < 1:
            raise Exception("Project name is required")

        if project.id >= 1:
            old_project = await self.get_project(project.id)
            return await self.update_existing_project(old_project, project)
        else:
            payload = project.to_dict()
            success, response = await postHttpRequest(
                f'{h2s_url}/db/projects', payload)
            if not success:
                raise response.raise_for_status()

            return Project(**response)

    async def remove_project(self, project_id: int):
        success, response = await deleteHttpRequest(f'{h2s_url}/db/projects/{project_id}')
        if not success:
            raise response.raise_for_status()

        return f"Successfully deleted project with id: {project_id}"

    async def ingest_train_metadata(self, project: Project):
        try:
            async with httpx.AsyncClient() as client:
                post_data = {
                    "project_id": str(project.id),
                    "username": project.connection.username,
                    "input_schemas": [schema.to_dict() for schema in project.db_metadata]
                }

                client.post(
                    f"{h2s_url}/vespa/ingest_schema",
                    json=post_data
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{h2s_url}/force_train",
                    json={
                        "project_id": project.id,
                        "project_name": project.name
                    },
                    timeout=60
                )

                return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Error while ingesting schema to vespa" + str(e)
            )
