import inspect
import logging
import logging.config
import logging.handlers
import asyncio
import multiprocessing
from typing import Iterator


import wiretap
import wiretap_sqlserver.sqlserverhandler

from wiretap_sqlserver.sqlserverhandler import SqlServerOdbcConnectionString

INSERT = """
INSERT INTO dev.wiretap_log(
    [instance],
    [parent], 
    [node], 
    [timestamp], 
    [scope], 
    [status], 
    [level], 
    [elapsed], 
    [message],
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
    :message,
    :details, 
    :attachment
)
"""


def configure_logging():
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            # "console": {
            #    "style": "{",
            #    "format": "{asctime}.{msecs:.0f} | {module}.{funcName} | {status}",
            #    "datefmt": "%Y-%m-%d %H:%M:%S",
            #    "defaults": {"status": "<status>", "correlation": "<correlation>", "extra": "<extra>"}
            # },
            "wiretap": {
                "()": wiretap.MultiFormatter,
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                ".": {
                    "formats": {
                        "classic": "{asctime}.{msecs:03.0f} | {levelname} | {module}.{funcName} | {message}",
                        "wiretap": "{asctime}.{msecs:03.0f} {indent} {module}.{funcName} | {status} | {elapsed:.3f}s | {message} | {details} | {attachment}"
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
                "level": "DEBUG"
            },
            "sqlserver": {
                #"class": "wiretap_sqlserver.src.wiretap_sqlserver.sqlserverhandler.SqlServerHandler",
                "class": "wiretap_sqlserver.sqlserverhandler.SqlServerHandler",
                "connection_string": SqlServerOdbcConnectionString.standard(server="localhost,1433", database="master", username="sa", password="MSSQL2022!"),
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
                # "handlers": ["console", "file", "sqlserver"],
                "handlers": ["console", "file"],
                # "handlers": ["file"],
                # "handlers": ["console", "file", "memory"],
                "level": "DEBUG"
            }
        }
    })


configure_logging()


@wiretap.telemetry()
def include_neither_args_nor_result(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(include_args=True, include_result=True)
def include_args_and_result(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(include_args=".1f", include_result=".3f")
def include_args_and_result_formatted(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(message="This is a start messag!")
def use_message(logger: wiretap.Logger = None):
    logger.running("This is a running message!")
    logger.canceled("This is a canceled message!")


@wiretap.telemetry(include_args=True)
def include_args_without_logger(a: int, b: int, logger: wiretap.Logger = None):
    return a + b


@wiretap.telemetry(include_args=dict(a=None, b=None))
def include_args_without_formatting(a: int, b: int):
    return a + b


@wiretap.telemetry()
def cancel_this_function_without_result():
    raise wiretap.Cancellation("This was canceled!")


@wiretap.telemetry(include_result=True)
def cancel_this_function_with_result():
    raise wiretap.Cancellation("This was canceled!", result=8)


@wiretap.telemetry()
def cancel_this_function_because_of_iteration_stop(logger: wiretap.Logger = None):
    @wiretap.telemetry()
    def numbers() -> Iterator[int]:
        yield 1
        yield 2
        return
        yield 3

    for x in numbers():
        logger.running(details=dict(x=x))


@wiretap.telemetry()
def foo(value: int, logger: wiretap.Logger = None, **kwargs) -> int:
    logger.running(details=dict(name=f"sync-{value}"))
    logging.info("This is a classic message!")
    # raise ValueError("Test!")
    qux(value)
    return logger.completed(message="This went smooth!", result=3, result_format=".1f")


@wiretap.telemetry(include_args=dict(value=".2f", bar=lambda x: f"{x}-callable"), include_result=True)
def fzz(value: int, logger: wiretap.Logger = None) -> int:
    # return logger.completed(3, wiretap.FormatResultDetails())
    return 3


@wiretap.telemetry()
def qux(value: int, scope: wiretap.Logger = None):
    scope.running(details=dict(name=f"sync-{value}"))
    # raise ValueError("Test!")


@wiretap.telemetry()
async def bar(value: int, scope: wiretap.Logger = None):
    scope.running(details=dict(name=f"sync-{value}"))
    await asyncio.sleep(2.0)
    foo(0)


@wiretap.telemetry()
async def baz(value: int, scope: wiretap.Logger = None):
    scope.running(details=dict(name=f"sync-{value}"))
    await asyncio.sleep(3.0)


def flow_test():
    with wiretap.telemetry_scope(module=None, name="outer") as outer:
        outer.running(details=dict(foo=1))
        with wiretap.telemetry_scope(module=None, name="inner") as inner:
            inner.running(details=dict(bar=2))

        try:
            raise ValueError
        except:
            # outer.canceled(reason="Testing suppressing exceptions.")
            outer.failed()


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


@wiretap.telemetry()
def main():
    pass


@wiretap.telemetry()
def test_completed():
    pass


@wiretap.telemetry()
def foo_e():
    bar_e()


@wiretap.telemetry(attachment="bar_e")
def bar_e():
    baz_e()


@wiretap.telemetry()
def baz_e():
    raise ZeroDivisionError


@wiretap.telemetry()
def blub(a):
    pass


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    # fzz(7)

    # flow_test()
    # print(foo(1, bar="baz"))

    # foo_e()

    # blub(1, 2)

    include_neither_args_nor_result(1, 2)
    include_args_and_result(1, 2)
    include_args_and_result_formatted(1, 2)
    use_message()
    include_args_without_logger(1, 2)
    include_args_without_formatting(3, 4)
    cancel_this_function_without_result()
    cancel_this_function_with_result()
    cancel_this_function_because_of_iteration_stop()
