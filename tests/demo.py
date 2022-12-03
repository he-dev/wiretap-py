import logging
import logging.config
import asyncio
import multiprocessing
import wiretap.src.wiretap as wiretap
from wiretap.src.wiretap import UnitOfWork, UnitOfWorkScope, telemetry, telemetry

from wiretap_sqlite.src.wiretap.handlers.sqlite import SQLiteHandler
from wiretap_sqlserver.src.wiretap.handlers import SqlServerHandler, SqlServerOdbcConnectionString


def configure_logging():
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "console": {
                "style": "{",
                "format": "{asctime}.{msecs:.0f} | {module}.{funcName} | {status} | {correlation} | {extra}",
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


#@wiretap.extra(**wiretap.APPLICATION)
@wiretap.telemetry(wiretap.layers.Application())
#@telemetry(**wiretap.APPLICATION)
def foo(value: int, scope: UnitOfWorkScope = None):
    ##wiretap.running(name=f"sync-{value}")
    wiretap.running(name=f"sync-{value}")
    #raise ValueError("Test!")
    qux(value)

@wiretap.telemetry(wiretap.layers.Application())
def qux(value: int, scope: UnitOfWorkScope = None):
    ##wiretap.running(name=f"sync-{value}")
    wiretap.running(name=f"sync-{value}")
    #raise ValueError("Test!")


@telemetry(wiretap.layers.Application())
async def bar(value: int, scope: UnitOfWorkScope = None):
    wiretap.running(name=f"sync-{value}")
    await asyncio.sleep(2.0)
    foo(0)


@telemetry(wiretap.layers.Application())
async def baz(value: int, scope: UnitOfWorkScope = None):
    wiretap.running(name=f"sync-{value}")
    await asyncio.sleep(3.0)


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


async def main():
    b1 = asyncio.create_task(bar(1))
    b2 = asyncio.create_task(baz(2))
    await asyncio.sleep(0)
    foo(3)
    await asyncio.gather(b1, b2)
    foo(4)


def main_proc():
    #b1 = asyncio.create_task(bar(1))
    #b2 = asyncio.create_task(baz(2))
    #await asyncio.sleep(0)
    #foo(3)
    #await asyncio.gather(b1, b2)
    #foo(4)

    with multiprocessing.Pool() as pool:
        for _ in pool.starmap(foo, [(x, ) for x in range(1, 10)]):
            pass




if __name__ == "__main__":
    asyncio.run(main())
    #main_proc()
