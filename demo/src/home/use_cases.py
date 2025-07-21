import asyncio
import logging
import logging.config
import logging.handlers
import pathlib
import random
from enum import Enum
from time import sleep

from wiretap import *


# @wiretap.telemetry()
async def bar(value: int):
    # scope.other.trace_info(details=dict(name=f"sync-{value}")).log_trace()
    await asyncio.sleep(2.0)
    # foo(0)


# @wiretap.telemetry()
async def baz(value: int):
    # scope.other.trace_info(details=dict(name=f"sync-{value}")).log_trace()
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


class TestException(Exception):
    def __init__(self, message: str, other: str):
        super().__init__(message)
        self.other = other


class TestEnum(Enum):
    SOME_NAME = "some_value"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


def log_without_scope():
    logging.info("There is no scope here!")


def log_with_defaults():
    with begin_scope(state={"foo": "bar"}):
        log_info("This is a core event.")
        log_debug("This is a util event.")
        log_trace("This is a meta event.")
        logging.info("This is a plain info.")


def log_with_timing_1():
    with begin_scope(state={"foo": "bar"}), log_duration():
        sleep(random.uniform(0.5, 1.0))
        log_info("This is a core event.")


def log_with_timing_2():
    try:
        with begin_scope(state={"foo": "bar"}), log_duration(level="debug"):
            sleep(random.uniform(0.5, 1.0))
            raise Exception("This is a test exception.")
            log_info("This is a core event.")
    except:
        pass


def log_nested_activities():
    with begin_scope(name="first", state={"foo": "foo"}):
        log_info("This is the first activity.")
        with begin_scope(name="second", state={"bar": "bar"}):
            log_info("This is the second activity.")
            with begin_scope(name="third", state={"baz": "baz"}):
                log_info("This is the third activity.")
            with begin_scope(name="other"):
                log_info("This is a transaction.")


def log_with_none_block():
    with begin_scope(tags={"foo"}):
        log_info("This is the info block.")
        with begin_scope(name="nope", tags={"bar"}):
            log_info("This is the lite scope.")
            log_debug("This is the lite scope.")


def log_single_loop_3():
    with begin_scope():
        sms_stats = LoopStats()
        for i in [1, 2, 3]:
            with begin_scope(index=i) as iter_scope:
                sleep(random.uniform(0.5, 1.5))
                sms_stats.count_item(iter_scope.stopwatch.elapsed_ms)
                log_debug("This item is complete.")
        log_info("Fake sms stats.", sms_stats=sms_stats)


def log_exception_with_stack():
    def always_fails():
        with begin_scope():
            raise TestException("Uses the message!", other="Has some custom value!")

    with begin_scope():
        try:
            always_fails()
        except:
            log_error("There was an error!")


def log_error_without_stack():
    def always_fails():
        with begin_scope():
            raise TestException("This is a test exception  message.!", other="Has some custom value!")

    with begin_scope():
        try:
            always_fails()
        except Exception as e:
            log_error(message=str(e))


def log_with_custom_correlation():
    with begin_scope(id="this-is-custom-id"):
        pass


def log_multiple_times():
    with begin_scope():
        pass


def log_path():
    with begin_scope():
        log_info("Logs paths", path=pathlib.Path("c:/temp/test.log"))


def log_error_():
    with begin_scope():
        log_error(message="This is an error message.")
