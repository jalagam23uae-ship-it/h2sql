# H2SQL Quick Start Guide

## Project Structure Created
```
D:\h2sql\
├── app/
│   ├── main.py                    # FastAPI application
│   ├── core/
│   │   ├── database.py           # Database configuration
│   │   └── settings.py           # App settings
│   ├── db/
│   │   └── response_logs/        # Response logging models
│   ├── projects/
│   │   ├── models.py             # Data models
│   │   ├── connectors/           # Database connectors
│   │   └── services/             # API services
│   └── prompts/                  # LLM prompts
├── requirements.txt
├── .env
├── run.bat
└── README.md
```

## Installation Steps

### 1. Install Dependencies
```bash
cd D:\h2sql
pip install -r requirements.txt
```

### 2. Configure Environment
Edit `.env` file with your database credentials:
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=database
POSTGRES_HOST=192.168.1.131
POSTGRES_PORT=5433
```

### 3. Run the Application

**Option A: Using the batch script**
```bash
run.bat
```

**Option B: Using Python directly**
```bash
cd app
python main.py
```

**Option C: Using uvicorn**
```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 11901 --reload
```

## Access the API

- **API Documentation**: http://localhost:11901/docs
- **Health Check**: http://localhost:11901/health
- **Root**: http://localhost:11901/

## Available Endpoints

1. POST `/h2s/data-upload/publish` - Publish data to database
2. POST `/h2s/data-upload/batch-publish` - Batch publish multiple files
3. POST `/h2s/data-upload/validate-connection/{id}` - Validate connection
4. POST `/h2s/data-upload/upload` - Upload CSV/Excel files
5. POST `/h2s/data-upload/recommendations/question` - Get recommendations
6. POST `/h2s/data-upload/generatereport` - Generate HTML reports
7. POST `/h2s/data-upload/executequey` - Execute natural language queries
8. POST `/h2s/data-upload/graph` - Generate graph from cached data

## Testing

### Test File Upload
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/upload" \
  -F "file=@test.csv"
```

### Test Query Execution
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/executequey" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 17, "question": "Get all customers"}'
```

### Test Graph Generation
```bash
curl -X POST "http://localhost:11901/h2s/data-upload/graph" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 17, "response_id": "resp_123"}'
```

## Troubleshooting

### ImportError
- Ensure you're in the `app` directory when running
- Check all `__init__.py` files exist

### Database Connection Error
- Verify `.env` file credentials
- Ensure PostgreSQL is running
- Test connection manually

### Module Not Found
- Install missing dependencies: `pip install -r requirements.txt`
- Check Python version (3.10+ required)

## Next Steps

1. **Setup Database Tables**
   - The `response_logs` table needs to be created
   - Use Alembic or create manually

2. **Configure LLM** (Optional)
   - Set LLM API keys in `.env`
   - Update prompts in `app/prompts/prompts.json`

3. **Test All Endpoints**
   - Use the Swagger UI at http://localhost:11901/docs
   - Test each endpoint with sample data

## Support

For issues, check:
- `README.md` for detailed documentation
- `MIGRATION_GUIDE.md` for migration details
- Logs in console output

Happy coding!
