import inspect
import logging
import logging.config
import logging.handlers
import asyncio
import multiprocessing
import wiretap.src.wiretap as wiretap
import wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler

from wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler import SqlServerOdbcConnectionString

INSERT = """
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
) VALUES (
    :instance, 
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
                    "formats": {
                        "classic": "{asctime}.{msecs:.0f} | {levelname} | {module}.{funcName} | {message}",
                        "wiretap": "{asctime}.{msecs:.0f} {indent} {levelname} | {module}.{funcName}: {status} | {elapsed:.3f}s | {details} | {attachment}"
                    },
                    "indent": ".",
                    "values": {"instance": "demo-1"}
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
                "insert": INSERT,
                "level": "DEBUG",
                "formatter": "wiretap"
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
                "handlers": ["console", "file", "sqlserver"],
                # "handlers": ["console", "file", "memory"],
                "level": "DEBUG"
            }
        }
    })


configure_logging()


@wiretap.collect_telemetry()
def foo(value: int, logger: wiretap.Logger = None, **kwargs) -> int:
    logger.running(name=f"sync-{value}")
    logging.info("This is a classic message!")
    # raise ValueError("Test!")
    qux(value)
    return logger.completed(3, wiretap.FormatResultDetails())


@wiretap.include_result()
@wiretap.include_args(value=".2f", bar=lambda x: f"{x}-callable")
@wiretap.collect_telemetry()
def fzz(value: int, logger: wiretap.Logger = None) -> int:
    # return logger.completed(3, wiretap.FormatResultDetails())
    return 3


@wiretap.collect_telemetry()
def qux(value: int, scope: wiretap.Logger = None):
    scope.running(name=f"sync-{value}")
    # raise ValueError("Test!")


@wiretap.collect_telemetry()
async def bar(value: int, scope: wiretap.Logger = None):
    scope.running(name=f"sync-{value}")
    await asyncio.sleep(2.0)
    foo(0)


@wiretap.collect_telemetry()
async def baz(value: int, scope: wiretap.Logger = None):
    scope.running(name=f"sync-{value}")
    await asyncio.sleep(3.0)


def flow_test():
    with wiretap.collect(module=None, name="outer") as outer:
        outer.running(foo=1)
        with wiretap.collect(module=None, name="inner") as inner:
            inner.running(bar=2)

        try:
            raise ValueError
        except:
            # outer.canceled(reason="Testing suppressing exceptions.")
            outer.faulted()


async def main_async():
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


@wiretap.collect_telemetry()
def main():
    pass


@wiretap.collect_telemetry()
def test_completed():
    pass


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    fzz(7)

    flow_test()
    print(foo(1, bar="baz"))
