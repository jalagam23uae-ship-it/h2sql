from typing import Any, Coroutine
from projects.models import ConnectionProfile, ResultSet

class DBConnector():
    connection:Any
    db_type: str

    def get_connection(self, con_profile: ConnectionProfile):
        pass

    def get_tables(self) -> list[str]:
        pass

    def get_columns(self, table_name) -> list[str]:
        pass

    def get_foreign_keys(self, table_name) -> list[str]:
        pass

    async def execute_query(self, query) -> Coroutine[Any, Any, tuple[ResultSet, None] | tuple[None, str]]:
        pass

    def get_text2sql_example(self) -> str:
        pass

    def get_query_validation_fix_example(self) -> str :
        pass

    def get_query_execution_fix_example(self) -> str:
        pass

    def get_query_rewrite_example(self) -> str:
        pass
