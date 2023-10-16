import atexit
import logging
import sys
import uuid
import sqlalchemy  # type: ignore
from datetime import datetime
from logging import Handler
from typing import Protocol, runtime_checkable, cast
from wiretap.types import DefaultExtra


# class _LogRecordExt(Protocol):
#     parent_id: uuid.UUID | None
#     unique_id: uuid.UUID
#     timestamp: datetime
#     subject: str
#     activity: str
#     trace: str
#     elapsed: float
#     details: str | None
#     attachment: str | None


class SqlServerHandler(Handler):
    extra_params: list[str] = list()

    def __init__(self, connection_string: str, insert: str):
        super().__init__()
        connection_url = sqlalchemy.engine.URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})
        self.engine = sqlalchemy.create_engine(connection_url)
        self.insert = sqlalchemy.sql.text(insert)

        atexit.register(self._cleanup)

    def emit(self, record: logging.LogRecord):
        extra = cast(DefaultExtra, record)

        details = None
        if isinstance(extra.details, dict) and extra.details:
            details = str(extra.details)

        if isinstance(extra.details, str) and extra.details != "{}":
            details = extra.details

        insert_params = {
            "parent_id": extra.parent_id.__str__() if extra.parent_id else None,
            "unique_id": extra.unique_id.__str__(),
            "timestamp": extra.timestamp,
            "subject": extra.subject,
            "activity": extra.activity,
            "trace": extra.trace.lower(),
            "level": record.levelname,
            "elapsed": extra.elapsed,
            "message": record.message if hasattr(record, "message") and record.message != str(None) else None,  # Prevent empty string messages.
            "details": details,
            "attachment": extra.attachment
        }

        if record.exc_text:
            insert_params["attachment"] = insert_params["attachment"] + "\n\n" + record.exc_text if insert_params["attachment"] else record.exc_text

        for p in self.extra_params:
            assert hasattr(record, p)
            insert_params[p] = record.__dict__[p]

        try:
            with self.engine.connect() as c:
                c.execute(self.insert, insert_params)
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
