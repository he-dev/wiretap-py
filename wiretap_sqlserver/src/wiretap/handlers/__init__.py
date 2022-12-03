import logging
import pyodbc
import json
import atexit
from datetime import datetime, date
from logging import Handler
from typing import Callable, Any, List, Optional


class SqlServerHandler(Handler):
    def __init__(self, connection_string: str, insert: str = "INSERT INTO log([timestamp], [scope], [status], [correlation], [extra], [comment]) VALUES (?, ?, ?, ?, ?, ?)"):
        super().__init__()
        self.connection_string = connection_string
        self.insert = insert
        self.db: Optional[pyodbc.Cursor] = None

        atexit.register(self._cleanup)

    def emit(self, record):
        self._connect()

        if record.exc_info:
            record.exc_text = logging.Formatter().formatException(record.exc_info)

        self.db.execute(
            self.insert,
            datetime.fromtimestamp(record.created),  # timestamp
            ".".join([record.module, record.funcName]),  # scope
            record.status if hasattr(record, "status") else None,  # status
            json.dumps(record.correlation, cls=_JsonDateTimeEncoder) if hasattr(record, "correlation") and record.correlation else None,  # correlation
            json.dumps(record.extra, cls=_JsonDateTimeEncoder) if hasattr(record, "extra") and record.extra else None,  # extra
            record.exc_text if record.exc_text else None,  # comment
        )
        self.db.commit()

    def _connect(self):
        if not self.db:
            connection = pyodbc.connect(self.connection_string)
            self.db = connection.cursor()

    def _cleanup(self):
        if self.db:
            self.db.connection.close()


class SqlServerOdbcConnectionString:

    @staticmethod
    def standard(server: str, database: str, username: str, password: str, driver_version: str = "17") -> str:
        return f"DRIVER={{ODBC Driver {driver_version} for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

    @staticmethod
    def trusted(server: str, database: str, driver_version: str = "17") -> str:
        return f"DRIVER={{ODBC Driver {driver_version} for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes"


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()
