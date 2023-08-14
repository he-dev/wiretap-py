import atexit
import logging
import sys
import uuid
from datetime import datetime, timezone
from logging import Handler
from typing import Any, Dict, Protocol, runtime_checkable, cast

import sqlalchemy  # type: ignore

DEFAULT_INSERT = """
INSERT INTO dev.wiretap_log(
    [parent_id], 
    [unique_id], 
    [timestamp], 
    [activity], 
    [trace], 
    [level], 
    [elapsed], 
    [message],
    [details],
    [attachment]
) VALUES (
    :parent_id, 
    :unique_id, 
    :timestamp, 
    :activity, 
    :trace, 
    :level, 
    :elapsed, 
    :message,
    :details, 
    :attachment
)
"""


@runtime_checkable
class _LogRecordExt(Protocol):
    parent_id: uuid.UUID | None
    unique_id: uuid.UUID
    activity: str
    trace: str
    elapsed: float
    details: str | None
    attachment: str | None


class SqlServerHandler(Handler):

    def __init__(self, connection_string: str, insert: str = DEFAULT_INSERT):
        super().__init__()
        connection_url = sqlalchemy.engine.URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})
        self.engine = sqlalchemy.create_engine(connection_url)
        self.insert = sqlalchemy.sql.text(insert)

        atexit.register(self._cleanup)

    def emit(self, record: logging.LogRecord):
        is_ext = hasattr(record, "trace")

        params = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
            #"activity": ".".join(n for n in [record.module, record.funcName] if n is not None),
            "level": record.levelname,
            "message": record.message if hasattr(record, "message") and record.message != str(None) else None,
        }

        recext = cast(_LogRecordExt, record)
        params = params | (self.formatter.values or {} if hasattr(self.formatter, "values") else {})

        if is_ext:
            params = params | {
                "parent_id": recext.parent_id.__str__() if recext.parent_id else None,
                "unique_id": recext.unique_id.__str__(),
                "activity": recext.activity,
                "trace": recext.trace.lower(),
                "elapsed": recext.elapsed,
                "details": recext.details,
                "attachment": recext.attachment
            }

            if record.exc_text:
                params["attachment"] = params["attachment"] + "\n\n" + record.exc_text if params["attachment"] else record.exc_text

        else:
            params = params | {
                "parent_id": None,
                "unique_id": None,
                "activity": None,
                "trace": None,
                "elapsed": None,
                "details": None,
                "attachment": None
            }

        try:
            with self.engine.connect() as c:
                c.execute(self.insert, params)
                c.commit()
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
