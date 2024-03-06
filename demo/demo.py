import dataclasses
import inspect
import logging
import logging.config
import logging.handlers
import asyncio
import multiprocessing
import pathlib
import time

import demo2
from typing import Iterator, Protocol

import wiretap
import wiretap_sqlserver.sqlserverhandler

from wiretap_sqlserver.sqlserverhandler import SqlServerOdbcConnectionString

INSERT = """
INSERT INTO dev.wiretap_log(
    [instance],
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
    :instance, 
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

config = {
    "version": 1,
    "formatters": {
        # "console": {
        #    "style": "{",
        #    "format": "{asctime}.{msecs:.0f} | {module}.{funcName} | {status}",
        #    "datefmt": "%Y-%m-%d %H:%M:%S",
        #    "defaults": {"status": "<status>", "correlation": "<correlation>", "extra": "<extra>"}
        # },
        "wiretap": {
            "()": logging.Formatter,
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "fmt": "{asctime}.{msecs:03.0f} {indent} {activity} | {event} | {elapsed:.3f}s | {message} | {snapshot}",
        },
        # "elastic": {
        #     "()": logging.Formatter,
        #     "style": "{",
        #     "datefmt": "%Y-%m-%d %H:%M:%S",
        #     "fmt": "{json}",
        # },
        "elastic": {
            "()": wiretap.formatters.JSONFormatter,
            # "style": "{",
            # "datefmt": "%Y-%m-%d %H:%M:%S",
            # "fmt": "{json}",
        }
    },
    "filters": {
        "instance": {
            "()": wiretap.filters.AddConstExtra,
            "name": "instance",
            "value": "demo-1"
        },
        "indent": {
            "()": wiretap.filters.AddIndentExtra,
            "char": "_"
        },
        "timestamp_local": {
            "()": wiretap.filters.AddTimestampExtra,
            "tz": "local"
        },
        "timestamp_utc": {
            "()": wiretap.filters.AddTimestampExtra,
            "tz": "utc"
        },
        "strip_exc_info": {
            "()": wiretap.filters.StripExcInfo
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "wiretap",
            "level": "DEBUG",
            "filters": [
                "indent",
                "timestamp_local",
                "strip_exc_info",
            ]
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": "d",
            "interval": 1,
            "filename": r"c:\temp\wiretap.log",
            "formatter": "wiretap",
            "level": "DEBUG"
        },
        "elastic": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": "d",
            "interval": 1,
            "filename": r"c:\temp\elastic.log",
            "formatter": "elastic",
            "level": "DEBUG",
            "filters": [
                # "indent",
                "timestamp_utc",
                "strip_exc_info",
                # "serialize_to_json"
                # "context_extra",
                # "trace_extra"
            ]
        },
        "sqlserver": {
            # "class": "wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler.SqlServerHandler",
            # "class": "wiretap_sqlserver.sqlserverhandler.SqlServerHandler",
            "()": wiretap_sqlserver.sqlserverhandler.SqlServerHandler,
            "connection_string": SqlServerOdbcConnectionString.standard(server="localhost,1433", database="master", username="sa", password="MSSQL2022!"),
            "insert": INSERT,
            "level": "DEBUG",
            "filters": [
                "instance",
                "strip_exc_info",
            ],
            ".": {
                "extra_params": ["instance"]
            }
        },
        "memory": {
            "class": "logging.handlers.MemoryHandler",
            "capacity": 100,
            "formatter": "wiretap",
            "level": "DEBUG"
        }
    },
    "loggers": {
        "": {
            # "handlers": ["console", "file", "sqlserver"],
            "handlers": ["console", "file", "elastic"],
            # "handlers": ["file"],
            # "handlers": ["console", "file", "memory"],
            "level": "DEBUG"
        }
    }
}

wiretap.dict_config(config)


# @wiretap.telemetry()
async def bar(value: int, scope: wiretap.process.Activity = None):
    scope.other.trace_info(details=dict(name=f"sync-{value}")).log()
    await asyncio.sleep(2.0)
    # foo(0)


# @wiretap.telemetry()
async def baz(value: int, scope: wiretap.process.Activity = None):
    scope.other.trace_info(details=dict(name=f"sync-{value}")).log()
    await asyncio.sleep(3.0)


async def main_async():
    b1 = asyncio.create_task(bar(1))
    b2 = asyncio.create_task(baz(2))
    await asyncio.sleep(0)
    # foo(3)
    await asyncio.gather(b1, b2)
    # foo(4)


def main_proc():
    # b1 = asyncio.create_task(bar(1))
    # b2 = asyncio.create_task(baz(2))
    # await asyncio.sleep(0)
    # foo(3)
    # await asyncio.gather(b1, b2)
    # foo(4)

    # with multiprocessing.Pool() as pool:
    #     for _ in pool.starmap(foo, [(x,) for x in range(1, 10)]):
    #         pass

    pass


def will_fail():
    with wiretap.begin_activity():
        raise ZeroDivisionError


def can_everything():
    logging.info("There is no scope here!")
    with wiretap.begin_activity(message="This is the main scope!", snapshot=dict(foo="bar")):
        time.sleep(0.2)
        wiretap.log_info("200ms later...", snapshot=dict(bar="baz"))
        with wiretap.begin_activity(name="can_cancel"):
            time.sleep(0.3)
            logging.warning("Didn't use wiretap!")
            wiretap.log_cancelled("There wasn't anything to do here!")
        wiretap.log("click", "Check!")
        time.sleep(0.3)

        with wiretap.begin_activity("catches"):
            try:
                will_fail()
            except ZeroDivisionError as e:
                wiretap.log_cancelled("Caught ZeroDivisionError!")


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    can_everything()
