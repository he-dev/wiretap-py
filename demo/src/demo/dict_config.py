import logging.handlers

import wiretap
import wiretap_sqlserver.sqlserverhandler
from wiretap_sqlserver.sqlserverhandler import SqlServerOdbcConnectionString

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
            "fmt": "{asctime}.{msecs:03.0f} {indent} {activity} | {event} | {elapsed:.3f}s | {message} | {snapshot} | {tags}",
        },
        "elastic": {
            "()": wiretap.formatters.JSONFormatter,
            ".": {
                "json_encoder_cls": wiretap.tools.JSONMultiEncoder
            }
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
                "timestamp_utc",
                "strip_exc_info",
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