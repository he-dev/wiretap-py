import logging
import sys
import uuid
import os
import pyodbc
import json
import atexit
from datetime import datetime, date, timezone
from logging import Handler
from typing import Callable, Any, List, Optional, Dict, Protocol, runtime_checkable

DEFAULT_INSERT = """
INSERT INTO wiretap_log(
    [instance],
    [parent], 
    [node], 
    [timestamp], 
    [scope], 
    [status], 
    [level], 
    [elapsed], 
    [details],
    [attachment]
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


@runtime_checkable
class _WiretapRecord(Protocol):
    exc_text: str | None
    created: float
    module: str
    funcName: str
    values: List[Any]
    parent: uuid.UUID | None
    node: uuid.UUID
    levelname: str
    status: str
    elapsed: float
    details: str | None
    attachment: str | None


class SqlServerHandler(Handler):

    def __init__(self, connection_string: str, insert: str):
        super().__init__()
        self.connection_string = connection_string
        self.insert = insert
        self.db: Optional[pyodbc.Cursor] = None
        atexit.register(self._cleanup)

    def emit(self, record: _WiretapRecord):
        # There's no 'status' or other fields when using the default interface.
        if not hasattr(record, "status"):
            return

        self.formatter.format(record)

        args = [
            record.parent.__str__() if record.parent else None,  # parent
            record.node.__str__(),  # node
            # record.instance,  # instance
            datetime.fromtimestamp(record.created, tz=timezone.utc),  # timestamp
            ".".join(n for n in [record.module, record.funcName] if n is not None),  # scope
            record.status.lower(),  # status
            record.levelname,  # level
            record.elapsed,  # elapsed
            record.details,  # details
            record.exc_text or record.attachment  # attachment
        ]

        args = record.values + args

        try:
            self._connect()
            self.db.execute(self.insert, *args)
            self.db.commit()
        except:
            # Disable this handler if an error occurs.
            self.setLevel(sys.maxsize)
            logging.exception(msg=f"Handler '{self.name}' could not log and has been disabled.", exc_info=True)

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
