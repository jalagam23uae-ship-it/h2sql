from ctypes import Array
import psycopg2
import psycopg2.extras
from projects.connectors.db_connector import DBConnector
from projects.models import ConnectionProfile, ResultSet, TableSchema
from projects.models import TableColumn, ForeignKeyColumn
import asyncio
import pandas as pd
import re

from prompts.prompts import Prompts

prompts = Prompts()

class PostgresConnector(DBConnector):
    def __init__(self):
        self.db_type = "postgres"

    def _get_connection(self, username, password, con_string, database):
        """
        Establish PostgreSQL connection.
        con_string format: host:port or just host
        """
        parts = con_string.split(":")
        host = parts[0]
        port = parts[1] if len(parts) > 1 else "5432"

        return psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )

    def get_connection(self, con_profile: ConnectionProfile):
        self.connection = self._get_connection(
            con_profile.username,
            con_profile.password,
            con_profile.con_string,
            con_profile.database
        )
        return self.connection

    def get_tables(self) -> list[str]:
        """Get all tables in the public schema"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name) -> list[str]:
        """Get column information for a table"""
        cursor = self.connection.cursor()

        # Get basic column information
        cursor.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM
                information_schema.columns
            WHERE
                table_schema = 'public'
                AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name.lower(),)
        )

        columns = []
        for row in cursor.fetchall():
            col_name, data_type, is_nullable = row

            # Check if column is unique (part of a unique constraint or primary key)
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.table_schema = 'public'
                    AND tc.table_name = %s
                    AND ccu.column_name = %s
                    AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
                """,
                (table_name.lower(), col_name)
            )
            is_col_unique = cursor.fetchone()[0] > 0

            # Determine if column is suitable for range queries (numeric or date types)
            is_col_range = data_type.upper() in (
                "INTEGER", "BIGINT", "SMALLINT", "NUMERIC", "DECIMAL", "REAL",
                "DOUBLE PRECISION", "SERIAL", "BIGSERIAL", "MONEY",
                "DATE", "TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE",
                "TIMESTAMP WITH TIME ZONE", "TIME"
            )

            # Determine if column is groupable (typically non-LOB types)
            groupable = data_type.upper() not in (
                "BYTEA", "TEXT", "JSON", "JSONB", "XML"
            )

            # Suggest aggregation functions based on data type
            if data_type.upper() in (
                "INTEGER", "BIGINT", "SMALLINT", "NUMERIC", "DECIMAL",
                "REAL", "DOUBLE PRECISION", "SERIAL", "BIGSERIAL", "MONEY"
            ):
                aggregation = ["SUM", "AVG", "MIN", "MAX", "COUNT"]
            elif data_type.upper() in (
                "DATE", "TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE",
                "TIMESTAMP WITH TIME ZONE", "TIME"
            ):
                aggregation = ["MIN", "MAX", "COUNT"]
            else:
                aggregation = ["COUNT"]

            columns.append(
                TableColumn(
                    name=col_name,
                    data_type=data_type.upper(),
                    is_null=(is_nullable == "YES"),
                    is_unique=is_col_unique,
                    is_range=is_col_range,
                    groupable=groupable,
                    aggregation=aggregation
                )
            )
        return columns

    def get_foreign_keys(self, table_name) -> list[str]:
        """Get foreign key relationships for a table"""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name = %s
            """,
            (table_name.lower(),)
        )
        return [
            ForeignKeyColumn(
                name=row[0],
                referenced_table=row[1],
                referenced_column=row[2]
            )
            for row in cursor.fetchall()
        ]

    async def execute_query(self, query, metadata: Array[TableSchema], result_limit=10):
        """Execute a SQL query asynchronously"""
        loop = asyncio.get_running_loop()

        def run_query():
            try:
                cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(query)

                # Get column names
                columns_data = [desc[0] for desc in cursor.description] if cursor.description else []

                # Fetch rows based on limit
                if result_limit > 0:
                    rows_data = cursor.fetchmany(result_limit)
                else:
                    rows_data = cursor.fetchall()

                # Fetch statistics for numeric/date columns
                statistics = {}
                if columns_data:
                    table_name = None
                    # Try to extract table name from the query if it's a simple SELECT * FROM table
                    match = re.match(
                        r"\s*SELECT\s+\*\s+FROM\s+([A-Za-z0-9_]+)", query, re.IGNORECASE)
                    if match:
                        table_name = match.group(1)

                    if table_name:
                        # Iterate through metadata to find the matching table schema
                        table_schema = None
                        for tbl in metadata:
                            if getattr(tbl, "name", None).lower() == table_name.lower():
                                table_schema = tbl
                                break

                        if table_schema:
                            # Get numerical/date columns from the table schema
                            min_max_cols = [
                                col.name for col in getattr(table_schema, "columns", [])
                                if col.aggregation and any(
                                    agg.upper() in ('MIN', 'MAX') for agg in col.aggregation
                                )
                            ]

                            avg_cols = [
                                col.name for col in getattr(table_schema, "columns", [])
                                if col.aggregation and any(
                                    agg.upper() in ('AVG') for agg in col.aggregation
                                )
                            ]

                            sum_cols = [
                                col.name for col in getattr(table_schema, "columns", [])
                                if col.aggregation and any(
                                    agg.upper() in ('SUM') for agg in col.aggregation
                                )
                            ]

                            if min_max_cols:
                                stats_query = "SELECT " + ", ".join(
                                    f"MIN({col}), MAX({col})" for col in min_max_cols
                                ) + f" FROM {table_name}"
                                cursor2 = self.connection.cursor()
                                cursor2.execute(stats_query)
                                stats_row = cursor2.fetchone()

                                for i, col in enumerate(min_max_cols):
                                    statistics[col] = {
                                        "min": stats_row[i*2],
                                        "max": stats_row[(i*2) + 1]
                                    }
                                cursor2.close()

                            if avg_cols:
                                avg_query = "SELECT " + ", ".join(
                                    f"AVG({col})" for col in avg_cols
                                ) + f" FROM {table_name}"
                                cursor2 = self.connection.cursor()
                                cursor2.execute(avg_query)
                                stats_row = cursor2.fetchone()

                                for i, col in enumerate(avg_cols):
                                    if col not in statistics:
                                        statistics[col] = {}
                                    statistics[col]["avg"] = stats_row[i]
                                cursor2.close()

                            if sum_cols:
                                sum_query = "SELECT " + ", ".join(
                                    f"SUM({col})" for col in sum_cols
                                ) + f" FROM {table_name}"
                                cursor2 = self.connection.cursor()
                                cursor2.execute(sum_query)
                                stats_row = cursor2.fetchone()

                                for i, col in enumerate(sum_cols):
                                    if col not in statistics:
                                        statistics[col] = {}
                                    statistics[col]["sum"] = stats_row[i]
                                cursor2.close()

                # Store result in a DataFrame
                df = pd.DataFrame(rows_data, columns=columns_data)

                # Convert DataFrame to list of lists (as strings)
                rows = df.astype(str).values.tolist()

                return (
                    ResultSet(
                        columns=columns_data,
                        rows=rows,
                        markdown=df.to_markdown(index=None),
                        statistics=statistics
                    ),
                    None
                )
            except psycopg2.DatabaseError as e:
                return (None, str(e))
            except Exception as e:
                return (None, str(e))

        return await loop.run_in_executor(None, run_query)

    def get_text2sql_example(self) -> str:
        """Get PostgreSQL-specific text2sql example"""
        return prompts.get_prompt_by_key("postgres_text2sql_example")

    def get_query_validation_fix_example(self) -> str:
        """Get PostgreSQL-specific validation fix example"""
        return prompts.get_prompt_by_key("postgres_sql_validation_fix_example")

    def get_query_execution_fix_example(self) -> str:
        """Get PostgreSQL-specific execution fix example"""
        return prompts.get_prompt_by_key("postgres_sql_execution_fix_example")

    def get_query_rewrite_example(self) -> str:
        """Get PostgreSQL-specific query rewrite example"""
        return prompts.get_prompt_by_key("postgres_query_rewrite_example")
