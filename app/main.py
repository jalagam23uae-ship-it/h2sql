"""
H2SQL - Standalone API for Data Upload and Query Execution
Exposes 8 key endpoints for database operations + local project management
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from projects.services import data_upload_api, projects_api
import uvicorn

app = FastAPI(
    title="H2SQL API",
    version="1.0.0",
    description="Standalone API for data upload, query execution, and visualization with local project management"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_upload_api.router)
app.include_router(projects_api.router)  # Local project management

@app.get("/")
async def root():
    return {
        "message": "H2SQL API",
        "version": "1.0.0",
        "endpoints": [
            "/h2s/data-upload/publish",
            "/h2s/data-upload/batch-publish",
            "/h2s/data-upload/validate-connection/{data_source_id}",
            "/h2s/data-upload/upload",
            "/h2s/data-upload/recommendations/question",
            "/h2s/data-upload/generatereport",
            "/h2s/data-upload/executequey",
            "/h2s/data-upload/graph"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=11901,
        reload=True
    )
