import asyncio
import datetime
import logging
import logging.config
import logging.handlers
import os
import pathlib
import random
import time
from enum import Enum

import yaml
import wiretap
from wiretap import begin_scope, begin_loop


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
    with wiretap.begin_scope(dump={"args": "none"}, tags={"baz", "bar"}) as t:
        t.log_basic(message="This is an info event.")
        t.log_debug(message="This is a debug event.")
        t.log_trace(event="test", message="This is a custom trace.")
        logging.info("This is a plain info.")


def log_nested_activities():
    with wiretap.begin_scope(name="first", tags={"foo"}) as foo:
        foo.log_basic(message="This is the first activity.")
        with wiretap.begin_scope(name="second", tags={"bar"}) as bar:
            bar.log_basic(message="This is the second activity.")
            with wiretap.begin_scope(name="third", tags={"baz"}) as baz:
                baz.log_basic(message="This is the third activity.")
            with wiretap.begin_scope(name="other") as qux:
                qux.log_basic(message="This is a transaction.")


def log_with_none_block():
    with wiretap.begin_scope(tags={"foo"}) as b:
        b.log_basic(message="This is the info block.")
        with wiretap.none_scope(name="nope", tags={"bar"}) as n:
            n.log_basic(message="This is the none block.")
            n.log_basic(message="This is the none block.")


def log_empty_loop():
    with begin_scope() as t, begin_loop(tags={"test_loop_0"}):
        pass


def log_single_loop():
    with begin_scope(), begin_loop(tags={"test_loop_1"}) as iteration:
        with iteration():
            pass


def log_multiple_loops():
    with wiretap.begin_scope(), begin_loop(name="find_email", tags={"custom_tag"}) as iteration:
        for i in range(5):
            with iteration() as incomplete:
                time.sleep(random.randint(1, 100) / 1000)  # waits for a random time between 1 and 100 milliseconds
                if i == 2:
                    incomplete()


def log_exception_with_stack():
    def always_fails():
        with wiretap.begin_scope():
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.begin_scope():
        try:
            always_fails()
        except:
            pass


def log_error_without_stack():
    def always_fails():
        with wiretap.begin_scope():
            raise TestException("This is a test exception  message.!", other="Has some custom value!")

    with wiretap.begin_scope() as t:
        try:
            always_fails()
        except Exception as e:
            t.log_error(message=str(e))


def log_with_custom_correlation():
    with wiretap.begin_scope(id="this-is-custom-id"):
        pass


def log_multiple_times():
    with wiretap.begin_scope():
        pass


def log_path():
    with wiretap.begin_scope() as s:
        s.log_basic(path=pathlib.Path("c:/temp/test.log"))


def log_debug():
    with wiretap.begin_scope() as s:
        s.log_debug(message="Scope visible only in debug mode.")


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"
    app_root = pathlib.Path(__file__).resolve().parent

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.dict_config(config)

    # can_everything()

    with wiretap.begin_scope(name="demo") as scope:
        log_without_scope()
        log_with_defaults()
        log_nested_activities()
        log_with_none_block()
        log_empty_loop()
        log_single_loop()
        log_multiple_loops()
        log_multiple_times()
        log_multiple_times()
        log_exception_with_stack()
        log_error_without_stack()
        log_with_custom_correlation()
        log_multiple_times()
        log_path()
        log_debug()
