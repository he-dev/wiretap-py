import dataclasses
import inspect
import logging
import logging.config
import logging.handlers
import asyncio
import multiprocessing
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
    [subject],
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
    :subject,
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
            "fmt": "{asctime}.{msecs:03.0f} {indent} {subject}/{activity} | {trace} | {elapsed:.3f}s | {message} | {details} | {attachment}",
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
        "strip_exc_info": {
            "()": wiretap.filters.StripExcInfo
        },
        "serialize_details": {
            "()": wiretap.filters.SerializeDetailsToJson
        },
        "context_extra": {
            "()": wiretap.filters.AddContextExtra
        },
        "trace_extra": {
            "()": wiretap.filters.AddTraceExtra
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
                # "context_extra",
                # "trace_extra"
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
                "serialize_details",
                # "context_extra",
                # "trace_extra"
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
            "handlers": ["console", "file", "sqlserver"],
            # "handlers": ["console", "file"],
            # "handlers": ["file"],
            # "handlers": ["console", "file", "memory"],
            "level": "DEBUG"
        }
    }
}

wiretap.dict_config(config)


@wiretap.telemetry()
def include_neither_args_nor_result(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(include_args=True, include_result=True)
def include_args_and_result(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(include_args=dict(a=".1f", b=".1f"), include_result=".3f")
def include_args_and_result_formatted(a: int, b: int) -> int:
    return a + b


@wiretap.telemetry(message="This is a start message!")
def use_message(logger: wiretap.TraceLogger = None):
    logger.other.log_info("This is an info message!")
    logger.final.log_noop("This is a noop message!")


@wiretap.telemetry()
def use_module():
    demo2.another_module()


@wiretap.telemetry()
def uses_default_logger():
    logging.info(msg="This is a classic log.")


@wiretap.telemetry()
def trace_only_once(logger: wiretap.TraceLogger = None):
    logger.final.log_end(message="Trace this only once!")


@wiretap.telemetry(include_args=dict(a=None, b=None))
def include_args_without_logger(a: int, b: int, logger: wiretap.BasicLogger = None):
    return a + b


@wiretap.telemetry(include_args=dict(a=None, b=None), include_result=True)
def include_args_without_formatting(a: int, b: int):
    return a + b


@wiretap.telemetry()
def cancel_this_function_because_of_iteration_stop(logger: wiretap.TraceLogger = None):
    @wiretap.telemetry()
    def numbers() -> Iterator[int]:
        yield 1
        yield 2
        return
        yield 3

    for x in numbers():
        logger.other.log_info(details=dict(x=x))


@wiretap.telemetry()
def foo(value: int, logger: wiretap.TraceLogger = None, **kwargs) -> int:
    logger.other.log_info(details=dict(name=f"sync-{value}"))
    logging.info("This is a classic message!")
    # raise ValueError("Test!")
    qux(value)
    result = 3
    logger.final.log_result(message="This went smooth!", details=dict(value=f"{result:.1f}"))
    return result


@wiretap.telemetry(include_args=dict(value=".2f", bar=lambda x: f"{x}-callable"), include_result=True)
def fzz(value: int, logger: wiretap.BasicLogger = None) -> int:
    # return logger.completed(3, wiretap.FormatResultDetails())
    return 3


@wiretap.telemetry()
def qux(value: int, scope: wiretap.TraceLogger = None):
    scope.other.log_info(details=dict(name=f"sync-{value}"))
    # raise ValueError("Test!")


@wiretap.telemetry()
async def bar(value: int, scope: wiretap.TraceLogger = None):
    scope.other.log_info(details=dict(name=f"sync-{value}"))
    await asyncio.sleep(2.0)
    foo(0)


@wiretap.telemetry()
async def baz(value: int, scope: wiretap.TraceLogger = None):
    scope.other.log_info(details=dict(name=f"sync-{value}"))
    await asyncio.sleep(3.0)


def flow_test():
    with wiretap.begin_telemetry(subject="outer", activity="outer") as outer:
        outer.other.log_info(details=dict(foo=1))
        with wiretap.begin_telemetry(subject="outer", activity="inner") as inner:
            inner.other.log_info(details=dict(bar=2))

        try:
            raise ValueError
        except:
            # outer.canceled(reason="Testing suppressing exceptions.")
            outer.final.log_error()


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
    try:
        bar_e()
    except ZeroDivisionError:
        pass


@wiretap.telemetry(attachment="bar_e")
def bar_e():
    baz_e()


@wiretap.telemetry()
def baz_e():
    raise ZeroDivisionError


@wiretap.telemetry()
def blub(a):
    pass


@dataclasses.dataclass
class Home(Protocol):
    foo: int


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    # h = Home(2)

    # fzz(7)

    # print(foo(1, bar="baz"))

    foo_e()

    # blub(1, 2)

    flow_test()
    include_neither_args_nor_result(1, 2)
    include_args_and_result(1, 2)
    include_args_and_result_formatted(1, 2)
    use_message()
    include_args_without_logger(1, 2)
    include_args_without_formatting(3, 4)
    cancel_this_function_because_of_iteration_stop()
    use_module()
    uses_default_logger()
    trace_only_once()
