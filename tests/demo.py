import logging
import logging.config

import wiretap.src.wiretap as wiretap
from wiretap.src.wiretap import UnitOfWork, UnitOfWorkScope, telemetry

from wiretap_sqlite.src.wiretap.handlers.sqlite import SQLiteHandler
from wiretap_sqlserver.src.wiretap.handlers import SqlServerHandler, SqlServerOdbcConnectionString


def configure_logging():
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "console": {
                "style": "{",
                "format": "{asctime}.{msecs:.0f} | {module}.{funcName} | {status} | {extra}",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "defaults": {"status": "<status>", "extra": "<extra>"}
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": "INFO"
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "when": "d",
                "interval": 1,
                "filename": r"c:\temp\wiretap.log",
                "formatter": "console",
                "level": "INFO"
            },
            "sqlserver": {
                "class": "wiretap_sqlserver.src.wiretap.handlers.SqlServerHandler",
                "connection_string": SqlServerOdbcConnectionString.standard(server="localhost,1433", database="master", username="sa", password="blub123!"),
                "level": "INFO"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "INFO"
            }
        }
    })


configure_logging()


@telemetry(**wiretap.APPLICATION)
def flow_decorator_test(value: int, scope: UnitOfWorkScope = None):
    scope.running(foo=value)
    # raise ValueError
    pass


def flow_test():
    with UnitOfWork(module="x", name="custom") as scope:
        # uow.started("Custom flow.")
        # flow.state(foo="bar")
        # if True:
        #    flow.altered("The value was true.")
        scope.running(metadata={"foo": "bar"})
        try:
            raise ValueError
        except:
            scope.canceled()


if __name__ == "__main__":
    # flow_test()
    flow_decorator_test(7)
