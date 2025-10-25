from ctypes import Array
import platform
import oracledb
from projects.connectors.db_connector import DBConnector
from projects.models import ConnectionProfile, ResultSet, TableSchema
from projects.models import TableColumn, ForeignKeyColumn
import asyncio
import pandas as pd
import re

from prompts.prompts import Prompts

prompts = Prompts()

class OracleConnector(DBConnector):
    def __init__(self):
        self.db_type = "oracle"

    def _get_connection(self, username, password, con_string):
        d = None                             # On Linux, no directory should be passed
        if platform.system() == "Windows":   # Windows
            d = r"C:\oracle\instantclient_23_9"
            oracledb.init_oracle_client(lib_dir=d)

        return oracledb.connect(user=username, password=password, dsn=con_string)

    def get_connection(self, con_profile: ConnectionProfile):
        self.connection = self._get_connection(
            con_profile.username, con_profile.password, con_profile.con_string)
        return self.connection

    def get_tables(self) -> list[str]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT table_name FROM user_tables")
        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name) -> list[str]:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT 
            column_name, 
            data_type, 
            nullable
            FROM 
            user_tab_columns 
            WHERE 
            table_name = :table_name
            """,
            {"table_name": table_name.upper()}
        )
        columns = []
        for row in cursor.fetchall():
            col_name, data_type, nullable = row

            # Check if column is unique (part of a unique constraint or primary key)
            cursor.execute(
                """
            SELECT COUNT(*) FROM user_cons_columns ucc
            JOIN user_constraints uc ON ucc.constraint_name = uc.constraint_name
            WHERE uc.table_name = :table_name
              AND ucc.column_name = :col_name
              AND uc.constraint_type IN ('U', 'P')
            """,
                {"table_name": table_name.upper(), "col_name": col_name}
            )
            is_col_unique = cursor.fetchone()[0] > 0

            # Determine if column is suitable for range queries (numeric or date types)
            is_col_range = data_type in (
                "NUMBER", "FLOAT", "DATE", "TIMESTAMP", "DECIMAL", "INTEGER"
            )

            # Determine if column is groupable (typically non-LOB types)
            groupable = data_type not in (
                "BLOB", "CLOB", "NCLOB", "LONG", "RAW", "LONG RAW"
            )

            # Suggest aggregation functions based on data type
            if data_type in ("NUMBER", "FLOAT", "DECIMAL", "INTEGER"):
                aggregation = ["SUM", "AVG", "MIN", "MAX", "COUNT"]
            elif data_type in ("DATE", "TIMESTAMP"):
                aggregation = ["MIN", "MAX", "COUNT"]
            else:
                aggregation = ["COUNT"]

            columns.append(
                TableColumn(
                    name=col_name,
                    data_type=data_type,
                    is_null=(nullable == "Y"),
                    is_unique=is_col_unique,
                    is_range=is_col_range,
                    groupable=groupable,
                    aggregation=aggregation
                )
            )
        return columns

    def get_foreign_keys(self, table_name) -> list[str]:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                a.column_name,
                c_pk.table_name AS referenced_table,
                b.column_name AS referenced_column
            FROM
                user_cons_columns a
                JOIN user_constraints c ON a.constraint_name = c.constraint_name
                JOIN user_constraints c_pk ON c.r_constraint_name = c_pk.constraint_name
                JOIN user_cons_columns b ON c_pk.constraint_name = b.constraint_name AND a.position = b.position
            WHERE
                c.constraint_type = 'R'
                AND a.table_name = :table_name
            """,
            {"table_name": table_name.upper()}
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
        loop = asyncio.get_running_loop()

        def run_query():
            try:
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns_data = [
                    desc[0] for desc in cursor.description] if cursor.description else []
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
                            if getattr(tbl, "name", None).upper() == table_name.upper():
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
                                    statistics[col]["sum"] = stats_row[i]
                                cursor2.close()

                else:
                    statistics = {}

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
            except oracledb.DatabaseError as e:
                error, = e.args
                return (None, str(error))
            except Exception as e:
                return (None, str(e))

        return await loop.run_in_executor(None, run_query)

    def get_text2sql_example(self) -> str:
        return prompts.get_prompt_by_key("oracle_text2sql_example")

    def get_query_validation_fix_example(self) -> str:
        return prompts.get_prompt_by_key("oracle_sql_validation_fix_example")

    def get_query_execution_fix_example(self) -> str:
        return prompts.get_prompt_by_key("oracle_sql_execution_fix_example")

    def get_query_rewrite_example(self) -> str:
        return prompts.get_prompt_by_key("oracle_query_rewrite_example")