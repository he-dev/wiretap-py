import logging
import logging.config
import asyncio
import multiprocessing
import wiretap.src.wiretap as wiretap
import wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler

from wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler import SqlServerOdbcConnectionString


def configure_logging():
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "console": {
                "style": "{",
                "format": "{asctime}.{msecs:.0f} | {module}.{funcName} | {status}",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "defaults": {"status": "<status>", "correlation": "<correlation>", "extra": "<extra>"}
            },
            "wiretap": {
                "()": wiretap.MultiFormatter,
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                ".": {
                    "classic": "{asctime}.{msecs:.0f} | {levelname} | {module}.{funcName} | {message}",
                    "wiretap": "{asctime}.{msecs:.0f} | {levelname} | {module}.{funcName} | {status} | {elapsed} | {details} | [{parent}/{node}] | {attachment}",
                    "values": ["demo-1"]
                }
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "wiretap",
                "level": "DEBUG"
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "when": "d",
                "interval": 1,
                "filename": r"c:\temp\wiretap.log",
                "formatter": "wiretap",
                "level": "INFO"
            },
            "sqlserver": {
                "class": "wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler.SqlServerHandler",
                "connection_string": SqlServerOdbcConnectionString.standard(server="localhost,1433", database="master", username="sa", password="blub123!"),
                "insert": wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler.DEFAULT_INSERT,
                "level": "DEBUG",
                "formatter": "wiretap"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file", "sqlserver"],
                "level": "DEBUG"
            }
        }
    })


configure_logging()


# @wiretap.extra(**wiretap.APPLICATION)
@wiretap.telemetry(on_started=lambda k: {"value": k["value"], "bar": k["bar"]}, on_completed=lambda r: {"count": r})
# @telemetry(**wiretap.APPLICATION)
def foo(value: int, scope: wiretap.Logger = None, **kwargs) -> int:
    ##wiretap.running(name=f"sync-{value}")
    scope.running(name=f"sync-{value}")
    # raise ValueError("Test!")
    qux(value)
    return 3


@wiretap.telemetry()
def qux(value: int, scope: wiretap.Logger = None):
    ##wiretap.running(name=f"sync-{value}")
    scope.running(name=f"sync-{value}")
    # raise ValueError("Test!")


@wiretap.telemetry()
async def bar(value: int, scope: wiretap.Logger = None):
    scope.running(name=f"sync-{value}")
    await asyncio.sleep(2.0)
    foo(0)


@wiretap.telemetry()
async def baz(value: int, scope: wiretap.Logger = None):
    scope.running(name=f"sync-{value}")
    await asyncio.sleep(3.0)


def flow_test():
    with wiretap.local(name="outer") as outer:
        outer.running(foo=1)
        with wiretap.local(name="inner") as inner:
            inner.running(bar=2)

        try:
            raise ValueError
        except:
            outer.faulted()


async def main():
    b1 = asyncio.create_task(bar(1))
    b2 = asyncio.create_task(baz(2))
    await asyncio.sleep(0)
    foo(3)
    await asyncio.gather(b1, b2)
    foo(4)


def main_proc():
    # b1 = asyncio.create_task(bar(1))
    # b2 = asyncio.create_task(baz(2))
    # await asyncio.sleep(0)
    # foo(3)
    # await asyncio.gather(b1, b2)
    # foo(4)

    with multiprocessing.Pool() as pool:
        for _ in pool.starmap(foo, [(x,) for x in range(1, 10)]):
            pass


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()
    # flow_test()
    foo(1, bar="baz")
