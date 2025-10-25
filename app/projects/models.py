import json
import projects.utils as utils

from pydantic import BaseModel

class ConnectionProfile:
    db_type: str
    con_string: str
    database: str
    username: str
    password: str

    def __init__(self, db_type="", con_string="", database="", username="", password=""):
        self.db_type = db_type
        self.con_string = con_string
        self.database = database
        self.username = username
        self.password = password

class TableColumn:
    name: str
    description: str
    data_type: str
    is_null: bool = False
    is_unique: bool = False
    is_range: bool = False
    groupable: bool = False
    aggregation: list[str] = []

    def __init__(
        self,
        name: str = "",
        description: str = "",
        data_type: str = "",
        is_null: bool = False,
        is_unique: bool = False,
        is_range: bool = False,
        groupable: bool = False,
        aggregation: list[str] = None
    ):
        self.name = name
        self.description = description
        self.data_type = data_type
        self.is_null = is_null
        self.is_unique = is_unique
        self.is_range = is_range
        self.groupable = groupable
        self.aggregation = aggregation if aggregation is not None else []

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "is_null": self.is_null,
            "is_unique": self.is_unique,
            "is_range": self.is_range,
            "groupable": self.groupable,
            "aggregation": self.aggregation
        }

class ForeignKeyColumn:
    name: str
    referenced_table: str
    referenced_column: str

    def __init__(
        self,
        name: str = "",
        referenced_table: str = "",
        referenced_column: str = ""
    ):
        self.name = name
        self.referenced_table = referenced_table
        self.referenced_column = referenced_column

    def to_dict(self):
        return {
            "name": self.name,
            "referenced_table": self.referenced_table,
            "referenced_column": self.referenced_column
        }

class TableSchema:
    name: str
    description: str
    columns: list[TableColumn]
    foreign_keys: list[ForeignKeyColumn]

    def __init__(
        self,
        name: str = "",
        description: str = "",
        columns: list[TableColumn] = None,
        foreign_keys: list[ForeignKeyColumn] = None
    ):
        self.name = name
        self.description = description
        if columns and len(columns)>0 and type(columns[0]) is not TableColumn:
            self.columns = [TableColumn(**column) for column in columns] if columns is not None else []
        else:
            self.columns = columns

        if foreign_keys and len(foreign_keys)>0 and type(foreign_keys[0]) is not ForeignKeyColumn:
            self.foreign_keys = [ForeignKeyColumn(**key) for key in foreign_keys] if foreign_keys is not None else []
        else:
            self.foreign_keys = foreign_keys

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "columns": [col.to_dict() for col in self.columns] if self.columns else [],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys] if self.foreign_keys else []
        }

    def to_json(self):
        return json.dumps(self.to_dict())

class Project:
    id: int = -1
    name: str
    train_id: str = None
    connection: ConnectionProfile = None
    db_metadata: list[TableSchema] = None

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', -1)
        self.name = kwargs.get('name',"")
        self.train_id = kwargs.get('train_id', None)
        connection = kwargs.get('connection', None)
        if type(connection) is str:
            self.connection = ConnectionProfile(**json.loads(connection))
        else:
            self.connection = connection

        db_metadata = kwargs.get('db_metadata', None)
        if type(db_metadata) is str:
            metadata_dict = json.loads(db_metadata)
            self.db_metadata = [TableSchema(**table) for table in metadata_dict]
        else:
            self.db_metadata = db_metadata

    def to_dict(self):
        connection = utils.serialize(self.connection) if self.connection else None
        db_metadata = json.dumps([table.to_dict() for table in self.db_metadata]) if self.db_metadata else []
        return {
            "id": self.id,
            "name": self.name,
            "train_id": self.train_id,
            "connection": connection,
            "db_metadata": db_metadata
        }

    def from_db(db_projects):
        projects = [Project(**project) for project in db_projects]
        return projects
    
class ResultSet(BaseModel):
    columns: list[str] = []
    rows: list[list[str]] = []
    markdown: str = ""
    statistics: dict = {}
