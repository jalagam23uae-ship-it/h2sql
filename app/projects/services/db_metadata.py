from projects.connectors import oracle
from projects.connectors import postgres
from projects.connectors.db_connector import DBConnector
from projects.models import ConnectionProfile, TableSchema

CONNECTOR_MAP = {
    "oracle": oracle.OracleConnector(),
    "postgres": postgres.PostgresConnector(),
    "postgresql": postgres.PostgresConnector()  # Support both naming conventions
}

def get_connector(db_type):
    connector = CONNECTOR_MAP.get(db_type)
    if not connector:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return connector

def get_db_metadata(conProfile: ConnectionProfile):
    connection = None
    metadata = []
    success = False
    connector:DBConnector = get_connector(conProfile.db_type)
    try:
        connection = connector.get_connection(conProfile)
        tables:list[str] = connector.get_tables()
        for table in tables:
            cols = connector.get_columns(table)
            keys = connector.get_foreign_keys(table)
            metadata.append(TableSchema(
                name=table,
                columns = [col for col in cols],
                foreign_keys = [key for key in keys]
            ))
        success=True
    except Exception as e:
        raise Exception("Connection failed: "+ str(e))
    finally:
        if connection:
            connection.close()
    return metadata, success