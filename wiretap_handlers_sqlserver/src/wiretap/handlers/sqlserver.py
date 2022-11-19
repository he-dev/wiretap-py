import logging
# import threading
import pyodbc
import json
import atexit
from datetime import datetime
from logging import Handler
from typing import Callable, Any, List


# lock = threading.RLock()


class SqlServerHandler(Handler):
    def __init__(self, connect: Callable[[], pyodbc.Connection], insert: str):
        super().__init__(logging.INFO)
        self.insert = insert
        self.connection = connect()
        self.db = self.connection.cursor()

        self._serialize_scope = ".".join
        self._serialize_extra = json.dumps

        atexit.register(self._cleanup)

    @property
    def serialize_scope(self) -> Callable[[List[Any]], str]:
        return self._serialize_scope

    @serialize_scope.setter
    def serialize_scope(self, func: Callable[[List[Any]], str]) -> None:
        self._serialize_scope = func

    @property
    def serialize_extra(self) -> Callable[[Any], str]:
        return self._serialize_extra

    @serialize_extra.setter
    def serialize_extra(self, func: Callable[[Any], str]) -> None:
        self.serialize_extra = func

    def emit(self, record):
        if record.exc_info:
            record.exc_text = logging.Formatter().formatException(record.exc_info)

        self.db.execute(
            self.insert,
            datetime.fromtimestamp(record.created),
            self.serialize_scope([record.module, record.funcName]),
            record.status if hasattr(record, "status") else None,
            self.serialize_extra(record.extra) if hasattr(record, "extra") and record.extra else None,
            record.exc_text if record.exc_text else None,
        )
        self.db.commit()

    def _cleanup(self):
        self.connection.close()


class SqlServerConnection:
    def __init__(self, server: str, database: str, username: str, password: str, driver_version: str = "17"):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver_version = driver_version

    def __call__(self, *args, **kwargs) -> pyodbc.Connection:
        return pyodbc.connect(f"DRIVER={{ODBC Driver {self.driver_version} for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password}")
