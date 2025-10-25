# H2SQL Project Migration Guide

## Overview
This guide explains how to extract the 8 key endpoints from the existing semantic-search project into a standalone H2SQL API.

## Target Endpoints
1. `/h2s/data-upload/publish`
2. `/h2s/data-upload/batch-publish`
3. `/h2s/data-upload/validate-connection/{data_source_id}`
4. `/h2s/data-upload/upload`
5. `/h2s/data-upload/recommendations/question`
6. `/h2s/data-upload/generatereport`
7. `/h2s/data-upload/executequey`
8. `/h2s/data-upload/graph`

## Required Files to Copy

### 1. Core Infrastructure
```
Source → Destination
app/core/database.py → app/core/database.py
app/core/settings.py → app/core/settings.py
```

### 2. Database Models
```
app/db/response_logs/models.py → app/db/response_logs/models.py
app/db/response_logs/__init__.py → app/db/response_logs/__init__.py
```

### 3. Projects Module
```
app/projects/models.py → app/projects/models.py
app/projects/connectors/db_connector.py → app/projects/connectors/db_connector.py
app/projects/connectors/oracle.py → app/projects/connectors/oracle.py
app/projects/connectors/postgres.py → app/projects/connectors/postgres.py
app/projects/services/db_metadata.py → app/projects/services/db_metadata.py
app/projects/services/data_upload_api.py → app/projects/services/data_upload_api.py
app/projects/services/projects.py → app/projects/services/projects.py
```

### 4. Supporting Files
```
app/prompts/prompts.py → app/prompts/prompts.py
app/prompts/prompts.json → app/prompts/prompts.json
```

## Dependencies to Remove

### External API Calls to Convert to Methods
The following external HTTP calls should be converted to internal method calls:

1. **Chart-Spec API** (`http://localhost:11901/h2s/chat/chart-spec`)
   - Location: `data_upload_api.py` lines 2035, 3065
   - Convert to: Internal chart specification logic

2. **LLM Metadata Assistant** (if external)
   - Location: `data_upload_api.py` around line 950+
   - Keep as method call

3. **Projects Service**
   - Already internal, keep as is

## Key Refactoring Steps

### Step 1: Update Imports
Replace:
```python
from app.core.database import get_db
from app.projects.connectors.oracle import OracleConnector
```

With:
```python
from core.database import get_db
from projects.connectors.oracle import OracleConnector
```

### Step 2: Remove chart-spec HTTP Call
In `data_upload_api.py`, replace:
```python
async def call_chart_spec_endpoint(question: str, table_data: Dict[str, Any]) -> Dict[str, Any]:
    url = "http://localhost:11901/h2s/chat/chart-spec"
    # ... HTTP call ...
```

With internal logic:
```python
def generate_chart_spec(question: str, table_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate chart specification locally"""
    columns = table_data.get("columns", [])

    # Separate numeric and non-numeric columns
    numeric_cols = []
    non_numeric_cols = []

    if table_data.get("rows"):
        first_row = table_data["rows"][0]
        for i, col in enumerate(columns):
            try:
                float(first_row[i])
                numeric_cols.append(col)
            except (ValueError, TypeError):
                non_numeric_cols.append(col)

    return {
        "chartType": "bar",
        "xFields": non_numeric_cols[:2] if non_numeric_cols else [columns[0]],
        "yFields": numeric_cols if numeric_cols else [columns[-1]],
        "xLabels": non_numeric_cols[:2] if non_numeric_cols else [columns[0]],
        "yLabels": numeric_cols if numeric_cols else [columns[-1]],
        "chartTypes": ["bar", "line", "area", "pie"],
        "title": f"Chart for {question}"
    }
```

### Step 3: Simplify LLM Calls
For functions like `generate_sql_from_question`, `generate_human_readable_answer`:
- Keep the LLM integration if you have access to LLM
- Or mock with simple logic for testing

### Step 4: Update ConnectionProfile
Ensure `ConnectionProfile` model includes:
```python
class ConnectionProfile(BaseModel):
    db_type: str  # "oracle" | "postgres" | "mysql" | "sqlserver"
    username: str
    password: str
    host: str
    port: int
    database: str | None = None
    con_string: str | None = None
```

## Environment Configuration

Create `.env` file:
```env
# PostgreSQL (for response_logs storage)
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=database
POSTGRES_HOST=192.168.1.131
POSTGRES_PORT=5433

# LLM Configuration (if using external LLM)
LLM_API_KEY=your_api_key
LLM_BASE_URL=http://192.168.1.6:3035/v1
LLM_MODEL=Llama-4-Scout-17B-16E-Instruct
```

## Installation Steps

### 1. Copy Files
```bash
# Copy all required files from source to D:\h2sql\app\
```

### 2. Install Dependencies
```bash
cd D:\h2sql
pip install -r requirements.txt
```

### 3. Setup Database
```bash
cd app
# Create tables
python -c "from core.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

Or use Alembic:
```bash
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Run Application
```bash
cd D:\h2sql\app
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 11901 --reload
```

## Testing Endpoints

### Test /upload
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/upload" \
  -F "file=@test.csv"
```

### Test /executequey
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/executequey" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 17,
    "question": "Get all customers from California"
  }'
```

### Test /graph
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/graph" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 17,
    "response_id": "resp_20251023_123456_abc123"
  }'
```

## Troubleshooting

### Issue: Import errors
**Solution**: Ensure all `__init__.py` files are present in each directory

### Issue: Database connection fails
**Solution**: Check `.env` file and ensure PostgreSQL is running

### Issue: Missing LLM responses
**Solution**: Verify LLM service is accessible or implement fallback logic

## Additional Notes

- The project uses **async/await** patterns throughout
- Database operations use **SQLAlchemy 2.0** async
- File uploads support **CSV** and **Excel** formats
- The response_logs table stores all query executions
- Chart generation now happens locally (no external API needed)

## Next Steps

1. Copy all required files maintaining directory structure
2. Update all import statements
3. Replace HTTP calls with local methods
4. Test each endpoint individually
5. Deploy to production

For questions or issues, refer to the original codebase at:
`D:\project\03102025_v1\working-code\sematic-searach\app\`
