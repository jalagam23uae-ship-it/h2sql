# Local Project Management Setup

**Solution:** Local PostgreSQL-based project storage to eliminate dependency on external `/h2s/db/projects` service.

---

## 🎯 Problem Solved

**Before:** All endpoints depended on external H2S DB service at `http://localhost:11901/h2s/db/projects/*`
- ❌ No project ID 18 → All calls returned 404
- ❌ External service dependency for basic operations
- ❌ Can't test without external infrastructure

**After:** Projects stored in local PostgreSQL database
- ✅ Full CRUD operations via REST API
- ✅ No external dependencies
- ✅ Easy seeding and testing
- ✅ All endpoints work independently

---

## 📦 What Was Added

### 1. Database Model
**File:** [`app/db/projects/models.py`](app/db/projects/models.py)
- `ProjectModel` - SQLAlchemy model for project storage
- Stores: id, name, train_id, connection (JSON), db_metadata (JSON), timestamps

### 2. Local Projects Service
**File:** [`app/projects/services/local_projects.py`](app/projects/services/local_projects.py)
- `LocalProjects` class with static methods:
  - `get_project(db, project_id)` - Get by ID
  - `get_project_by_name(db, name)` - Get by name
  - `get_all_projects(db)` - List all
  - `create_project(...)` - Create new
  - `update_project(db, project)` - Update existing
  - `delete_project(db, project_id)` - Delete

### 3. Projects REST API
**File:** [`app/projects/services/projects_api.py`](app/projects/services/projects_api.py)
- **GET** `/h2s/db/projects` - List all projects
- **GET** `/h2s/db/projects/{project_id}` - Get project by ID
- **POST** `/h2s/db/projects` - Create new project
- **DELETE** `/h2s/db/projects/{project_id}` - Delete project

### 4. Database Migration
**File:** [`app/migrations/versions/create_projects_table.py`](app/migrations/versions/create_projects_table.py)
- Creates `projects` table with proper schema
- Indexes on `id` and `name`

### 5. Seed Script
**File:** [`seed_project.py`](seed_project.py)
- Creates test project in database
- Configurable via environment variables
- Safe to run multiple times (checks for existing)

### 6. Updated Endpoints
**File:** [`app/projects/services/data_upload_api.py`](app/projects/services/data_upload_api.py)
- Modified `get_project_by_id()` - Now uses LocalProjects + db session
- Modified `get_project_by_name()` - Now uses LocalProjects + db session
- Updated all endpoint calls to pass `db` parameter
- Upload endpoint now updates local database

---

## 🚀 Setup Instructions

### Step 1: Run Database Migrations

```bash
cd D:\h2sql\app

# If using Alembic (configured)
alembic upgrade head

# OR manually run the migration SQL
python -c "
from migrations.versions.create_projects_table import upgrade
import asyncio
from core.database import engine

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(upgrade)

asyncio.run(run())
"
```

### Step 2: Seed Test Project

```bash
cd D:\h2sql
python seed_project.py
```

**Output:**
```
============================================================
H2SQL Project Seed Script
============================================================

Database: postgresql+asyncpg://user:***@192.168.1.131:5433/database
Host: 192.168.1.131:5433
Database: database

✅ Created project successfully!
   ID: 1
   Name: test_project
   Connection: PostgreSQL @ 192.168.1.131:5433/database

You can now use this project_id=1 in your API calls.

============================================================
Seed complete!
============================================================
```

### Step 3: Start the Server

```bash
cd D:\h2sql\app
python main.py
```

The server now exposes:
- ✅ `/h2s/data-upload/*` - Data upload and query endpoints
- ✅ `/h2s/db/projects` - **NEW** Local project management API

---

## 🧪 Testing the Setup

### 1. Check Health
```bash
curl http://localhost:11901/health
# {"status":"healthy"}
```

### 2. List All Projects
```bash
curl http://localhost:11901/h2s/db/projects
# {"projects":[{"id":1,"name":"test_project",...}]}
```

### 3. Get Project by ID
```bash
curl http://localhost:11901/h2s/db/projects/1
# {"id":1,"name":"test_project","connection":{...},"db_metadata":[]}
```

### 4. Create a New Project
```bash
curl -X POST http://localhost:11901/h2s/db/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_project",
    "db_type": "postgres",
    "con_string": "localhost:5432/mydb",
    "database": "mydb",
    "username": "user",
    "password": "password"
  }'
```

### 5. Test Data Upload (Using Seeded Project)
```bash
# Use the project_id from step 2 (likely 1)
curl -X POST http://localhost:11901/h2s/data-upload/upload \
  -F "file=@test.csv" \
  -F "project_id=1"
```

### 6. Test Execute Query
```bash
curl -X POST http://localhost:11901/h2s/data-upload/executequey \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "question": "Show me all records"
  }'
```

---

## 📊 Database Schema

### projects Table
```sql
CREATE TABLE projects (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    train_id        VARCHAR(255),
    connection      TEXT NOT NULL,           -- JSON: {db_type, con_string, database, username, password}
    db_metadata     TEXT,                    -- JSON: [{name, description, columns: [...]}]
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_projects_id ON projects(id);
CREATE UNIQUE INDEX ix_projects_name ON projects(name);
```

---

## 🔄 Migration from External Service

If you have existing projects in the external H2S DB service, you can migrate them:

```python
import asyncio
import httpx
from core.database import get_db
from projects.services.local_projects import LocalProjects
from projects.models import Project

async def migrate_projects():
    """Fetch projects from external service and save locally"""

    async with httpx.AsyncClient() as client:
        # Fetch from external service
        response = await client.get(
            "http://localhost:11901/h2s/db/projects?size=-1",
            headers={"Authorization": "apikey"}
        )

        projects_data = response.json()["projects"]

        # Save to local database
        async for db in get_db():
            for project_dict in projects_data:
                project = Project(**project_dict)
                await LocalProjects.create_project(
                    db=db,
                    name=project.name,
                    connection=project.connection,
                    db_metadata=project.db_metadata,
                    train_id=project.train_id
                )
                print(f"Migrated: {project.name}")

asyncio.run(migrate_projects())
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Database has `projects` table
- [ ] Seed script created at least one project
- [ ] Server starts without errors
- [ ] `/health` endpoint returns 200
- [ ] `/h2s/db/projects` endpoint lists projects
- [ ] `/h2s/data-upload/executequey` with valid project_id doesn't return 404
- [ ] No errors in server logs about "Project not found"

---

## 🎯 Benefits

1. **No External Dependencies** - Fully self-contained
2. **Easy Testing** - Seed projects with one command
3. **Fast Development** - No network calls for project lookup
4. **Data Persistence** - Projects survive server restarts
5. **Standard REST API** - CRUD operations via HTTP
6. **Async Performance** - Fully async SQLAlchemy

---

## 📝 Configuration

Projects use these environment variables (from `.env`):

```bash
# PostgreSQL connection for project storage
APP_POSTGRES_DB_HOST=192.168.1.131
APP_POSTGRES_DB_PORT=5433
APP_POSTGRES_DB_NAME=database
APP_POSTGRES_DB_USER=user
APP_POSTGRES_DB_PASWD=password
```

Make sure these are set correctly before running the seed script or starting the server.

---

## 🆘 Troubleshooting

### "Project with ID X not found"
- **Cause:** No project exists with that ID
- **Solution:** Run `seed_project.py` or create via POST `/h2s/db/projects`

### "Table 'projects' doesn't exist"
- **Cause:** Migration not run
- **Solution:** Run the migration script (Step 1 above)

### "Connection refused to PostgreSQL"
- **Cause:** PostgreSQL not running or wrong credentials
- **Solution:** Verify `.env` settings and PostgreSQL service status

### Import errors for LocalProjects
- **Cause:** Python path issues
- **Solution:** Make sure you're running from the `app/` directory or `PYTHONPATH` is set

---

**Status:** ✅ Ready for use
**Last Updated:** 2025-10-25
