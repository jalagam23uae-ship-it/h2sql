# H2SQL API

A standalone FastAPI application for data upload, SQL query execution, and visualization generation.

## Features

- **Data Upload**: Upload CSV/Excel files and create database tables automatically
- **Query Execution**: Execute natural language queries converted to SQL
- **Response Logging**: Automatic logging of all query executions
- **Graph Generation**: Generate chart configurations from cached query results
- **Multi-Database Support**: Oracle, PostgreSQL, MySQL, SQL Server
- **Report Generation**: Create HTML reports with interactive charts

## Project Structure

```
D:\h2sql\
├── app/
│   ├── main.py                          # FastAPI application entry point
│   ├── core/
│   │   ├── database.py                  # Database configuration
│   │   └── settings.py                  # Application settings
│   ├── db/
│   │   └── response_logs/
│   │       ├── models.py                # Response logs model
│   │       └── __init__.py
│   ├── projects/
│   │   ├── models.py                    # Project models
│   │   ├── connectors/                  # Database connectors
│   │   │   ├── db_connector.py
│   │   │   ├── oracle.py
│   │   │   └── postgres.py
│   │   └── services/
│   │       ├── data_upload_api.py       # Main API endpoints
│   │       ├── db_metadata.py
│   │       └── projects.py
│   └── prompts/
│       ├── prompts.py
│       └── prompts.json
├── requirements.txt
├── .env.example
├── MIGRATION_GUIDE.md
└── README.md
```

## Available Endpoints

### 1. `/h2s/data-upload/publish`
Create a table and insert data into a data source.

**Method**: POST
**Request**:
```json
{
  "dataSourceId": "1",
  "tableStructure": {
    "tableName": "customers",
    "columns": [
      {"name": "id", "dataType": "INTEGER"},
      {"name": "name", "dataType": "VARCHAR(100)"}
    ]
  },
  "data": [
    ["1", "John Doe"],
    ["2", "Jane Smith"]
  ]
}
```

### 2. `/h2s/data-upload/batch-publish`
Create multiple tables and insert data for multiple files.

**Method**: POST

### 3. `/h2s/data-upload/validate-connection/{data_source_id}`
Validate connection to a data source.

**Method**: POST
**Path Parameter**: `data_source_id` - ID of the data source

### 4. `/h2s/data-upload/upload`
Upload CSV/Excel file and automatically create table with data.

**Method**: POST
**Content-Type**: multipart/form-data
**Request**:
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/upload" \
  -F "file=@customers.csv"
```

**Response**:
```json
{
  "success": true,
  "message": "File uploaded successfully",
  "projectId": 17,
  "tableName": "customers_a1b2c3d4",
  "rowsInserted": 1500
}
```

### 5. `/h2s/data-upload/recommendations/question`
Get recommendation questions for a project.

**Method**: POST
**Request**:
```json
{
  "projectId": 17
}
```

### 6. `/h2s/data-upload/generatereport`
Generate HTML report with charts for recommended questions.

**Method**: POST
**Request**:
```json
{
  "projectId": 17,
  "recomended_questions": [
    {
      "recomended_qstn_id": "q1",
      "sql_query": "SELECT city, COUNT(*) FROM customers GROUP BY city",
      "question": "Customer distribution by city"
    }
  ]
}
```

**Response**: HTML page with interactive charts

### 7. `/h2s/data-upload/executequey`
Execute natural language query with comprehensive analytics.

**Method**: POST
**Request**:
```json
{
  "project_id": 17,
  "question": "Which roles have 'Approve Proposal' in Operations column and 'Level 2' in Level column?"
}
```

**Response**:
```json
{
  "response_id": "resp_20251023_094530_abc123",
  "question": "Which roles...",
  "llm_generated_sql": "SELECT role FROM table WHERE...",
  "query_filter_data": {...},
  "db_result": [...],
  "statistics": {...},
  "human_readable_answer": "Based on the data...",
  "quotation": "2 roles match the criteria",
  "metadata": {...}
}
```

### 8. `/h2s/data-upload/graph`
Generate graph data from cached response.

**Method**: POST
**Request**:
```json
{
  "project_id": 17,
  "response_id": "resp_20251023_094530_abc123"
}
```

**Response**:
```json
{
  "id": "f3a8b2c1",
  "title": "Chart for customer count by city and state",
  "type": "bar",
  "data": [
    {"CITY": "Los Angeles", "STATE": "California", "COUNT": 58},
    {"CITY": "Dubai", "STATE": "Ohio", "COUNT": 2}
  ],
  "config": {
    "xAxis": ["CITY", "STATE"],
    "yAxis": ["COUNT"],
    "colors": ["#3b82f6", "#ef4444"]
  },
  "size": "large",
  "position": {"row": 0, "col": 0}
}
```

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL database
- Oracle Instant Client (if using Oracle databases)

### Setup Steps

1. **Clone/Copy Files**
   ```bash
   # Copy all files from source project to D:\h2sql\
   ```

2. **Create Virtual Environment**
   ```bash
   cd D:\h2sql
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   copy .env.example .env
   # Edit .env with your database credentials
   ```

5. **Setup Database Tables**
   ```bash
   cd app
   python -c "from core.database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

6. **Run Application**
   ```bash
   cd app
   python main.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 11901 --reload
   ```

## Configuration

### Environment Variables

Edit `.env` file:

```env
# PostgreSQL (for response_logs)
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=database
POSTGRES_HOST=192.168.1.131
POSTGRES_PORT=5433

# LLM (Optional)
LLM_API_KEY=your_key
LLM_BASE_URL=http://your-llm-server:3035/v1
LLM_MODEL=your-model-name
```

### Database Connection

The application connects to PostgreSQL to store:
- Query execution logs (`response_logs` table)
- Project configurations

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:11901/docs
- **ReDoc**: http://localhost:11901/redoc
- **Health Check**: http://localhost:11901/health

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
flake8 app/
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Your message"
alembic upgrade head
```

## Troubleshooting

### Issue: ImportError
**Solution**: Ensure you're in the correct directory and virtual environment is activated

### Issue: Database Connection Failed
**Solution**:
- Check `.env` file has correct credentials
- Ensure PostgreSQL is running
- Test connection: `psql -h 192.168.1.131 -p 5433 -U user -d database`

### Issue: Oracle Client Error
**Solution**:
- Install Oracle Instant Client
- Set path in `projects/connectors/oracle.py`
- Windows: `C:\oracle\instantclient_23_9`

### Issue: File Upload Fails
**Solution**:
- Check file format (CSV or Excel)
- Ensure file is not empty
- Check column names for reserved keywords

## Migration from Original Project

See `MIGRATION_GUIDE.md` for detailed instructions on migrating from the original semantic-search project.

## Key Differences from Original

1. **Standalone**: No dependencies on other services
2. **Simplified**: Removed unnecessary features
3. **Local Chart Generation**: No external chart-spec API calls
4. **Streamlined**: Focus on 8 core endpoints only

## License

Proprietary

## Support

For issues or questions, contact the development team.

## Version History

- **1.0.0** (2025-01-23): Initial standalone release
  - 8 core endpoints
  - PostgreSQL logging
  - Multi-database support
  - Graph generation
