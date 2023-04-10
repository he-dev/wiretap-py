import atexit
import logging
import sys
import uuid
from datetime import datetime, timezone
from logging import Handler
from typing import Any, Dict, Protocol, runtime_checkable, cast

import sqlalchemy  # type: ignore

DEFAULT_INSERT = """
INSERT INTO wiretap_log(
    [parent], 
    [node], 
    [timestamp], 
    [scope], 
    [status], 
    [level], 
    [elapsed], 
    [details],
    [attachment]
) VALUES (
    :parent, 
    :node, 
    :timestamp, 
    :scope, 
    :status, 
    :level, 
    :elapsed, 
    :details, 
    :attachment
)
"""


@runtime_checkable
class _LogRecordExt(Protocol):
    values: Dict[str, Any] | None
    parent: uuid.UUID | None
    node: uuid.UUID
    status: str
    elapsed: float
    details: str | None
    attachment: str | None


class SqlServerHandler(Handler):

    def __init__(self, connection_string: str, insert: str = DEFAULT_INSERT):
        super().__init__()
        self.insert = sqlalchemy.sql.text(insert)

        connection_url = sqlalchemy.engine.URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})
        self.engine = sqlalchemy.create_engine(connection_url)

        atexit.register(self._cleanup)

    def emit(self, record: logging.LogRecord):
        default_message: str | None = None
        if self.formatter:
            record.format = "{message}"
            default_message = self.formatter.format(record)
            record.__dict__.pop("format", None)

        params = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
            "scope": ".".join(n for n in [record.module, record.funcName] if n is not None),
            "level": record.levelname,
        }

        recext = cast(_LogRecordExt, record)
        params = params | (recext.values or {})

        if hasattr(record, "status"):
            params = params | {
                "parent": recext.parent.__str__() if recext.parent else None,
                "node": recext.node.__str__(),
                "status": recext.status.lower(),
                "elapsed": recext.elapsed,
                "details": recext.details,
                "attachment": recext.attachment
            }
        else:
            params = params | {
                "parent": None,
                "node": None,
                "status": None,
                "elapsed": None,
                "details": None,
                "attachment": default_message
            }

        try:
            with self.engine.connect() as c:
                c.execute(self.insert, **params)
        except:  # noqa
            # Disable this handler if an error occurs.
            self.setLevel(sys.maxsize)
            logging.exception(msg=f"Handler '{self.name}' could not log and has been disabled.", exc_info=True)

    def _cleanup(self):
        self.engine.dispose(close=True)


class SqlServerOdbcConnectionString:

    @staticmethod
    def standard(server: str, database: str, username: str, password: str, driver_version: str = "17") -> str:
        return f"DRIVER={{ODBC Driver {driver_version} for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

    @staticmethod
    def trusted(server: str, database: str, driver_version: str = "17") -> str:
        return f"DRIVER={{ODBC Driver {driver_version} for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes"
