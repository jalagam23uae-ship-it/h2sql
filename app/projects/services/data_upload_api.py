"""
Data Upload API
Handles CSV/Excel file uploads, table creation, and data insertion into configured data sources.
"""
import unicodedata
import re
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from projects.connectors.oracle import OracleConnector, ConnectionProfile
from projects.services.db_metadata import get_connector
import logging
import asyncio
import pandas as pd
import io
import json
import uuid
import httpx
import time
from projects.models import TableSchema, TableColumn
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/h2s/data-upload", tags=["data-upload"])

# Get base URL from environment variable
APP_SERVER_URL = os.getenv("APP_SERVER_URL", "http://localhost:11901")
CHART_SPEC_URL = f"{APP_SERVER_URL}/h2s/chat/chart-spec"


class ColumnDefinition(BaseModel):
    """Column definition for table creation"""
    name: str
    dataType: str
    description: Optional[str] = None


class TableStructure(BaseModel):
    """Table structure with columns"""
    tableName: str
    columns: List[ColumnDefinition]
    description: Optional[str] = None


class PublishDataRequest(BaseModel):
    """Request to publish data to a data source"""
    dataSourceId: str
    tableStructure: TableStructure
    data: List[List[str]]  # 2D array: rows × columns


class PublishDataResponse(BaseModel):
    """Response after publishing data"""
    success: bool
    message: str
    rowsInserted: int
    tableName: str


class FileUpload(BaseModel):
    """Individual file upload data"""
    fileName: str
    tableStructure: TableStructure
    data: List[List[str]]


class BatchPublishRequest(BaseModel):
    """Request to publish multiple files"""
    dataSourceId: str
    files: List[FileUpload]


class FileUploadResult(BaseModel):
    """Result for a single file upload"""
    fileName: str
    success: bool
    message: str
    rowsInserted: int
    tableName: str
    error: Optional[str] = None


class BatchPublishResponse(BaseModel):
    """Response after batch publishing"""
    success: bool
    results: List[FileUploadResult]
    totalFiles: int
    successfulFiles: int
    failedFiles: int


def generate_create_table_sql(structure: TableStructure, db_type: str = "oracle") -> str:
    """
    Generate CREATE TABLE SQL statement from table structure.

    Args:
        structure: Table structure with columns
        db_type: Database type ("oracle" or "postgres")

    Returns:
        SQL CREATE TABLE statement
    """
    # Normalize db_type
    db_type_lower = db_type.lower()

    columns = []
    for col in structure.columns:
        # Map data types to database-specific SQL types
        data_type = map_data_type_to_db(col.dataType, db_type)

        # Quote column names to handle reserved keywords
        if db_type_lower in ("postgres", "postgresql"):
            # PostgreSQL uses double quotes for identifiers
            quoted_col_name = f'"{col.name}"'
        else:
            # Oracle uses double quotes for case-sensitive/reserved identifiers
            quoted_col_name = f'"{col.name}"'

        columns.append(f"  {quoted_col_name} {data_type}")

    columns_sql = ",\n".join(columns)

    # Quote table name as well
    if db_type_lower in ("postgres", "postgresql"):
        quoted_table_name = f'"{structure.tableName}"'
    else:
        quoted_table_name = f'"{structure.tableName}"'

    sql = f"CREATE TABLE {quoted_table_name} (\n{columns_sql}\n)"

    return sql


def map_data_type_to_db(data_type: str, db_type: str = "oracle") -> str:
    """
    Map data types to database-specific SQL types.

    Args:
        data_type: Data type (e.g., "VARCHAR(100)", "INTEGER")
        db_type: Database type ("oracle" or "postgres")

    Returns:
        Database-compatible SQL data type
    """
    # Normalize db_type
    db_type_lower = db_type.lower()

    # Get base type (e.g., "INTEGER" from "INTEGER(10)")
    base_type = data_type.split("(")[0].upper()

    if db_type_lower in ("postgres", "postgresql"):
        # PostgreSQL type mappings
        postgres_mappings = {
            "NUMBER": "INTEGER",
            "VARCHAR2": "VARCHAR",
            "CLOB": "TEXT",
        }

        if base_type in postgres_mappings:
            # Extract precision if present
            if "(" in data_type:
                precision = data_type.split("(")[1].split(")")[0]
                if postgres_mappings[base_type] in ("VARCHAR", "INTEGER"):
                    return f"{postgres_mappings[base_type]}({precision})" if postgres_mappings[base_type] == "VARCHAR" else "INTEGER"
            return postgres_mappings[base_type]

        # Already PostgreSQL compatible
        return data_type
    else:
        # Oracle type mappings
        oracle_mappings = {
            "INTEGER": "NUMBER(10)",
            "SMALLINT": "NUMBER(5)",
            "BIGINT": "NUMBER(19)",
            "DECIMAL": "NUMBER",
            "BOOLEAN": "NUMBER(1)",
            "TEXT": "CLOB",
            "VARCHAR": "VARCHAR2",
        }

        if base_type in oracle_mappings:
            # Extract precision if present
            if "(" in data_type and base_type == "VARCHAR":
                precision = data_type.split("(")[1].split(")")[0]
                return f"VARCHAR2({precision})"
            return oracle_mappings[base_type]

        # Already Oracle compatible
        return data_type


def generate_insert_sql(table_name: str, columns: List[str], row_data: List[str]) -> str:
    """
    Generate INSERT SQL statement for a single row.

    Args:
        table_name: Name of the table
        columns: List of column names
        row_data: List of values for the row

    Returns:
        SQL INSERT statement
    """
    # Quote column names to handle reserved keywords
    quoted_columns = [f'"{col}"' for col in columns]
    column_list = ", ".join(quoted_columns)

    # Quote table name to handle reserved keywords
    quoted_table_name = f'"{table_name}"'

    # Escape and format values
    values = []
    for val in row_data:
        if val is None or val == "":
            values.append("NULL")
        elif val.lower() in ["true", "false"]:
            # Convert boolean to 1/0 for Oracle
            values.append("1" if val.lower() == "true" else "0")
        else:
            # Escape single quotes and wrap in quotes
            escaped_val = val.replace("'", "''")
            values.append(f"'{escaped_val}'")

    values_list = ", ".join(values)
    sql = f"INSERT INTO {quoted_table_name} ({column_list}) VALUES ({values_list})"

    return sql


async def get_data_source_connection(data_source_id: str, db: AsyncSession) -> ConnectionProfile:
    """
    Retrieve data source connection details from database.

    Args:
        data_source_id: ID of the data source
        db: Database session (not used, kept for compatibility)

    Returns:
        ConnectionProfile for the data source

    Raises:
        HTTPException: If data source not found
    """
    # Import the Projects service to get project details
    from projects.services.projects import Projects
    from projects.models import Project

    projects_service = Projects()

    try:
        # Get project by ID
        project_data = await projects_service.get_project(int(data_source_id))

        if not project_data:
            raise HTTPException(status_code=404, detail=f"Data source {data_source_id} not found")

        # Convert to Project object which handles connection JSON parsing
        project = Project(**project_data)

        if not project.connection:
            raise HTTPException(status_code=400, detail=f"Data source {data_source_id} has no connection configured")

        return project.connection

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving data source {data_source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving data source: {str(e)}")





@router.post("/publish", response_model=PublishDataResponse)
async def publish_data(
    request: PublishDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create table and insert data into a data source.

    This endpoint:
    1. Connects to the specified data source
    2. Creates the table with the given structure
    3. Inserts all data rows
    4. Returns the number of rows inserted

    Args:
        request: PublishDataRequest with dataSourceId, tableStructure, and data
        db: Database session

    Returns:
        PublishDataResponse with success status and rows inserted

    Raises:
        HTTPException: If connection fails, table creation fails, or data insertion fails
    """
    try:
        logger.info(f"Publishing data to data source {request.dataSourceId}")
        logger.info(f"Table: {request.tableStructure.tableName}, Rows: {len(request.data)}")

        # Get data source connection
        connection_profile = await get_data_source_connection(request.dataSourceId, db)

        # Get database type and select appropriate connector
        db_type = connection_profile.db_type
        connector = get_connector(db_type)

        # Generate CREATE TABLE SQL (database-aware)
        create_table_sql = generate_create_table_sql(request.tableStructure, db_type)
        logger.info(f"CREATE TABLE SQL:\n{create_table_sql}")

        # Execute CREATE TABLE
        try:
            connection = connector.get_connection(connection_profile)
            cursor = connection.cursor()

            # Drop table if exists (optional - remove if you want to preserve existing tables)
            try:
                cursor.execute(f'DROP TABLE "{request.tableStructure.tableName}"')
                logger.info(f"Dropped existing table {request.tableStructure.tableName}")
            except Exception as e:
                logger.debug(f"Table doesn't exist or couldn't be dropped: {e}")

            # Create table
            cursor.execute(create_table_sql)
            connection.commit()
            logger.info(f"Successfully created table {request.tableStructure.tableName}")

        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")

        # Insert data rows
        rows_inserted = 0
        column_names = [col.name for col in request.tableStructure.columns]

        # Skip header row if first row matches column names
        data_rows = request.data
        if len(data_rows) > 0 and data_rows[0] == column_names:
            data_rows = data_rows[1:]
            logger.info("Skipped header row in data")

        try:
            for row in data_rows:
                insert_sql = generate_insert_sql(
                    request.tableStructure.tableName,
                    column_names,
                    row
                )
                cursor.execute(insert_sql)
                rows_inserted += 1

                # Commit every 100 rows for performance
                if rows_inserted % 100 == 0:
                    connection.commit()
                    logger.info(f"Inserted {rows_inserted} rows...")

            # Final commit
            connection.commit()
            logger.info(f"Successfully inserted {rows_inserted} rows into {request.tableStructure.tableName}")

        except Exception as e:
            connection.rollback()
            logger.error(f"Failed to insert data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to insert data: {str(e)}")

        finally:
            cursor.close()
            connection.close()

        return PublishDataResponse(
            success=True,
            message=f"Successfully created table and inserted {rows_inserted} rows",
            rowsInserted=rows_inserted,
            tableName=request.tableStructure.tableName
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error publishing data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/batch-publish", response_model=BatchPublishResponse)
async def batch_publish_data(
    request: BatchPublishRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create tables and insert data for multiple files.

    This endpoint processes multiple files sequentially and returns
    individual results for each file.

    Args:
        request: BatchPublishRequest with dataSourceId and list of files
        db: Database session

    Returns:
        BatchPublishResponse with results for each file
    """
    try:
        logger.info(f"Batch publishing {len(request.files)} files to data source {request.dataSourceId}")

        # Get data source connection once
        connection_profile = await get_data_source_connection(request.dataSourceId, db)

        # Get database type and select appropriate connector
        db_type = connection_profile.db_type
        connector = get_connector(db_type)

        results: List[FileUploadResult] = []
        successful_files = 0
        failed_files = 0

        # Process each file
        for file_upload in request.files:
            try:
                logger.info(f"Processing file: {file_upload.fileName}")

                # Generate CREATE TABLE SQL (database-aware)
                create_table_sql = generate_create_table_sql(file_upload.tableStructure, db_type)

                # Execute CREATE TABLE and INSERT
                connection = connector.get_connection(connection_profile)
                cursor = connection.cursor()

                try:
                    # Drop table if exists
                    try:
                        cursor.execute(f'DROP TABLE "{file_upload.tableStructure.tableName}"')
                        logger.info(f"Dropped existing table {file_upload.tableStructure.tableName}")
                    except Exception:
                        pass

                    # Create table
                    cursor.execute(create_table_sql)
                    connection.commit()
                    logger.info(f"Created table {file_upload.tableStructure.tableName}")

                    # Insert data
                    rows_inserted = 0
                    column_names = [col.name for col in file_upload.tableStructure.columns]

                    # Skip header row if present
                    data_rows = file_upload.data
                    if len(data_rows) > 0 and data_rows[0] == column_names:
                        data_rows = data_rows[1:]

                    for row in data_rows:
                        insert_sql = generate_insert_sql(
                            file_upload.tableStructure.tableName,
                            column_names,
                            row
                        )
                        cursor.execute(insert_sql)
                        rows_inserted += 1

                        # Commit every 100 rows
                        if rows_inserted % 100 == 0:
                            connection.commit()

                    # Final commit
                    connection.commit()
                    logger.info(f"Inserted {rows_inserted} rows into {file_upload.tableStructure.tableName}")

                    results.append(FileUploadResult(
                        fileName=file_upload.fileName,
                        success=True,
                        message=f"Successfully inserted {rows_inserted} rows",
                        rowsInserted=rows_inserted,
                        tableName=file_upload.tableStructure.tableName
                    ))
                    successful_files += 1

                except Exception as e:
                    connection.rollback()
                    error_msg = f"Failed to process table: {str(e)}"
                    logger.error(f"Error processing {file_upload.fileName}: {error_msg}")
                    results.append(FileUploadResult(
                        fileName=file_upload.fileName,
                        success=False,
                        message="Failed to create table or insert data",
                        rowsInserted=0,
                        tableName=file_upload.tableStructure.tableName,
                        error=error_msg
                    ))
                    failed_files += 1

                finally:
                    cursor.close()
                    connection.close()

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Unexpected error processing {file_upload.fileName}: {error_msg}")
                results.append(FileUploadResult(
                    fileName=file_upload.fileName,
                    success=False,
                    message="Unexpected error",
                    rowsInserted=0,
                    tableName=file_upload.tableStructure.tableName,
                    error=error_msg
                ))
                failed_files += 1

        return BatchPublishResponse(
            success=successful_files > 0,
            results=results,
            totalFiles=len(request.files),
            successfulFiles=successful_files,
            failedFiles=failed_files
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch publish: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch publish failed: {str(e)}")


@router.get("/validate-connection/{data_source_id}")
async def validate_connection(
    data_source_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate connection to a data source.

    Args:
        data_source_id: ID of the data source to validate
        db: Database session

    Returns:
        Connection status
    """
    try:
        connection_profile = await get_data_source_connection(data_source_id, db)
        connector = OracleConnector()

        # Try to get connection
        connection = connector.get_connection(connection_profile)
        connection.close()

        return {
            "success": True,
            "message": "Connection successful"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


# ================== NEW /upload ENDPOINT ==================

class UploadResponse(BaseModel):
    """Response from upload endpoint"""
    success: bool
    message: str
    projectId: int
    tableName: str
    rowsInserted: int


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Clean and validate DataFrame before database insertion.

    Performs comprehensive data cleaning:
    1. Remove duplicate rows
    2. Handle missing values
    3. Standardize formatting (dates, text, spacing)
    4. Detect and handle outliers
    5. Validate data types
    6. Standardize categorical values
    7. Remove unnecessary columns
    8. Handle special characters

    Args:
        df: Raw pandas DataFrame

    Returns:
        Tuple of (cleaned DataFrame, cleaning report dict)
    """
    cleaning_report = {
        "original_rows": len(df),
        "original_columns": len(df.columns),
        "duplicates_removed": 0,
        "missing_values_found": 0,
        "columns_cleaned": [],
        "outliers_detected": 0,
        "columns_removed": [],
        "warnings": []
    }

    logger.info(f"Starting data cleaning. Original shape: {df.shape}")

    # Step 1: Remove completely empty rows and columns
    initial_rows = len(df)
    df = df.dropna(how='all')  # Remove rows where all values are NaN
    df = df.dropna(axis=1, how='all')  # Remove columns where all values are NaN

    empty_rows_removed = initial_rows - len(df)
    if empty_rows_removed > 0:
        logger.info(f"Removed {empty_rows_removed} completely empty rows")
        cleaning_report["warnings"].append(f"Removed {empty_rows_removed} empty rows")

    # Step 2: Remove duplicate rows
    initial_rows = len(df)
    df = df.drop_duplicates()
    duplicates_removed = initial_rows - len(df)
    cleaning_report["duplicates_removed"] = duplicates_removed

    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate rows")

    # Step 3: Clean column names
    # Remove special characters, replace spaces with underscores
    original_columns = df.columns.tolist()
    df.columns = [
        ''.join(c if c.isalnum() else '_' for c in col).strip('_').upper()
        for col in df.columns
    ]

    # Ensure column names start with a letter
    df.columns = [
        f"COL_{col}" if col[0].isdigit() else col
        for col in df.columns
    ]

    logger.info(f"Standardized column names: {list(df.columns)}")

    # Step 4: Handle missing values and clean data per column
    for col in df.columns:
        col_report = {"name": col, "actions": []}

        # Count missing values
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            cleaning_report["missing_values_found"] += missing_count
            col_report["actions"].append(f"Found {missing_count} missing values")

        # For object/string columns: clean and standardize
        if df[col].dtype == 'object':
            # Remove leading/trailing whitespace
            df[col] = df[col].astype(str).str.strip()

            # Replace common null representations with actual NaN
            null_values = ['null', 'NULL', 'Null', 'none', 'None', 'NONE', 'N/A', 'n/a', 'NA', 'nan', '']
            df[col] = df[col].replace(null_values, pd.NA)

            # Try to detect and parse dates
            try:
                # Sample first 10 non-null values
                sample = df[col].dropna().head(10)
                if len(sample) > 0:
                    parsed_dates = pd.to_datetime(sample, errors='coerce')
                    # If >80% parse as dates, convert entire column
                    if parsed_dates.notna().sum() / len(sample) > 0.8:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        col_report["actions"].append("Converted to datetime")
            except:
                pass

            # Try to detect and parse numbers (with formatting)
            if df[col].dtype == 'object':  # Still object after date check
                try:
                    sample = df[col].dropna().head(10)
                    if len(sample) > 0:
                        # Clean number formatting
                        cleaned = sample.str.replace(',', '').str.replace('$', '').str.replace('%', '').str.strip()
                        numeric_values = pd.to_numeric(cleaned, errors='coerce')
                        # If >80% parse as numbers, convert entire column
                        if numeric_values.notna().sum() / len(sample) > 0.8:
                            df[col] = df[col].str.replace(',', '').str.replace('$', '').str.replace('%', '').str.strip()
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            col_report["actions"].append("Converted to numeric")
                except:
                    pass

            # Standardize text case for categorical columns (if still object)
            if df[col].dtype == 'object':
                unique_count = df[col].nunique()
                # If low cardinality (<20% unique values), standardize case
                if unique_count < len(df) * 0.2 and unique_count < 100:
                    # Standardize to title case
                    df[col] = df[col].str.title()
                    col_report["actions"].append("Standardized to title case")

        # For numeric columns: detect outliers
        elif pd.api.types.is_numeric_dtype(df[col]):
            non_null = df[col].dropna()
            if len(non_null) > 0:
                Q1 = non_null.quantile(0.25)
                Q3 = non_null.quantile(0.75)
                IQR = Q3 - Q1

                # Detect outliers (beyond 1.5*IQR)
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = ((non_null < lower_bound) | (non_null > upper_bound)).sum()

                if outliers > 0:
                    cleaning_report["outliers_detected"] += outliers
                    col_report["actions"].append(f"Detected {outliers} potential outliers (kept)")
                    # Note: We detect but don't remove outliers - let user decide

        if col_report["actions"]:
            cleaning_report["columns_cleaned"].append(col_report)

    # Step 5: Fill remaining missing values with appropriate defaults
    for col in df.columns:
        if df[col].isna().any():
            if pd.api.types.is_numeric_dtype(df[col]):
                # For numeric: fill with 0 or mean (configurable)
                df[col] = df[col].fillna(0)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # For dates: leave as NULL (database will handle)
                pass
            else:
                # For strings: fill with empty string
                df[col] = df[col].fillna('')

    cleaning_report["final_rows"] = len(df)
    cleaning_report["final_columns"] = len(df.columns)

    logger.info(f"Data cleaning complete. Final shape: {df.shape}")
    logger.info(f"Cleaning summary: {duplicates_removed} duplicates removed, "
                f"{cleaning_report['missing_values_found']} missing values handled, "
                f"{cleaning_report['outliers_detected']} outliers detected")

    return df, cleaning_report


import pandas as pd

def infer_data_type(series_or_df, db_type: str = "oracle") -> str:
    """
    Infer SQL data type from pandas Series or DataFrame (auto-fallback for Excel/CSV headers).
    Handles:
        - Arabic/non-ASCII column names
        - Multi-row headers
        - Wrong inputs (DataFrame instead of Series)
        - Database-aware type inference (Oracle/Postgres)
    """

    # ✅ If a DataFrame was passed instead of a Series
    if isinstance(series_or_df, pd.DataFrame):
        if series_or_df.empty or series_or_df.shape[1] == 0:
            # Empty DF fallback
            return "VARCHAR2(255)" if db_type.lower() == "oracle" else "VARCHAR(255)"
        series = series_or_df.iloc[:, 0]
    else:
        series = series_or_df

    # ✅ Drop nulls for inference
    non_null_series = series.dropna()

    if len(non_null_series) == 0:
        # All nulls — fallback to string
        return "VARCHAR2(255)" if db_type.lower() == "oracle" else "VARCHAR(255)"

    dtype = series.dtype

    # ✅ Boolean detection
    if pd.api.types.is_bool_dtype(dtype):
        return "NUMBER(1)" if db_type.lower() == "oracle" else "BOOLEAN"

    # ✅ Integer detection
    elif pd.api.types.is_integer_dtype(dtype):
        min_val = non_null_series.min()
        max_val = non_null_series.max()

        if db_type.lower() in ("postgres", "postgresql"):
            if min_val >= -32768 and max_val <= 32767:
                return "SMALLINT"
            elif min_val >= -2147483648 and max_val <= 2147483647:
                return "INTEGER"
            else:
                return "BIGINT"
        else:
            max_digits = max(len(str(abs(int(min_val)))), len(str(abs(int(max_val)))))
            return f"NUMBER({max_digits})"

    # ✅ Float detection
    elif pd.api.types.is_float_dtype(dtype):
        if db_type.lower() in ("postgres", "postgresql"):
            has_decimals = (non_null_series % 1 != 0).any()
            return "NUMERIC(15,2)" if has_decimals else "DOUBLE PRECISION"
        else:
            return "NUMBER"

    # ✅ Date/time detection
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATE" if db_type.lower() == "oracle" else "TIMESTAMP"

    # ✅ Try to detect date or numeric in object/string
    else:
        try:
            sample = non_null_series.head(10)
            with pd.option_context("mode.chained_assignment", None):
                parsed_dates = pd.to_datetime(sample, errors="coerce", format="%d/%m/%Y")
            if parsed_dates.notna().sum() / len(sample) > 0.8:
                return "DATE" if db_type.lower() == "oracle" else "TIMESTAMP"
        except Exception:
            pass

        try:
            sample = non_null_series.head(10).astype(str)
            cleaned = sample.str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.strip()
            numeric_values = pd.to_numeric(cleaned, errors="coerce")
            if numeric_values.notna().sum() / len(sample) > 0.8:
                return "NUMBER" if db_type.lower() == "oracle" else "NUMERIC(15,2)"
        except Exception:
            pass

        # ✅ String fallback with size detection
        max_length = non_null_series.astype(str).str.len().max()
        if pd.isna(max_length) or max_length == 0:
            max_length = 100
        else:
            max_length = int(max_length * 1.2)  # buffer

        if db_type.lower() in ("postgres", "postgresql"):
            if max_length > 1000:
                return "TEXT"
            else:
                return f"VARCHAR({max(50, min(1000, max_length))})"
        else:  # Oracle
            if max_length > 4000:
                return "CLOB"
            else:
                return f"VARCHAR2({max(50, min(4000, max_length))})"



def generate_table_name_from_filename(filename: str) -> str:
    """
    Generate a valid table name from filename with unique ID.

    Args:
        filename: Original filename

    Returns:
        Valid table name in lowercase with short unique ID appended
    """
    import uuid

    # Remove extension
    base_name = filename.rsplit('.', 1)[0]

    # Replace invalid characters with underscore
    table_name = ''.join(c if c.isalnum() else '_' for c in base_name)

    # Ensure it starts with a letter
    if not table_name[0].isalpha():
        table_name = 't_' + table_name

    # Convert to lowercase
    # table_name = table_name.lower()

    # Generate short unique ID (8 characters from UUID)
    short_uuid = str(uuid.uuid4())[:8]

    # Append unique ID to table name
    table_name = f"{table_name}_{short_uuid}"

    return table_name.upper()


async def call_metadata_assistant(
        headers: List[str],
        sample_data: List[List[str]],
        column_mapping: Dict[str, str],
        db_type: str,
        table_name: str
) -> Dict[str, str]:
    """
    Call /metadata/assistant LLM endpoint to generate column descriptions.
    Includes both original Excel headers and database-safe column names.

    Args:
        headers: List of original Excel column names.
        sample_data: Sample rows for context.
        column_mapping: Dict mapping original -> sanitized DB-safe names.
        db_type: Database type (oracle, postgres, etc.).
        table_name: Name of the uploaded table.

    Returns:
        Dict mapping DB-safe column name -> description text.
    """
    try:
        # Build LLM-friendly payload for /metadata/assistant
        columns_input = []
        for i, header in enumerate(headers):
            safe_name = column_mapping.get(header, header)
            sample_values = [row[i] if i < len(row) else "" for row in sample_data[:5]]

            columns_input.append({
                "original_name": header,
                "name": safe_name,
                "data_type": None,          # LLM infers meaning
                "sample_values": sample_values
            })

        table_input = {
            "tables": [
                {
                    "name": table_name,
                    "description": "",
                    "columns": columns_input,
                    "foreign_keys": [],
                    "column_mapping": column_mapping,
                    "db_type": db_type
                }
            ]
        }

        logger.info(f"Calling metadata_assistant for table {table_name} with {len(columns_input)} columns")

        # Call the metadata assistant API (FastAPI internal)


        import numpy as np, math, json

        # Safely clean NaN / np.float64 / np.int64
        def clean_json(obj):
            if isinstance(obj, dict):
                return {k: clean_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_json(v) for v in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                if math.isnan(obj):
                    return None
                return float(obj)
            else:
                return obj

        safe_payload = clean_json(payload)
        async with httpx.AsyncClient(timeout=60.0) as client:
         response = await client.post("http://localhost:11901/projects/metadata/assistant", json=safe_payload)
        if response.status_code != 200:
            logger.warning(f"Metadata assistant returned HTTP {response.status_code}")
            return {}

        result = response.json()
        suggestions = result.get("suggestions", [])

        # Map response back to safe DB column names
        descriptions = {}
        for s in suggestions:
            if s.get("target_type") == "column":
                col = s.get("column")
                text = s.get("text", "")
                if col:
                    descriptions[col] = text

        logger.info(f"Received {len(descriptions)} column descriptions from metadata_assistant")
        return descriptions

    except Exception as e:
        logger.error(f"Error calling metadata_assistant: {e}", exc_info=True)
        return {}


async def get_project_by_id(project_id: int, db: AsyncSession) -> Optional[Dict]:
    """
    Get project details by ID from local database.

    Args:
        project_id: ID of the project
        db: Database session

    Returns:
        Project data dictionary with hydrated Project object, or None
    """
    from projects.services.local_projects import LocalProjects

    try:
        # Get project from local database
        project_obj = await LocalProjects.get_project(db, project_id)
        if project_obj:
            return {
                "id": project_obj.id,
                "name": project_obj.name,
                "connection": project_obj.connection,
                "db_metadata": project_obj.db_metadata,
                "project": project_obj  # Include the full object for update operations
            }
        return None
    except Exception as e:
        logger.error(f"Error getting project by ID: {e}")
        return None


async def get_project_by_name(project_name: str, db: AsyncSession) -> Optional[Dict]:
    """
    Get project details by name from local database.

    Args:
        project_name: Name of the project
        db: Database session

    Returns:
        Project data dictionary with hydrated Project object, or None
    """
    from projects.services.local_projects import LocalProjects

    try:
        # Get project from local database
        project_obj = await LocalProjects.get_project_by_name(db, project_name)
        if project_obj:
            return {
                "id": project_obj.id,
                "name": project_obj.name,
                "connection": project_obj.connection,
                "db_metadata": project_obj.db_metadata,
                "project": project_obj  # Include the full object for update operations
            }
        return None
    except Exception as e:
        logger.error(f"Error getting project by name: {e}")
        return None


async def trigger_recommendation_qa_generation(project_id: int) -> None:
    """
    Trigger recommendation QA generation for the project using add_update_project logic.

    Args:
        project_id: ID of the project
    """
    try:
        from projects.services.projects import Projects
        from projects.models import Project

        projects_service = Projects()

        # Get the project
        project_data = await projects_service.get_project(project_id)
        if not project_data:
            logger.warning(f"Project {project_id} not found for QA generation")
            return

        project = Project(**project_data)

        # Trigger training (ingest and train metadata)
        logger.info(f"Triggering recommendation QA generation for project {project_id}")
        training_state = await projects_service.ingest_train_metadata(project)

        logger.info(f"QA generation initiated with task_id: {training_state.get('task_id')}")

    except Exception as e:
        logger.error(f"Error triggering recommendation QA generation: {e}")
        # Don't fail the upload if QA generation fails




# Reserved words
ORACLE_RESERVED = {
    "ACCESS", "ADD", "ALL", "ALTER", "AND", "ANY", "AS", "ASC", "BEGIN",
    "BETWEEN", "BY", "CASE", "CHECK", "CLUSTER", "COLUMN", "COMMENT",
    "CONNECT", "CREATE", "CURRENT", "DATE", "DECIMAL", "DEFAULT",
    "DELETE", "DESC", "DISTINCT", "DROP", "ELSE", "END", "EXISTS",
    "FLOAT", "FOR", "FROM", "GRANT", "GROUP", "HAVING", "IN", "INDEX",
    "INSERT", "INTEGER", "INTO", "IS", "LEVEL", "LIKE", "LOCK", "LONG",
    "MINUS", "MODE", "MODIFY", "NOT", "NULL", "NUMBER", "OF", "ON",
    "OPTION", "OR", "ORDER", "PCTFREE", "PRIOR", "PUBLIC", "RAW",
    "RENAME", "RESOURCE", "REVOKE", "ROW", "ROWID", "ROWNUM", "SELECT",
    "SESSION", "SET", "SHARE", "SIZE", "SMALLINT", "START", "TABLE",
    "THEN", "TO", "TRIGGER", "UNION", "UNIQUE", "UPDATE", "USER",
    "VALIDATE", "VALUES", "VARCHAR", "VARCHAR2", "VIEW", "WHERE", "WITH",
    "ROLE", "PROFILE"
}

PG_RESERVED = {
    "user", "role", "level", "order", "group", "select", "where", "table",
    "column", "view", "index", "primary", "key", "constraint"
}

# -----------------------------------------------------------
# ✅ Utility Functions
# -----------------------------------------------------------

def is_arabic_text(text: str) -> bool:
    """Detect if text contains any Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text or ""))


def sanitize_column_name(col_name: str, db_type: str, index: int = 0) -> str:
    """
    Convert Excel header to safe DB identifier.
    If Arabic or unreadable, fallback to 'col_<index>'.
    """
    import re
    import unicodedata

    # detect Arabic / non-ASCII
    def is_arabic(text):
        return any("\u0600" <= ch <= "\u06FF" for ch in text)

    if not col_name or is_arabic(col_name) or not col_name.isascii():
        return f"col_{index}"

    safe = re.sub(r"[^0-9A-Za-z_]", "_", col_name.strip())
    if db_type.lower() == "oracle":
        safe = safe.upper()
        if safe in ORACLE_RESERVED:
            safe += "_COL"
    else:
        safe = safe.lower()
        if safe in PG_RESERVED:
            safe += "_col"
    if re.match(r"^[0-9]", safe):
        safe = f"col_{safe}"
    return safe



def detect_header_row(df: pd.DataFrame, max_scan_rows: int = 5) -> int:
    """Detect which row likely contains the real headers."""
    for i in range(min(max_scan_rows, len(df))):
        row = df.iloc[i].dropna().tolist()
        if len(row) > 1 and all(isinstance(x, str) and len(x) < 40 for x in row if pd.notna(x)):
            return i
    return 0


def parse_file_data(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV/Excel and auto-detect header row (skip titles)."""
    if filename.lower().endswith(".csv"):
        df_raw = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig", header=None)
    elif filename.lower().endswith((".xls", ".xlsx")):
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
    else:
        raise ValueError("Unsupported file format")

    header_row = detect_header_row(df_raw)
    headers = df_raw.iloc[header_row].fillna("").tolist()
    df = df_raw.iloc[header_row + 1:].reset_index(drop=True)
    df.columns = headers
    df = df.dropna(how="all", axis=1)

    title_text = " ".join(df_raw.iloc[:header_row].fillna("").astype(str).values.flatten())
    logger.info(f"Detected title section: {title_text}")

    return df


# =========================================================
# SAFE DROP TABLE HANDLER (Oracle + PostgreSQL compatible)
# =========================================================
def drop_table_if_exists(cursor, connection, table_name: str, db_type: str):
    """Safely drop an existing table, view, or synonym."""
    try:
        if db_type.lower() in ("oracle", "oracle_free", "oracle_xe"):
            plsql = f"""
            DECLARE
                obj_type VARCHAR2(30);
            BEGIN
                SELECT object_type INTO obj_type
                FROM all_objects
                WHERE object_name = UPPER('{table_name}')
                AND owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                AND ROWNUM = 1;

                IF obj_type = 'TABLE' THEN
                    EXECUTE IMMEDIATE 'DROP TABLE {table_name} CASCADE CONSTRAINTS';
                ELSIF obj_type = 'VIEW' THEN
                    EXECUTE IMMEDIATE 'DROP VIEW {table_name}';
                ELSIF obj_type = 'SYNONYM' THEN
                    EXECUTE IMMEDIATE 'DROP SYNONYM {table_name}';
                END IF;
            EXCEPTION
                WHEN NO_DATA_FOUND THEN
                    NULL;
            END;
            """
            cursor.execute(plsql)
        else:
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

        connection.commit()
        logger.info(f"🗑️ Dropped existing object named {table_name} if it existed.")
    except Exception as e:
        logger.warning(f"⚠️ Could not drop object {table_name}: {e}")
        connection.rollback()


# =========================================================
# SAFE SQL VALUE CONVERTER
# =========================================================
def safe_sql_value(val, sql_type: str) -> str:
    """Safely format a Python value for Oracle/Postgres SQL INSERT."""
    if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
        return "NULL"

    sql_type = (sql_type or "").upper()

    # --- String types ---
    if any(t in sql_type for t in ["CHAR", "VARCHAR", "CLOB", "TEXT"]):
        escaped = str(val).replace("'", "''").strip()
        return f"'{escaped}'"

    # --- Date/time types ---
    if "DATE" in sql_type or "TIMESTAMP" in sql_type:
        try:
            parsed = pd.to_datetime(val, errors="coerce")
            if pd.isna(parsed):
                return "NULL"
            # Use Oracle TO_DATE or ISO for Postgres
            return f"TO_DATE('{parsed.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        except Exception:
            return "NULL"

    # --- Numeric types ---
    if any(t in sql_type for t in ["NUMBER", "INT", "DECIMAL", "NUMERIC", "FLOAT"]):
        try:
            return str(float(val)).rstrip("0").rstrip(".") if "." in str(val) else str(int(float(val)))
        except Exception:
            return "NULL"

    # --- Fallback ---
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"



# =========================================================
# UPLOAD ENDPOINT
# =========================================================
@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload CSV/Excel → Auto-clean → Create DB table → Generate metadata → Trigger LLM enrichment.

    Args:
        file: CSV or Excel file to upload
        project_id: ID of the project to upload to
        db: Database session
    """
    connection = None
    cursor = None

    try:
        logger.info(f"📂 Starting upload for {file.filename} to project_id={project_id}")
        file_content = await file.read()

        if file.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            df = pd.read_csv(io.StringIO(file_content.decode("utf-8")), encoding="utf-8")

        if df.empty:
            raise HTTPException(status_code=400, detail="File is empty or has no data")

        logger.info(f"✅ Parsed file: {len(df)} rows, {len(df.columns)} columns")

        # --- Fetch project and DB connection ---
        project_data = await get_project_by_id(project_id, db)
        if not project_data:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        # Extract data from dict (project_data is a dict, not an object)
        actual_project_id = project_data["id"]
        connection_profile = project_data["connection"]
        db_type = connection_profile.db_type
        table_name = generate_table_name_from_filename(file.filename)

        # --- Sanitize headers (Arabic, empty, reserved words) ---
        headers = df.columns.tolist()
        columns, column_mapping = [], {}

        for i, col_name in enumerate(headers, start=1):
            col_name = str(col_name).strip()
            # Arabic / empty header fallback
            safe_col = sanitize_column_name(col_name, db_type, i)
            series = df[col_name] if col_name in df.columns else df.iloc[:, i - 1]
            data_type = infer_data_type(series, db_type=db_type)
            columns.append(ColumnDefinition(name=safe_col, dataType=data_type, description=None))
            column_mapping[col_name] = safe_col

        # --- Build CREATE TABLE SQL ---
        table_structure = TableStructure(tableName=table_name, columns=columns)
        create_table_sql = generate_create_table_sql(table_structure, db_type)
        logger.info(f"🧱 Generated CREATE TABLE:\n{create_table_sql}")

        # --- Connect and drop existing table if needed ---
        connector = get_connector(db_type)
        connection = connector.get_connection(connection_profile)
        cursor = connection.cursor()

        drop_table_if_exists(cursor, connection, table_name, db_type)

        # --- Create table ---
        cursor.execute(create_table_sql)
        connection.commit()

        # --- Insert rows safely with batch commits ---
        rows_inserted = 0
        col_names_sql = ", ".join([f'"{c.name}"' for c in columns])

        rows_inserted = 0
        col_names_sql = ", ".join([f'"{c.name}"' for c in columns])

        for idx, row in df.iterrows():
            try:
                values_sql = [safe_sql_value(v, c.dataType) for v, c in zip(row.tolist(), columns)]
                # Ensure all values are safe strings and properly comma-separated
                values_str = ", ".join(values_sql)
                insert_sql = f'INSERT INTO "{table_name}" ({col_names_sql}) VALUES ({values_str})'
                cursor.execute(insert_sql)
                rows_inserted += 1

                if rows_inserted % 100 == 0:
                    connection.commit()
                    logger.info(f"✅ Inserted {rows_inserted} rows so far...")

            except Exception as e:
                logger.warning(f"⚠️ Row {idx} insert failed: {e}")
                connection.rollback()
                continue

        connection.commit()
        logger.info(f"✅ Inserted total {rows_inserted} rows successfully.")


# --- Generate metadata using LLM ---
        sample_data = [df.iloc[i].tolist() for i in range(min(10, len(df)))]
        column_descriptions = await call_metadata_assistant(
            headers=headers,
            sample_data=sample_data,
            column_mapping=column_mapping,
            db_type=db_type,
            table_name=table_name,
        )

        # --- Build TableSchema ---
        column_meta = []
        for orig, col in zip(headers, columns):
            desc = column_descriptions.get(orig, f"Column {orig}")
            col_meta = TableColumn(
                name=col.name,
                data_type=col.dataType,
                description=desc,
                is_null=True,
                is_unique=False,
                is_range="NUMBER" in col.dataType,
                groupable=True,
                aggregation=["SUM", "AVG", "MIN", "MAX", "COUNT"] if "NUMBER" in col.dataType else ["COUNT"],
            )
            column_meta.append(col_meta)
        table_description = (
            table_name.split("_")[0].upper()
            if "_" in table_name
            else table_name.upper()
        )
        new_schema = TableSchema(name=table_name,  description=table_description,columns=column_meta, foreign_keys=[])

        # --- Update Project metadata safely ---
        from projects.services.local_projects import LocalProjects

        project_obj = project_data["project"]  # Get the Project object we stored earlier

        if not project_obj.db_metadata:
            project_obj.db_metadata = []
        project_obj.db_metadata = [t for t in project_obj.db_metadata if t.name != table_name]
        project_obj.db_metadata.append(new_schema)

        await LocalProjects.update_project(db, project_obj)
        logger.info(f"[UPLOAD] Project metadata updated with {table_name}")

        # --- Trigger async recommendation QA generation ---
        asyncio.create_task(trigger_recommendation_qa_generation(actual_project_id))

        return UploadResponse(
            success=True,
            message=f"✅ Uploaded and processed {file.filename}",
            projectId=actual_project_id,
            tableName=table_name,
            rowsInserted=rows_inserted,
        )

    except Exception as e:
        logger.exception(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()








# ================== NEW /recommendations/question ENDPOINT ==================

class RecommendationQuestionRequest(BaseModel):
    """Request for getting recommendation questions by project"""
    projectId: int


class RecommendationQuestionItem(BaseModel):
    """Individual recommendation question"""
    recomended_qstn_id: str
    question: str


class RecommendationQuestionResponse(BaseModel):
    """Response with all recommendation questions for a project"""
    project_id: int
    description: str
    recommendations_list: List[RecommendationQuestionItem]


@router.post("/recommendations/question", response_model=List[RecommendationQuestionResponse])
async def get_recommendation_questions(
    request: RecommendationQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all recommendation questions for a project, grouped by recommendation groups.

    This endpoint:
    1. Gets all recommendation groups for the given project_id
    2. For each group, gets all recommendation questions
    3. Returns grouped questions with group description

    Args:
        request: RecommendationQuestionRequest with projectId
        db: Database session

    Returns:
        List[RecommendationQuestionResponse] with grouped recommendations

    Example Response:
    [
        {
            "project_id": 17,
            "description": "Order Trends",
            "recommendations_list": [
                {
                    "recomended_qstn_id": "16_group_0_recom_qstn_0",
                    "question": "What are the total quantity of products ordered?"
                }
            ]
        }
    ]
    """
    try:
        from sqlalchemy import select
        try:
            from db.recomendation_group.models import RecommendationGroupModel
            from db.recomendation_questions.models import RecomendedQuestionsModel
        except ImportError as e:
            logger.error(f"Recommendation models not available: {e}")
            raise HTTPException(
                status_code=501,
                detail="Recommendation feature not implemented. Missing database models: db.recomendation_group and db.recomendation_questions"
            )

        logger.info(f"Fetching recommendation questions for project_id: {request.projectId}")

        # Step 1: Get all recommendation groups for this project
        stmt = select(RecommendationGroupModel).where(
            RecommendationGroupModel.project_id == request.projectId
        )
        result = await db.execute(stmt)
        groups = result.scalars().all()

        if not groups:
            logger.warning(f"No recommendation groups found for project_id: {request.projectId}")
            return []

        logger.info(f"Found {len(groups)} recommendation groups")

        # Step 2: For each group, get all questions
        response_list = []

        for group in groups:
            # Get all questions for this group
            stmt_questions = select(RecomendedQuestionsModel).where(
                RecomendedQuestionsModel.project_id == request.projectId,
                RecomendedQuestionsModel.group_id == group.group_id
            )
            result_questions = await db.execute(stmt_questions)
            questions = result_questions.scalars().all()

            logger.info(f"Group {group.group_id} has {len(questions)} questions")

            # Build recommendation list for this group
            recommendations_list = [
                RecommendationQuestionItem(
                    recomended_qstn_id=q.recomended_qstn_id,
                    question=q.question or ""  # Handle None values
                )
                for q in questions
            ]

            # Add to response
            response_list.append(
                RecommendationQuestionResponse(
                    project_id=request.projectId,
                    description=group.description or group.name or "Recommendations",
                    recommendations_list=recommendations_list
                )
            )

        logger.info(f"Returning {len(response_list)} recommendation groups with questions")
        return response_list

    except Exception as e:
        logger.error(f"Error fetching recommendation questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recommendation questions: {str(e)}"
        )


# ================== NEW /executequey ENDPOINT ==================

class ExecuteQueryRequest(BaseModel):
    """Request for executing query with natural language"""
    project_id: int
    question: str
    response_id: Optional[str] = None  # If provided, fetch cached response from database


class QueryFilterData(BaseModel):
    """Filter and aggregation metadata from query"""
    time_period: Optional[str] = None
    group_by: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class Statistics(BaseModel):
    """Statistics computed from query results"""
    total_rows: int
    total_categories: Optional[int] = None
    grand_total: Optional[float] = None
    highest_category: Optional[Dict[str, Any]] = None
    lowest_category: Optional[Dict[str, Any]] = None
    average_per_category: Optional[float] = None
    additional_stats: Optional[Dict[str, Any]] = None


class ExecuteQueryResponse(BaseModel):
    """Response from query execution with analytics"""
    response_id: str
    question: str
    llm_generated_sql: str
    query_filter_data: QueryFilterData
    db_result: List[Dict[str, Any]]
    statistics: Statistics
    human_readable_answer: str
    quotation: str
    metadata: Dict[str, Any]


# ================== NEW /generatereport ENDPOINT ==================

class RecommendedQuestion(BaseModel):
    """Single recommended question with SQL"""
    recomended_qstn_id: str
    sql_query: str
    question: str


class GenerateReportRequest(BaseModel):
    """Request for generating HTML report"""
    projectId: int
    recomended_questions: Optional[List[RecommendedQuestion]] = None
    recomended_qstn_id: Optional[str] = None  # Single question ID
    question: Optional[str] = None  # Natural language question for dynamic SQL generation


async def fetch_questions_from_db(db: AsyncSession, project_id: int, question_id: str) -> List[RecommendedQuestion]:
    """
    Fetch recommendation questions from database.

    Args:
        db: Database session
        project_id: Project ID
        question_id: Question ID to fetch

    Returns:
        List of RecommendedQuestion objects
    """
    from sqlalchemy import select
    try:
        from db.recomendation_questions.models import RecomendedQuestionsModel
    except ImportError as e:
        logger.error(f"Recommendation questions model not available: {e}")
        raise HTTPException(
            status_code=501,
            detail="Recommendation feature not implemented. Missing database model: db.recomendation_questions"
        )

    logger.info(f"Fetching question {question_id} for project {project_id}")

    stmt = select(RecomendedQuestionsModel).where(
        RecomendedQuestionsModel.project_id == project_id,
        RecomendedQuestionsModel.recomended_qstn_id == question_id
    )

    result = await db.execute(stmt)
    questions = result.scalars().all()

    if not questions:
        logger.warning(f"No questions found for {question_id}")
        return []

    # Convert to RecommendedQuestion format
    recommended_questions = []
    for q in questions:
        recommended_questions.append(RecommendedQuestion(
            recomended_qstn_id=q.recomended_qstn_id,
            sql_query=q.sql_query or "",
            question=q.question or ""
        ))

    logger.info(f"Found {len(recommended_questions)} question(s)")
    return recommended_questions


import json
import re
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def generate_sql_from_question(question: str, db_metadata: list, dialect: str = "Oracle") -> str:
    """
    Generate SQL query from natural language question using LLM.
    Includes validation, fallback handling, Arabic keyword mapping,
    and automatic Oracle identifier quoting.
    """

    from llm.ChatModel import ChatModel
    from prompts.prompts import Prompts
    from llm_config.llm_config_manager import get_llm_config

    try:
        logger.info(f"[SQL_GEN] Generating SQL from question: {question}")

        # Step 1: Prepare schema JSON
        schema_dict = {}
        for table in db_metadata:
            if hasattr(table, "name") and hasattr(table, "columns"):
                table_columns = []
                for col in table.columns:
                    col_info = {
                        "name": col.name,
                        "data_type": col.data_type,
                    }
                    if hasattr(col, "description") and col.description:
                        col_info["description"] = col.description
                    table_columns.append(col_info)
                schema_dict[table.name] = table_columns

        schema_json = json.dumps(schema_dict, indent=2, ensure_ascii=True)
        logger.info(f"[SQL_GEN] Schema prepared for SQL generation ({len(schema_dict)} tables)")

        # Step 2: Initialize LLM
        llm_config = get_llm_config("sql_generation")
        chat_model = ChatModel(
            api_url=llm_config.base_url,
            model=f"{llm_config.provider}/{llm_config.model}",
            api_key=llm_config.api_key
        )
        prompts = Prompts()

        # Step 3: Prepare prompt
        main_prompt = prompts.get_prompt_by_key("sql_query_generator").format(
            dialect=dialect,
            schema=schema_json
        )
        instruct_prompt = prompts.get_prompt_by_key("sql_query_from_user_question_prompt").format(
            dialect=dialect
        )

        combined_prompt = f"{main_prompt}\n\nUser Question: {question}\n\n{instruct_prompt}"

        # Step 4: Call LLM
        logger.info("[SQL_GEN] Calling LLM to generate SQL...")
        sql_query = chat_model.infer_llm(user_prompt=combined_prompt, temperature=0.1)

        if not sql_query or "error" in str(sql_query).lower():
            raise ValueError(f"LLM returned invalid response: {sql_query}")

        # Step 5: Clean and validate SQL
        sql_query = str(sql_query).strip()
        sql_query = re.sub(r"^```(sql)?|```$", "", sql_query).strip()

        # Fix duplicate SELECT statements and incomplete UNION (LLM sometimes returns multiple queries)
        # Example: "SELECT ... SELECT ..." -> "SELECT ..."
        # Example: "SELECT ... UNION" -> "SELECT ..."

        # Remove trailing incomplete UNION/UNION ALL
        sql_query = re.sub(r'\s+(UNION\s*ALL?)\s*$', '', sql_query, flags=re.IGNORECASE).strip()

        select_matches = list(re.finditer(r'(?i)\bSELECT\b', sql_query))
        if len(select_matches) > 1:
            # Multiple SELECT statements found - take only the first complete one
            first_select_pos = select_matches[0].start()
            second_select_pos = select_matches[1].start()
            # Extract only the first SELECT statement
            sql_query = sql_query[first_select_pos:second_select_pos].strip()
            # Remove trailing UNION again after extraction
            sql_query = re.sub(r'\s+(UNION\s*ALL?)\s*$', '', sql_query, flags=re.IGNORECASE).strip()
            logger.warning(f"[SQL_GEN] Removed duplicate SELECT statements. Using first query only.")

        if not re.match(r"(?i)^(select|insert|update|delete|create|with)\b", sql_query):
            logger.warning(f"[SQL_GEN] LLM output not a valid SQL statement: {sql_query}")
            raise ValueError("Invalid SQL generated by LLM")

        # Step 6: Quote table and column names for Oracle and PostgreSQL safety
        # Only quote identifiers that are not already quoted
        if dialect.lower() in ("oracle", "postgres", "postgresql"):
            for table_name in schema_dict.keys():
                # Match table name not already surrounded by quotes
                sql_query = re.sub(
                    rf'(?<!")(\b{table_name}\b)(?!")',
                    f'"{table_name}"',
                    sql_query,
                    flags=re.IGNORECASE
                )
            all_columns = [col["name"] for cols in schema_dict.values() for col in cols]
            for col in all_columns:
                # Match column name not already surrounded by quotes
                sql_query = re.sub(rf'(?<!")(\b{col}\b)(?!")', f'"{col}"', sql_query, flags=re.IGNORECASE)

        logger.info(f"[SQL_GEN] Final Generated SQL:\n{sql_query}")
        return sql_query

    except Exception as e:
        logger.error(f"[SQL_GEN] LLM SQL generation failed: {str(e)}")

        # Step 7: Safe fallback - Arabic keyword detection
        fallback_sql = None
        try:
            table_name = next(iter(schema_dict.keys()))
            salary_col = None
            job_col = None
            for c in schema_dict[table_name]:
                if "راتب" in c.get("description", ""):
                    salary_col = c["name"]
                if "وظيف" in c.get("description", ""):
                    job_col = c["name"]

            if "متوسط" in question and salary_col:
                fallback_sql = f'SELECT AVG("{salary_col}") AS متوسط_الراتب FROM "{table_name}"'
                if "قسم" in question or "موارد" in question:
                    if job_col:
                        fallback_sql += f' WHERE "{job_col}" LIKE \'%الموارد البشرية%\''
            elif "مجموع" in question and salary_col:
                fallback_sql = f'SELECT SUM("{salary_col}") AS مجموع_الرواتب FROM "{table_name}"'
            elif "عدد" in question:
                fallback_sql = f'SELECT COUNT(*) AS عدد_الموظفين FROM "{table_name}"'

            if fallback_sql:
                logger.info(f"🛟 Using fallback SQL:\n{fallback_sql}")
                return fallback_sql

        except Exception as inner_e:
            logger.error(f"Error building fallback SQL: {inner_e}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SQL from question: {str(e)}"
        )




@router.post("/generatereport")
async def generate_report(
    request: GenerateReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate interactive HTML report with charts from SQL queries.

    This endpoint supports three modes:

    Mode 1: Pass full question data
    {
        "projectId": 17,
        "recomended_questions": [{"recomended_qstn_id": "...", "sql_query": "...", "question": "..."}]
    }

    Mode 2: Pass question ID - fetches from database
    {
        "projectId": 17,
        "recomended_qstn_id": "17_group_1_recom_qstn_0"
    }

    Mode 3: Pass natural language question - generates SQL using LLM
    {
        "projectId": 17,
        "question": "What is the total amount spent by customers who have placed more than 5 orders?"
    }

    Args:
        request: GenerateReportRequest with projectId and either recomended_questions, recomended_qstn_id, or question
        db: Database session

    Returns:
        HTML response with interactive charts
    """
    try:
        logger.info(f"Generating report for project_id: {request.projectId}")

        # Get project data from local database
        project_data = await get_project_by_id(request.projectId, db)

        if not project_data:
            raise HTTPException(
                status_code=404,
                detail=f"Project {request.projectId} not found"
            )

        # project_data contains both dict fields and project object
        project = project_data["project"]

        # Determine which mode: direct questions, fetch from DB, or generate SQL
        if request.recomended_questions:
            # Mode 1: Questions provided directly
            questions = request.recomended_questions
            logger.info(f"Mode 1: Using provided questions: {len(questions)} questions")
        elif request.recomended_qstn_id:
            # Mode 2: Fetch question from database
            logger.info(f"Mode 2: Fetching question from database: {request.recomended_qstn_id}")
            questions = await fetch_questions_from_db(db, request.projectId, request.recomended_qstn_id)
            if not questions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Question {request.recomended_qstn_id} not found in database"
                )
            logger.info(f"Fetched {len(questions)} question(s) from database")
        elif request.question:
            # Mode 3: Generate SQL from natural language question using LLM
            logger.info(f"Mode 3: Generating SQL from natural language question")

            # Get database type from project connection
            db_type = project.connection.db_type
            # Map db_type to SQL dialect for LLM
            dialect = "PostgreSQL" if db_type.lower() in ("postgres", "postgresql") else "Oracle"
            logger.info(f"Using SQL dialect: {dialect} for db_type: {db_type}")

            # Generate SQL using LLM
            sql_query = await generate_sql_from_question(
                question=request.question,
                db_metadata=project.db_metadata,
                dialect=dialect
            )

            # Create question object with generated SQL
            questions = [RecommendedQuestion(
                recomended_qstn_id=f"adhoc_{int(time.time())}",
                sql_query=sql_query,
                question=request.question
            )]
            logger.info(f"Generated SQL for natural language question")
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'recomended_questions', 'recomended_qstn_id', or 'question' must be provided"
            )

        logger.info(f"Processing {len(questions)} questions")

        # Get connector for database queries
        import projects.services.db_metadata as metadata
        connector = metadata.get_connector(project.connection.db_type)
        connector.get_connection(project.connection)

        # Process each question
        report_data = []
        error_details = []

        for question in questions:
            try:
                logger.info(f"Processing question: {question.recomended_qstn_id}")
                logger.info(f"SQL Query: {question.sql_query}")

                # Execute SQL query
                sql_query = question.sql_query.replace('\n', ' ').replace(';', '')

                logger.info(f"Executing query against database...")
                result, error = await connector.execute_query(
                    sql_query,
                    project.db_metadata,
                    result_limit=-1  # Get all results
                )

                logger.info(f"Query execution result - Error: {error}, Result type: {type(result)}")

                if error:
                    error_msg = f"SQL error for {question.recomended_qstn_id}: {error}"
                    logger.error(error_msg)
                    error_details.append({
                        "question_id": question.recomended_qstn_id,
                        "error": str(error),
                        "sql": question.sql_query
                    })
                    continue

                # Handle ResultSet object (Pydantic model) or dict
                from projects.models import ResultSet

                if isinstance(result, ResultSet):
                    # ResultSet is a Pydantic model with columns and rows attributes
                    columns = result.columns
                    rows = result.rows
                    logger.info(f"ResultSet format - Columns: {columns}, Rows count: {len(rows)}")
                elif isinstance(result, dict):
                    # Fallback for dict format
                    columns = result.get("columns", [])
                    rows = result.get("rows", [])
                    logger.info(f"Dict format - Columns: {columns}, Rows count: {len(rows)}")
                else:
                    error_msg = f"Unexpected result format for {question.recomended_qstn_id}: {type(result)}"
                    logger.error(error_msg)
                    error_details.append({
                        "question_id": question.recomended_qstn_id,
                        "error": "Unexpected result format",
                        "result_type": str(type(result))
                    })
                    continue

                logger.info(f"Data - Columns: {len(columns)}, Rows: {len(rows)}")

                if not columns or not rows:
                    error_msg = f"No data returned for {question.recomended_qstn_id} - Columns: {len(columns)}, Rows: {len(rows)}"
                    logger.warning(error_msg)
                    error_details.append({
                        "question_id": question.recomended_qstn_id,
                        "error": "No data returned from query",
                        "columns_count": len(columns),
                        "rows_count": len(rows)
                    })
                    continue

                # Call chart-spec API
                chart_spec_response = await call_chart_spec_api(question.question, columns, rows)

                # Add to report data
                report_data.append({
                    "id": question.recomended_qstn_id,
                    "question": question.question,
                    "sql_query": question.sql_query,
                    "columns": columns,
                    "rows": rows,
                    "chart_spec": chart_spec_response
                })

                logger.info(f"Successfully processed {question.recomended_qstn_id}")

            except Exception as e:
                error_msg = f"Error processing question {question.recomended_qstn_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                error_details.append({
                    "question_id": question.recomended_qstn_id,
                    "error": str(e),
                    "traceback": "Check server logs for full traceback"
                })
                continue

        if not report_data:
            # Provide detailed error information
            error_summary = f"No valid data to generate report. Processed {len(questions)} questions, all failed."
            if error_details:
                error_summary += f" Errors: {json.dumps(error_details, indent=2)}"

            logger.error(error_summary)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "No valid data to generate report",
                    "total_questions": len(questions),
                    "successful_questions": 0,
                    "errors": error_details
                }
            )

        # Generate HTML report
        html_content = generate_html_report(report_data, project.name)

        logger.info(f"Generated HTML report with {len(report_data)} charts")

        # Return HTML response
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


async def call_chart_spec_api(message: str, columns: List[str], rows: List[List]) -> Dict:
    """
    Call the chart-spec API to get chart recommendations.

    Args:
        message: The question/message for context
        columns: Column names
        rows: Data rows

    Returns:
        Chart specification dictionary
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                CHART_SPEC_URL,
                json={
                    "message": message,
                    "table": {
                        "columns": columns,
                        "rows": rows
                    }
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Chart-spec API returned status {response.status_code}")
                # Return fallback spec
                return {
                    "chartType": "bar",
                    "xField": columns[0] if columns else "x",
                    "yField": columns[1] if len(columns) > 1 else "y",
                    "chartTypes": ["bar", "line", "pie", "table"],
                    "title": message
                }

    except Exception as e:
        logger.error(f"Error calling chart-spec API: {e}")
        # Return fallback spec
        return {
            "chartType": "bar",
            "xField": columns[0] if columns else "x",
            "yField": columns[1] if len(columns) > 1 else "y",
            "chartTypes": ["bar", "line", "pie", "table"],
            "title": message
        }


def generate_html_report(report_data: List[Dict], project_name: str) -> str:
    """
    Generate interactive HTML report with charts.

    Args:
        report_data: List of data items with columns, rows, and chart_spec
        project_name: Name of the project

    Returns:
        HTML string with embedded JavaScript for interactive charts
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report - {project_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #ffffff;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            border: 1px solid #e0e0e0;
            margin-bottom: 30px;
        }}
        .chart-title {{
            font-size: 1.5em;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
        }}
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .control-group label {{
            font-size: 0.9em;
            color: #666;
            font-weight: 600;
        }}
        select {{
            padding: 10px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            background: white;
            cursor: pointer;
            transition: border-color 0.3s;
        }}
        select:hover {{
            border-color: #667eea;
        }}
        select:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .canvas-wrapper {{
            position: relative;
            height: 400px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .sql-query {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #333;
            margin-top: 15px;
            overflow-x: auto;
        }}
        .toggle-sql {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s;
        }}
        .toggle-sql:hover {{
            background: #5568d3;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
"""

    # Add each chart
    for idx, item in enumerate(report_data):
        chart_id = f"chart_{idx}"
        table_id = f"table_{idx}"
        sql_id = f"sql_{idx}"

        columns = item["columns"]
        rows = item["rows"]
        chart_spec = item["chart_spec"]

        # Get chart configuration
        chart_type = chart_spec.get("chartType", "bar")
        x_field = chart_spec.get("xField", columns[0])
        y_field = chart_spec.get("yField", columns[1] if len(columns) > 1 else columns[0])
        chart_types = chart_spec.get("chartTypes", ["bar", "line", "pie", "table"])

        # Ensure 'table' is always in chart_types
        if "table" not in chart_types:
            chart_types.append("table")

        # Detect numeric columns
        numeric_columns = []
        for col_idx, col in enumerate(columns):
            try:
                # Check if column has numeric values
                for row in rows[:5]:  # Check first 5 rows
                    if col_idx < len(row):
                        float(row[col_idx])
                numeric_columns.append(col)
                break
            except:
                pass

        if not numeric_columns:
            numeric_columns = columns[1:] if len(columns) > 1 else columns

        html += f"""
        <div class="chart-container">
            <div class="chart-title">{item['question']}</div>

            <div class="controls">
                <div class="control-group">
                    <label>Chart Type:</label>
                    <select id="type_{chart_id}" onchange="updateChart_{idx}()">
"""

        for ct in chart_types:
            selected = "selected" if ct == chart_type else ""
            html += f'                        <option value="{ct}" {selected}>{ct.title()}</option>\n'

        html += f"""
                    </select>
                </div>

                <div class="control-group">
                    <label>X-Axis:</label>
                    <select id="x_{chart_id}" onchange="updateChart_{idx}()">
"""

        for col in columns:
            selected = "selected" if col == x_field else ""
            html += f'                        <option value="{col}" {selected}>{col}</option>\n'

        html += f"""
                    </select>
                </div>

                <div class="control-group">
                    <label>Y-Axis: <small style="color: #999; font-weight: normal;">(Ctrl+Click for multiple)</small></label>
                    <select id="y_{chart_id}" onchange="updateChart_{idx}()" multiple size="3">
"""

        for col in numeric_columns:
            selected = "selected" if col == y_field else ""
            html += f'                        <option value="{col}" {selected}>{col}</option>\n'

        html += f"""
                    </select>
                </div>

                <div class="control-group">
                    <label>&nbsp;</label>
                    <button class="toggle-sql" onclick="toggleSQL_{idx}()">Show SQL</button>
                </div>
            </div>

            <div class="canvas-wrapper">
                <canvas id="{chart_id}"></canvas>
            </div>

            <div id="{table_id}" class="hidden"></div>

            <div id="{sql_id}" class="sql-query hidden">
                {item['sql_query']}
            </div>
        </div>

        <script>
            let chart_{idx} = null;

            const data_{idx} = {{
                columns: {json.dumps(columns)},
                rows: {json.dumps(rows)}
            }};

            function toggleSQL_{idx}() {{
                const sqlDiv = document.getElementById('{sql_id}');
                sqlDiv.classList.toggle('hidden');
            }}

            function updateChart_{idx}() {{
                const chartType = document.getElementById('type_{chart_id}').value;
                const xField = document.getElementById('x_{chart_id}').value;
                const ySelects = document.getElementById('y_{chart_id}').selectedOptions;
                const yFields = Array.from(ySelects).map(opt => opt.value);

                if (chartType === 'table') {{
                    showTable_{idx}();
                    return;
                }}

                // Ensure at least one Y-axis is selected
                if (yFields.length === 0) {{
                    console.warn('No Y-axis selected, using first numeric column');
                    const firstOption = document.getElementById('y_{chart_id}').options[0];
                    if (firstOption) {{
                        firstOption.selected = true;
                        yFields.push(firstOption.value);
                    }}
                }}

                document.getElementById('{table_id}').classList.add('hidden');
                document.getElementById('{chart_id}').parentElement.classList.remove('hidden');

                const xIdx = data_{idx}.columns.indexOf(xField);
                const labels = data_{idx}.rows.map(row => row[xIdx]);

                const datasets = yFields.map((yField, idx) => {{
                    const yIdx = data_{idx}.columns.indexOf(yField);
                    const data = data_{idx}.rows.map(row => parseFloat(row[yIdx]) || 0);

                    const colors = [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)'
                    ];

                    return {{
                        label: yField,
                        data: data,
                        backgroundColor: chartType === 'pie' ? colors : colors[idx % colors.length],
                        borderColor: chartType === 'pie' ? colors : colors[idx % colors.length].replace('0.8', '1'),
                        borderWidth: 2
                    }};
                }});

                if (chart_{idx}) {{
                    chart_{idx}.destroy();
                }}

                const ctx = document.getElementById('{chart_id}').getContext('2d');
                chart_{idx} = new Chart(ctx, {{
                    type: chartType,
                    data: {{
                        labels: labels,
                        datasets: datasets
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                position: 'top'
                            }},
                            title: {{
                                display: true,
                                text: '{item["question"]}'
                            }}
                        }},
                        scales: chartType !== 'pie' ? {{
                            y: {{
                                beginAtZero: true
                            }}
                        }} : {{}}
                    }}
                }});
            }}

            function showTable_{idx}() {{
                document.getElementById('{chart_id}').parentElement.classList.add('hidden');
                const tableDiv = document.getElementById('{table_id}');
                tableDiv.classList.remove('hidden');

                let tableHTML = '<table><thead><tr>';
                data_{idx}.columns.forEach(col => {{
                    tableHTML += `<th>${{col}}</th>`;
                }});
                tableHTML += '</tr></thead><tbody>';

                data_{idx}.rows.forEach(row => {{
                    tableHTML += '<tr>';
                    row.forEach(cell => {{
                        tableHTML += `<td>${{cell}}</td>`;
                    }});
                    tableHTML += '</tr>';
                }});

                tableHTML += '</tbody></table>';
                tableDiv.innerHTML = tableHTML;
            }}

            // Initialize chart
            updateChart_{idx}();
        </script>
"""

    html += """
    </div>
</body>
</html>
"""

    return html


# ================== NEW /executequey ENDPOINT ==================

@router.post("/executequey")
async def execute_query(
    request: ExecuteQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute natural language query with comprehensive analytics.

    This endpoint:
    1. Gets project details by name ("dev")
    2. Generates SQL from natural language question using LLM
    3. Executes SQL on the database
    4. Generates statistics from results
    5. Creates human-readable answer using LLM
    6. Returns comprehensive response with analytics or HTML visualization

    Request (new query):
    {
        "project_id": 17,
        "question": "What is the distribution of customers by gender?"
    }

    Request (cached response with HTML):
    {
        "project_id": 17,
        "question": "What is the distribution of customers by gender?",
        "response_id": "resp_20251022_144327_ea13ce"
    }

    Response (JSON):
    {
        "response_id": "resp_20251022_001",
        "question": "...",
        "llm_generated_sql": "SELECT...",
        "query_filter_data": {...},
        "db_result": [...],
        "statistics": {...},
        "human_readable_answer": "...",
        "quotation": "...",
        "metadata": {...}
    }

    Response (HTML): Interactive chart page
    """
    try:
        from projects.services.projects import Projects
        from datetime import datetime
        from fastapi.responses import HTMLResponse

        logger.info(f"Execute query request: project_id={request.project_id}, question={request.question}, response_id={request.response_id}")

        # Check if response_id is provided (cached response scenario)
        if request.response_id:
            logger.info(f"Fetching cached response: {request.response_id}")

            # Step 1: Get cached response from database
            cached_data = await get_cached_response(
                project_id=request.project_id,
                response_id=request.response_id,
                db=db
            )

            if not cached_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Cached response not found: response_id={request.response_id}, project_id={request.project_id}"
                )

            logger.info(f"Cached response found, executing SQL to get fresh data")

            # Step 2: Get project details and re-execute SQL
            project_data = await get_project_by_id(request.project_id, db)
            if not project_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project with ID {request.project_id} not found."
                )

            connection_profile = project_data["connection"]
            db_type = connection_profile.db_type

            # Step 3: Execute cached SQL query (using synchronous connector pattern)
            connector = get_connector(db_type)
            connection = connector.get_connection(connection_profile)
            cursor = connection.cursor()

            # Clean and execute SQL
            sql_query = cached_data["llm_generated_sql"].replace('\n', ' ').replace(';', '').strip()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert to list of dicts
            db_result = []
            for row in rows:
                row_dict = {}
                for idx, col_name in enumerate(columns):
                    value = row[idx]
                    # Convert to JSON-serializable types
                    if hasattr(value, 'isoformat'):  # datetime
                        value = value.isoformat()
                    elif isinstance(value, (bytes, bytearray)):
                        value = value.decode('utf-8', errors='ignore')
                    row_dict[col_name] = value
                db_result.append(row_dict)

            # Close connection
            cursor.close()
            connection.close()

            if not db_result:
                raise HTTPException(
                    status_code=500,
                    detail="Query returned no results"
                )

            logger.info(f"Query executed, got {len(db_result)} rows")

            # Step 4: Prepare data for chart-spec endpoint
            rows_for_chart = [[str(row.get(col, "")) for col in columns] for row in db_result]

            table_data = {
                "columns": columns,
                "rows": rows_for_chart
            }

            # Step 5: Call chart-spec endpoint
            logger.info("Calling chart-spec endpoint")
            chart_spec = await call_chart_spec_endpoint(
                question=cached_data["question"],
                table_data=table_data
            )

            # Step 6: Generate interactive HTML
            logger.info("Generating interactive HTML")
            html_content = generate_interactive_html(
                question=cached_data["question"],
                sql_query=cached_data["llm_generated_sql"],
                db_result=db_result,
                chart_spec=chart_spec,
                human_readable_answer=cached_data["human_readable_answer"],
                quotation=cached_data["quotation"],
                response_id=request.response_id
            )

            # Return HTML response
            return HTMLResponse(content=html_content)

        # Normal flow (no response_id provided)
        # Generate unique response ID
        response_id = f"resp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Step 1: Get project details by ID
        logger.info(f"Step 1: Getting project details for project_id={request.project_id}")
        project_data = await get_project_by_id(request.project_id, db)

        if not project_data:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {request.project_id} not found. Please create it first."
            )

        project_id = project_data["id"]
        connection_profile = project_data["connection"]
        db_metadata = project_data["db_metadata"]

        logger.info(f"Found project: id={project_id}, name={project_data['name']}")

        # Step 2: Get database type and connector
        db_type = connection_profile.db_type
        dialect = "PostgreSQL" if db_type.lower() in ("postgres", "postgresql") else "Oracle"
        logger.info(f"Database type: {db_type}, SQL dialect: {dialect}")

        # Step 3: Generate SQL from question using LLM
        logger.info(f"Step 2: Generating SQL from question using LLM")
        llm_generated_sql = await generate_sql_from_question(
            question=request.question,
            db_metadata=db_metadata,
            dialect=dialect
        )
        logger.info(f"Generated SQL (before table name fix): {llm_generated_sql}")

        # Step 3.5: Fix LLM table name hallucination
        # LLM sometimes uses generic names (e.g., CUSTOMERS) instead of hash-suffixed names (e.g., CUSTOMERS_59C96545)
        # Build mapping from generic names to actual table names
        import re
        table_name_mapping = {}
        for table_item in db_metadata:
            # db_metadata can be a list of dicts or TableSchema objects
            if isinstance(table_item, dict):
                actual_name = table_item.get("name", "")
            elif hasattr(table_item, 'name'):
                # TableSchema object
                actual_name = table_item.name
            else:
                actual_name = str(table_item)

            if actual_name:
                # Extract base name by removing hash suffix (everything after last underscore followed by hex)
                # CUSTOMERS_59C96545 -> CUSTOMERS
                # EMPLOYEES_WITH_NORMAL_HEADINGS_07A68017 -> EMPLOYEES_WITH_NORMAL_HEADINGS
                base_name = re.sub(r'_[A-F0-9]{8}$', '', actual_name, flags=re.IGNORECASE)
                if base_name != actual_name:  # Only add if there was a hash suffix
                    table_name_mapping[base_name.upper()] = actual_name

        # Replace generic table names with actual names in SQL
        sql_query = llm_generated_sql
        for generic_name, actual_name in table_name_mapping.items():
            # Match table name in FROM, JOIN clauses (case-insensitive, word boundary)
            # Replace: FROM CUSTOMERS -> FROM "CUSTOMERS_59C96545"
            # Replace: JOIN EMPLOYEES -> JOIN "EMPLOYEES_WITH_NORMAL_HEADINGS_07A68017"
            sql_query = re.sub(
                rf'\bFROM\s+{generic_name}\b',
                f'FROM "{actual_name}"',
                sql_query,
                flags=re.IGNORECASE
            )
            sql_query = re.sub(
                rf'\bJOIN\s+{generic_name}\b',
                f'JOIN "{actual_name}"',
                sql_query,
                flags=re.IGNORECASE
            )
            sql_query = re.sub(
                rf'\bUPDATE\s+{generic_name}\b',
                f'UPDATE "{actual_name}"',
                sql_query,
                flags=re.IGNORECASE
            )
            sql_query = re.sub(
                rf'\bINTO\s+{generic_name}\b',
                f'INTO "{actual_name}"',
                sql_query,
                flags=re.IGNORECASE
            )

        llm_generated_sql = sql_query
        logger.info(f"Generated SQL (after table name fix): {llm_generated_sql}")

        # Step 4: Execute SQL on database
        logger.info(f"Step 3: Executing SQL on database")
        connector = get_connector(db_type)
        connection = connector.get_connection(connection_profile)
        cursor = connection.cursor()

        # Clean SQL
        sql_query = llm_generated_sql.replace('\n', ' ').replace(';', '').strip()

        # Execute query with Unicode-safe error handling
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
        except Exception as e:
            # Convert error message to ASCII-safe string (Oracle errors contain Arabic characters)
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            logger.error(f"Error in execute_query: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute query: {error_msg}"
            )
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Convert to list of dicts
        db_result = []
        for row in rows:
            row_dict = {}
            for idx, col_name in enumerate(columns):
                value = row[idx]
                # Convert to JSON-serializable types
                if hasattr(value, 'isoformat'):  # datetime
                    value = value.isoformat()
                elif isinstance(value, (bytes, bytearray)):
                    value = value.decode('utf-8', errors='ignore')
                row_dict[col_name] = value
            db_result.append(row_dict)

        logger.info(f"Query returned {len(db_result)} rows")

        # Close connection
        cursor.close()
        connection.close()

        # Step 5: Extract query filter data from SQL
        logger.info(f"Step 4: Extracting query metadata")
        query_filter_data = extract_query_metadata(llm_generated_sql, columns)

        # Step 6: Generate statistics
        logger.info(f"Step 5: Generating statistics from results")
        statistics = generate_statistics(db_result, columns, query_filter_data)

        # Step 7: Generate human-readable answer using LLM
        logger.info(f"Step 6: Generating human-readable answer using LLM")
        human_readable_answer, quotation = await generate_human_readable_answer(
            question=request.question,
            sql_query=llm_generated_sql,
            db_result=db_result[:10],  # Send first 10 rows as sample
            statistics=statistics,
            db_metadata=db_metadata
        )

        # Step 8: Build metadata
        logger.info(f"Step 7: Building metadata")
        response_metadata = {
            "source_tables": extract_table_names(llm_generated_sql),
            "generated_at": datetime.now().isoformat(),
            "llm_model": "gpt-5-data-analyst",
            "database_type": db_type,
            "total_rows_returned": len(db_result)
        }

        # Step 9: Save response to database
        logger.info(f"Step 8: Saving response to database")
        await save_query_response(
            response_id=response_id,
            project_id=project_id,
            question=request.question,
            sql_query=llm_generated_sql,
            query_filter_data=query_filter_data,
            human_readable_answer=human_readable_answer,
            quotation=quotation,
            metadata=response_metadata,
            db=db
        )

        # Step 10: Build final response
        logger.info(f"Step 9: Building final response")
        response = ExecuteQueryResponse(
            response_id=response_id,
            question=request.question,
            llm_generated_sql=llm_generated_sql,
            query_filter_data=query_filter_data,
            db_result=db_result,
            statistics=statistics,
            human_readable_answer=human_readable_answer,
            quotation=quotation,
            metadata=response_metadata
        )

        logger.info(f"Execute query completed successfully: {response_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in execute_query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute query: {str(e)}"
        )


def extract_query_metadata(sql_query: str, columns: List[str]) -> QueryFilterData:
    """
    Extract metadata from SQL query (GROUP BY, aggregations, etc.)

    Args:
        sql_query: SQL query string
        columns: Column names from result

    Returns:
        QueryFilterData with extracted metadata
    """
    import re

    sql_upper = sql_query.upper()

    # Extract GROUP BY columns
    group_by = []
    group_by_match = re.search(r'GROUP\s+BY\s+([\w\s,._]+?)(?:ORDER|HAVING|$)', sql_upper)
    if group_by_match:
        group_by_str = group_by_match.group(1)
        group_by = [col.strip().split('.')[-1] for col in group_by_str.split(',')]

    # Extract metrics (aggregations like SUM, COUNT, AVG)
    metrics = []
    for agg in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']:
        if agg in sql_upper:
            # Find columns with this aggregation
            pattern = f'{agg}\\s*\\(([^)]+)\\)'
            matches = re.findall(pattern, sql_upper)
            for match in matches:
                col_name = match.strip().split('.')[-1]
                metrics.append(f"{agg}({col_name})")

    # Extract time period filters
    time_period = None
    if 'SYSDATE' in sql_upper or 'CURRENT_DATE' in sql_upper:
        if 'ADD_MONTHS' in sql_upper or 'INTERVAL' in sql_upper:
            # Try to extract month count
            month_match = re.search(r'-(\d+)', sql_upper)
            if month_match:
                months = month_match.group(1)
                time_period = f"last_{months}_months"

    # Extract WHERE filters
    filters = {}
    where_match = re.search(r'WHERE\s+(.+?)(?:GROUP|ORDER|$)', sql_upper)
    if where_match:
        where_clause = where_match.group(1).strip()
        # Simple filter extraction (can be enhanced)
        filters['where_clause'] = where_clause

    return QueryFilterData(
        time_period=time_period,
        group_by=group_by if group_by else None,
        metrics=metrics if metrics else None,
        filters=filters if filters else None
    )


def generate_statistics(db_result: List[Dict[str, Any]], columns: List[str], query_filter_data: QueryFilterData) -> Statistics:
    """
    Generate comprehensive statistics from query results.

    Args:
        db_result: Query results as list of dicts
        columns: Column names
        query_filter_data: Query metadata

    Returns:
        Statistics object with computed metrics
    """
    if not db_result:
        return Statistics(
            total_rows=0,
            total_categories=0,
            grand_total=0,
            additional_stats={"note": "No data returned from query"}
        )

    total_rows = len(db_result)

    # Find numeric columns for aggregation
    numeric_cols = []
    for col in columns:
        if db_result and col in db_result[0]:
            val = db_result[0][col]
            if isinstance(val, (int, float)):
                numeric_cols.append(col)

    # Find category columns (non-numeric)
    category_cols = [col for col in columns if col not in numeric_cols]

    # Calculate statistics
    total_categories = None
    grand_total = None
    highest_category = None
    lowest_category = None
    average_per_category = None
    additional_stats = {}

    # If we have group by columns, calculate category-based stats
    if query_filter_data.group_by and category_cols:
        category_col = category_cols[0]  # Use first category column
        total_categories = len(db_result)

        # If we have numeric column, calculate totals
        if numeric_cols:
            value_col = numeric_cols[0]  # Use first numeric column

            # Calculate grand total
            grand_total = sum(row.get(value_col, 0) for row in db_result if isinstance(row.get(value_col), (int, float)))

            # Find highest and lowest
            sorted_results = sorted(db_result, key=lambda x: x.get(value_col, 0) if isinstance(x.get(value_col), (int, float)) else 0, reverse=True)
            if sorted_results:
                highest = sorted_results[0]
                lowest = sorted_results[-1]

                highest_category = {
                    "name": str(highest.get(category_col, "Unknown")),
                    "value": highest.get(value_col, 0)
                }
                lowest_category = {
                    "name": str(lowest.get(category_col, "Unknown")),
                    "value": lowest.get(value_col, 0)
                }

                # Calculate average
                if total_categories > 0:
                    average_per_category = grand_total / total_categories

    # Additional stats
    additional_stats = {
        "numeric_columns": numeric_cols,
        "category_columns": category_cols,
        "sample_row": db_result[0] if db_result else None
    }

    return Statistics(
        total_rows=total_rows,
        total_categories=total_categories,
        grand_total=grand_total,
        highest_category=highest_category,
        lowest_category=lowest_category,
        average_per_category=average_per_category,
        additional_stats=additional_stats
    )


async def generate_human_readable_answer(
    question: str,
    sql_query: str,
    db_result: List[Dict[str, Any]],
    statistics: Statistics,
    db_metadata: list
) -> tuple[str, str]:
    """
    Generate human-readable answer and quotation using LLM.

    Args:
        question: Original question
        sql_query: Generated SQL
        db_result: Sample query results
        statistics: Computed statistics
        db_metadata: Database metadata

    Returns:
        Tuple of (human_readable_answer, quotation)
    """
    from llm.ChatModel import ChatModel
    from llm_config.llm_config_manager import get_llm_config

    try:
        # Initialize LLM
        llm_config = get_llm_config("sql_generation")
        chat_model = ChatModel(
            api_url=llm_config.base_url,
            model=f'{llm_config.provider}/{llm_config.model}'
        )

        # Build prompt for human-readable answer
        prompt = f"""You are a data analyst. Based on the following information, provide a human-readable answer and an insightful quotation.

Question: {question}

SQL Query:
{sql_query}

Sample Results (first 10 rows):
{json.dumps(db_result, indent=2)}

Statistics:
- Total Rows: {statistics.total_rows}
- Total Categories: {statistics.total_categories}
- Grand Total: {statistics.grand_total}
- Highest: {json.dumps(statistics.highest_category) if statistics.highest_category else 'N/A'}
- Lowest: {json.dumps(statistics.lowest_category) if statistics.lowest_category else 'N/A'}
- Average per Category: {statistics.average_per_category}

Provide your response in the following JSON format:
{{
    "human_readable_answer": "A clear, concise answer to the question with key insights and specific numbers.",
    "quotation": "A brief, impactful quote summarizing the main finding."
}}

Focus on:
1. Answering the original question directly
2. Highlighting key numbers and trends
3. Making it easy to understand for non-technical users
4. Being specific with actual values from the data
"""

        # Generate answer
        logger.info("Calling LLM to generate human-readable answer...")
        llm_response = chat_model.infer_llm(user_prompt=prompt, temperature=0.3)

        # Parse JSON response
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in llm_response:
                llm_response = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                llm_response = llm_response.split("```")[1].strip()

            response_data = json.loads(llm_response)
            human_readable_answer = response_data.get("human_readable_answer", "Analysis complete.")
            quotation = response_data.get("quotation", "Insights generated from data.")
        except:
            # Fallback if JSON parsing fails
            human_readable_answer = llm_response
            quotation = "Data analysis completed successfully."

        return human_readable_answer, quotation

    except Exception as e:
        logger.error(f"Error generating human-readable answer: {str(e)}")
        # Return fallback response
        return (
            f"Query executed successfully and returned {statistics.total_rows} rows of data.",
            "Data retrieved successfully."
        )


async def save_query_response(
    response_id: str,
    project_id: int,
    question: str,
    sql_query: str,
    query_filter_data: QueryFilterData,
    human_readable_answer: str,
    quotation: str,
    metadata: Dict[str, Any],
    db: AsyncSession
):
    """
    Save query response to database table.

    Args:
        response_id: Unique response ID
        project_id: Project ID
        question: Original question
        sql_query: Generated SQL
        query_filter_data: Query metadata
        human_readable_answer: LLM-generated answer
        quotation: Brief summary quote
        metadata: Additional metadata
        db: Database session
    """
    try:
        from db.response_logs.models import ResponseLogsModel

        # Create new response log entry
        response_log = ResponseLogsModel(
            response_id=response_id,
            project_id=str(project_id),
            llm_generated_sql=sql_query,
            question=question,
            query_filter_data=json.dumps(query_filter_data.dict()),  # Convert to JSON string
            human_readable_answer=human_readable_answer,
            response_metadata=json.dumps(metadata),  # Convert to JSON string
            quotation=quotation
        )

        # Add to database
        db.add(response_log)
        await db.commit()
        await db.refresh(response_log)

        logger.info(f"Saved query response to database: {response_id}")

    except Exception as e:
        logger.warning(f"Failed to save query response to database: {str(e)}")
        await db.rollback()
        # Don't fail the request if logging fails


async def get_cached_response(
    project_id: int,
    response_id: str,
    db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Fetch cached response from database.

    Args:
        project_id: Project ID
        response_id: Response ID to fetch
        db: Database session

    Returns:
        Dictionary with cached response data or None if not found
    """
    try:
        from db.response_logs.models import ResponseLogsModel
        from sqlalchemy import select

        # Query database for cached response
        stmt = select(ResponseLogsModel).where(
            ResponseLogsModel.project_id == str(project_id),
            ResponseLogsModel.response_id == response_id
        )
        result = await db.execute(stmt)
        response_log = result.scalar_one_or_none()

        if not response_log:
            return None

        # Parse JSON strings back to objects
        query_filter_data = json.loads(response_log.query_filter_data) if response_log.query_filter_data else {}
        metadata = json.loads(response_log.response_metadata) if response_log.response_metadata else {}

        return {
            "response_id": response_log.response_id,
            "project_id": int(response_log.project_id),
            "llm_generated_sql": response_log.llm_generated_sql,
            "question": response_log.question,
            "query_filter_data": query_filter_data,
            "human_readable_answer": response_log.human_readable_answer,
            "metadata": metadata,
            "quotation": response_log.quotation
        }

    except Exception as e:
        logger.error(f"Error fetching cached response: {str(e)}")
        return None


async def call_chart_spec_endpoint(
    question: str,
    table_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Call the /chart-spec endpoint to get chart configuration.

    Args:
        question: The user's question
        table_data: Dictionary with columns and rows

    Returns:
        Chart specification from LLM
    """
    try:
        import httpx

        payload = {
            "message": question,
            "table": table_data
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(CHART_SPEC_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Error calling chart-spec endpoint: {str(e)}")
        # Return default chart spec
        return {
            "xAxis": table_data["columns"][0] if table_data["columns"] else "x",
            "yAxis": [table_data["columns"][1]] if len(table_data["columns"]) > 1 else ["y"],
            "chartTypes": ["bar", "line", "pie", "table"],
            "title": "Data Visualization"
        }


def generate_interactive_html(
    question: str,
    sql_query: str,
    db_result: List[Dict[str, Any]],
    chart_spec: Dict[str, Any],
    human_readable_answer: str,
    quotation: str,
    response_id: str
) -> str:
    """
    Generate interactive HTML with chart visualization.

    Args:
        question: User's question
        sql_query: Generated SQL query
        db_result: Query results
        chart_spec: Chart specification from LLM
        human_readable_answer: Human-readable answer
        quotation: Quote/summary
        response_id: Response ID

    Returns:
        HTML string with interactive charts
    """
    # Extract columns and convert data for JavaScript
    columns = list(db_result[0].keys()) if db_result else []
    rows_data = [[str(row.get(col, "")) for col in columns] for row in db_result]

    # Convert to JSON for embedding in HTML
    columns_json = json.dumps(columns)
    rows_json = json.dumps(rows_data)
    chart_spec_json = json.dumps(chart_spec)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Query Results - {response_id}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .response-id {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .controls {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .control-group {{
            display: flex;
            flex-direction: column;
        }}
        label {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #555;
            font-size: 14px;
        }}
        select {{
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }}
        select:hover {{
            border-color: #667eea;
        }}
        select:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        select[multiple] {{
            height: 120px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 20px;
            padding: 20px;
            background: white;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }}
        .answer-box {{
            padding: 20px;
            background: #f0f7ff;
            border-left: 4px solid #667eea;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .answer-box p {{
            line-height: 1.6;
            color: #333;
        }}
        .quotation {{
            padding: 20px;
            background: #fff9e6;
            border-left: 4px solid #ffa500;
            border-radius: 8px;
            font-style: italic;
            margin-bottom: 20px;
        }}
        .sql-box {{
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .table-wrapper {{
            max-height: 500px;
            overflow-y: auto;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        .hint {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Query Results Visualization</h1>
            <div class="response-id">Response ID: {response_id}</div>
        </div>

        <div class="content">
            <!-- Question Section -->
            <div class="section">
                <div class="section-title">❓ Question</div>
                <div class="answer-box">
                    <p><strong>{question}</strong></p>
                </div>
            </div>

            <!-- Answer Section -->
            <div class="section">
                <div class="section-title">💡 Analysis</div>
                <div class="answer-box">
                    <p>{human_readable_answer}</p>
                </div>
            </div>

            <!-- Quotation Section -->
            <div class="section">
                <div class="section-title">📝 Summary</div>
                <div class="quotation">
                    "{quotation}"
                </div>
            </div>

            <!-- Chart Controls -->
            <div class="section">
                <div class="section-title">🎨 Visualization Controls</div>
                <div class="controls">
                    <div class="control-group">
                        <label for="chartType">Chart Type</label>
                        <select id="chartType" onchange="updateChart()">
                            <option value="bar">Bar Chart</option>
                            <option value="line">Line Chart</option>
                            <option value="pie">Pie Chart</option>
                            <option value="table">Data Table</option>
                        </select>
                    </div>

                    <div class="control-group">
                        <label for="xAxis">X-Axis (Multiple Selection)</label>
                        <select id="xAxis" multiple onchange="updateChart()">
                            <!-- Populated by JavaScript -->
                        </select>
                        <div class="hint">Hold Ctrl/Cmd to select multiple</div>
                    </div>

                    <div class="control-group">
                        <label for="yAxis">Y-Axis (Multiple Selection)</label>
                        <select id="yAxis" multiple onchange="updateChart()">
                            <!-- Populated by JavaScript -->
                        </select>
                        <div class="hint">Hold Ctrl/Cmd to select multiple</div>
                    </div>
                </div>
            </div>

            <!-- Chart Display -->
            <div class="section">
                <div class="section-title">📈 Chart</div>
                <div id="chartDisplay" class="chart-container">
                    <canvas id="myChart"></canvas>
                </div>
            </div>

            <!-- Table Display -->
            <div class="section" id="tableSection" style="display: none;">
                <div class="section-title">📋 Data Table</div>
                <div class="table-wrapper">
                    <table id="dataTable">
                        <thead id="tableHead"></thead>
                        <tbody id="tableBody"></tbody>
                    </table>
                </div>
            </div>

            <!-- SQL Query Section -->
            <div class="section">
                <div class="section-title">🔍 Generated SQL Query</div>
                <div class="sql-box">{sql_query}</div>
            </div>
        </div>
    </div>

    <script>
        // Data from backend
        const columns = {columns_json};
        const rows = {rows_json};
        const chartSpec = {chart_spec_json};

        let currentChart = null;

        // Initialize dropdowns
        function initializeDropdowns() {{
            const xAxisSelect = document.getElementById('xAxis');
            const yAxisSelect = document.getElementById('yAxis');

            // Populate X-Axis dropdown
            columns.forEach((col, idx) => {{
                const option = document.createElement('option');
                option.value = col;
                option.textContent = col;
                // Pre-select based on chart spec
                if (chartSpec.xAxis && chartSpec.xAxis === col) {{
                    option.selected = true;
                }}
                xAxisSelect.appendChild(option);
            }});

            // Populate Y-Axis dropdown (numeric columns only)
            columns.forEach((col, idx) => {{
                // Check if column has numeric values
                const isNumeric = rows.every(row => {{
                    const val = row[idx];
                    return val === '' || !isNaN(parseFloat(val));
                }});

                const option = document.createElement('option');
                option.value = col;
                option.textContent = col + (isNumeric ? ' (numeric)' : '');

                // Pre-select based on chart spec
                if (chartSpec.yAxis && chartSpec.yAxis.includes(col)) {{
                    option.selected = true;
                }}

                yAxisSelect.appendChild(option);
            }});
        }}

        // Prepare chart data
        function prepareChartData() {{
            const xAxisSelect = document.getElementById('xAxis');
            const yAxisSelect = document.getElementById('yAxis');

            const selectedXCols = Array.from(xAxisSelect.selectedOptions).map(opt => opt.value);
            const selectedYCols = Array.from(yAxisSelect.selectedOptions).map(opt => opt.value);

            if (selectedXCols.length === 0 || selectedYCols.length === 0) {{
                return null;
            }}

            // Get column indices
            const xIndices = selectedXCols.map(col => columns.indexOf(col));
            const yIndices = selectedYCols.map(col => columns.indexOf(col));

            // Create composite labels for X-axis
            const labels = rows.map(row => {{
                return selectedXCols.map((col, idx) => row[xIndices[idx]]).join(' - ');
            }});

            // Prepare datasets for each Y column
            const datasets = selectedYCols.map((yCol, idx) => {{
                const data = rows.map(row => parseFloat(row[yIndices[idx]]) || 0);
                const colors = [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)'
                ];

                return {{
                    label: yCol,
                    data: data,
                    backgroundColor: colors[idx % colors.length],
                    borderColor: colors[idx % colors.length].replace('0.8', '1'),
                    borderWidth: 2
                }};
            }});

            return {{ labels, datasets }};
        }}

        // Update chart based on selections
        function updateChart() {{
            const chartType = document.getElementById('chartType').value;
            const tableSection = document.getElementById('tableSection');
            const chartDisplay = document.getElementById('chartDisplay');

            if (chartType === 'table') {{
                // Show table, hide chart
                tableSection.style.display = 'block';
                chartDisplay.style.display = 'none';
                renderTable();
            }} else {{
                // Show chart, hide table
                tableSection.style.display = 'none';
                chartDisplay.style.display = 'block';
                renderChart(chartType);
            }}
        }}

        // Render chart
        function renderChart(chartType) {{
            const chartData = prepareChartData();
            if (!chartData) {{
                return;
            }}

            const ctx = document.getElementById('myChart').getContext('2d');

            // Destroy existing chart
            if (currentChart) {{
                currentChart.destroy();
            }}

            // Create new chart
            currentChart = new Chart(ctx, {{
                type: chartType,
                data: chartData,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top'
                        }},
                        title: {{
                            display: true,
                            text: chartSpec.title || 'Data Visualization',
                            font: {{
                                size: 18
                            }}
                        }}
                    }},
                    scales: chartType !== 'pie' ? {{
                        y: {{
                            beginAtZero: true
                        }}
                    }} : {{}}
                }}
            }});
        }}

        // Render table
        function renderTable() {{
            const xAxisSelect = document.getElementById('xAxis');
            const yAxisSelect = document.getElementById('yAxis');

            const selectedXCols = Array.from(xAxisSelect.selectedOptions).map(opt => opt.value);
            const selectedYCols = Array.from(yAxisSelect.selectedOptions).map(opt => opt.value);

            const displayCols = [...selectedXCols, ...selectedYCols];
            const displayIndices = displayCols.map(col => columns.indexOf(col));

            // Create table header
            const tableHead = document.getElementById('tableHead');
            tableHead.innerHTML = '';
            const headerRow = document.createElement('tr');
            displayCols.forEach(col => {{
                const th = document.createElement('th');
                th.textContent = col;
                headerRow.appendChild(th);
            }});
            tableHead.appendChild(headerRow);

            // Create table body
            const tableBody = document.getElementById('tableBody');
            tableBody.innerHTML = '';
            rows.forEach(row => {{
                const tr = document.createElement('tr');
                displayIndices.forEach(idx => {{
                    const td = document.createElement('td');
                    td.textContent = row[idx];
                    tr.appendChild(td);
                }});
                tableBody.appendChild(tr);
            }});
        }}

        // Initialize on page load
        initializeDropdowns();
        updateChart();
    </script>
</body>
</html>
    """

    return html_template


def extract_table_names(sql_query: str) -> List[str]:
    """
    Extract table names from SQL query.

    Args:
        sql_query: SQL query string

    Returns:
        List of table names
    """
    import re

    # Simple regex to extract table names after FROM and JOIN
    pattern = r'(?:FROM|JOIN)\s+(\w+)'
    matches = re.findall(pattern, sql_query, re.IGNORECASE)

    # Remove duplicates and return
    return list(set(matches))


# ================== NEW /graph ENDPOINT ==================

class GraphRequest(BaseModel):
    """Request for generating graph from cached response"""
    project_id: int
    response_id: str


class GraphResponse(BaseModel):
    """Response with graph data and configuration"""
    id: str
    title: str
    type: str
    data: List[Dict[str, Any]]
    config: Dict[str, Any]
    size: str = "large"
    position: Dict[str, int] = {"row": 0, "col": 0}


@router.post("/graph", response_model=GraphResponse)
async def generate_graph(
    request: GraphRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate graph data from cached response.

    This endpoint:
    1. Fetches cached response from response_logs table
    2. Executes the SQL query on the datasource
    3. Calls chart-spec endpoint to get chart configuration
    4. Returns formatted graph response

    Request:
    {
        "project_id": 17,
        "response_id": "resp_20251022_144327_ea13ce"
    }

    Response:
    {
        "id": "a1b2c3d4",
        "title": "Chart for customers.csv",
        "type": "bar",
        "data": [
            {"City": "Dubai", "Orders": 120, "Revenue": 85000},
            {"City": "Abu Dhabi", "Orders": 90, "Revenue": 65000}
        ],
        "config": {
            "xAxis": "City",
            "yAxis": ["Orders", "Revenue"],
            "colors": ["#3b82f6", "#ef4444"]
        },
        "size": "large",
        "position": {"row": 0, "col": 0}
    }
    """
    try:
        logger.info(f"Generate graph request: project_id={request.project_id}, response_id={request.response_id}")

        # Step 1: Get cached response from database
        logger.info("Step 1: Fetching cached response from database")
        cached_data = await get_cached_response(
            project_id=request.project_id,
            response_id=request.response_id,
            db=db
        )

        if not cached_data:
            raise HTTPException(
                status_code=404,
                detail=f"Cached response not found: response_id={request.response_id}, project_id={request.project_id}"
            )

        logger.info(f"Cached response found for response_id: {request.response_id}")

        # Step 2: Get project details
        logger.info(f"Step 2: Getting project details for project_id={request.project_id}")
        project_data = await get_project_by_id(request.project_id, db)

        if not project_data:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {request.project_id} not found."
            )

        connection_profile = project_data["connection"]
        db_type = connection_profile.db_type

        # Step 3: Execute SQL query on datasource
        logger.info(f"Step 3: Executing SQL query on {db_type} database")
        llm_generated_sql = cached_data["llm_generated_sql"]

        connector = get_connector(db_type)
        connection = connector.get_connection(connection_profile)
        cursor = connection.cursor()

        # Clean SQL
        sql_query = llm_generated_sql.replace('\n', ' ').replace(';', '').strip()

        # Execute query
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Convert to list of dicts
        db_result = []
        for row in rows:
            row_dict = {}
            for idx, col_name in enumerate(columns):
                value = row[idx]
                # Convert to JSON-serializable types
                if hasattr(value, 'isoformat'):  # datetime
                    value = value.isoformat()
                elif isinstance(value, (bytes, bytearray)):
                    value = value.decode('utf-8', errors='ignore')
                row_dict[col_name] = value
            db_result.append(row_dict)

        logger.info(f"Query returned {len(db_result)} rows")

        # Close connection
        cursor.close()
        connection.close()

        # Step 4: Prepare data for chart-spec endpoint
        logger.info("Step 4: Preparing data for chart-spec endpoint")
        rows_data = [[str(row.get(col, "")) for col in columns] for row in db_result]

        table_data = {
            "columns": columns,
            "rows": rows_data
        }

        # Step 5: Call chart-spec endpoint
        logger.info("Step 5: Calling chart-spec endpoint")
        chart_spec = await call_chart_spec_endpoint(
            question=cached_data["question"],
            table_data=table_data
        )

        logger.info(f"Chart spec received: {chart_spec}")

        # Step 6: Build graph response
        logger.info("Step 6: Building graph response")

        # Separate numeric and non-numeric columns
        numeric_columns = []
        non_numeric_columns = []

        if db_result:
            first_row = db_result[0]
            for col in columns:
                value = first_row.get(col)
                # Check if value is numeric (int, float, or numeric string)
                try:
                    if value is not None:
                        if isinstance(value, (int, float)):
                            numeric_columns.append(col)
                        elif isinstance(value, str):
                            # Try to convert to float
                            float(value)
                            numeric_columns.append(col)
                        else:
                            non_numeric_columns.append(col)
                    else:
                        non_numeric_columns.append(col)
                except (ValueError, TypeError):
                    non_numeric_columns.append(col)

        # Ensure at least one column in each category
        if not numeric_columns and columns:
            numeric_columns = [columns[-1]]  # Use last column as numeric
        if not non_numeric_columns and columns:
            non_numeric_columns = [columns[0]]  # Use first column as non-numeric

        # Extract chart configuration from chart_spec
        chart_type = chart_spec.get("chartType", "bar")

        # Override with intelligent axis assignment
        # xAxis should be non-numeric (categorical) - use all non-numeric columns
        # yAxis should be numeric (values) - use all numeric columns
        x_fields = non_numeric_columns if non_numeric_columns else [columns[0]]
        y_fields = numeric_columns if numeric_columns else [columns[-1]]

        logger.info(f"Axis assignment - xAxis: {x_fields}, yAxis: {y_fields}")
        logger.info(f"Numeric columns detected: {numeric_columns}")
        logger.info(f"Non-numeric columns detected: {non_numeric_columns}")

        # Color palette - assign colors based on number of xAxis fields
        base_colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899",
                       "#06b6d4", "#f97316", "#14b8a6", "#a855f7", "#eab308", "#84cc16"]

        # Generate colors based on number of xAxis fields
        # Each xAxis field (dimension) gets its own color
        colors = []
        for i in range(len(x_fields)):
            colors.append(base_colors[i % len(base_colors)])

        logger.info(f"Generated {len(colors)} colors for {len(x_fields)} xAxis fields")

        # Build response
        graph_response = GraphResponse(
            id=str(uuid.uuid4())[:8],
            title=f"Chart for {cached_data.get('question', 'Query Result')}",
            type=chart_type,
            data=db_result,
            config={
                "xAxis": x_fields,
                "yAxis": y_fields,
                "colors": colors
            },
            size="large",
            position={"row": 0, "col": 0}
        )

        logger.info(f"Graph response generated successfully: id={graph_response.id}")
        return graph_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_graph: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate graph: {str(e)}"
        )
