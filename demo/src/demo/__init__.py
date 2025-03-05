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
from wiretap import info_loop


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


def logging_without_scope():
    logging.info("There is no scope here!")


def logging_with_defaults():
    with wiretap.info_scope(tags={"baz", "bar"}) as t:
        t.log_info(message="This is an ordinary info.")
        t.log_trace(name="test", message="This is a custom trace.")
        logging.info("This is a plain info.")


def logging_nested_activities():
    with wiretap.info_scope(name="first", tags={"foo"}) as foo:
        foo.log_info(message="This is the first activity.")
        with wiretap.info_scope(name="second", tags={"bar"}) as bar:
            bar.log_info(message="This is the second activity.")
            with wiretap.info_scope(name="third", tags={"baz"}) as baz:
                baz.log_info(message="This is the third activity.")
            with wiretap.info_scope(name="other") as qux:
                qux.log_info(message="This is a transaction.")


def log_with_none_block():
    with wiretap.info_scope(tags={"foo"}) as b:
        b.log_info(message="This is the info block.")
        with wiretap.none_block(name="nope", tags={"bar"}) as n:
            n.log_info(message="This is the none block.")
            n.log_info(message="This is the none block.")


def logging_empty_loop():
    with wiretap.info_scope() as t, info_loop(tags={"test_loop_0"}):
        pass


def logging_single_loop():
    with wiretap.info_scope(), info_loop(tags={"test_loop_1"}) as iteration:
        with iteration():
            pass


def logging_multiple_loops():
    with wiretap.info_scope(), info_loop(name="find_email", tags={"custom_tag"}) as iteration:
        for i in range(5):
            with iteration() as abort:
                time.sleep(random.randint(1, 100) / 1000)  # waits for a random time between 1 and 100 milliseconds
                if i == 2:
                    abort()


def logging_exception_with_stack():
    def always_fails():
        with wiretap.info_scope():
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.info_scope():
        try:
            always_fails()
        except:
            pass


def logging_exception_without_stack():
    def always_fails():
        with wiretap.info_scope():
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.info_scope() as t:
        try:
            always_fails()
        except Exception as e:
            t.log_error(message=str(e))


def logging_with_custom_correlation():
    with wiretap.info_scope(id="this-is-custom-id"):
        pass


def logging_multiple_times():
    with wiretap.info_scope():
        pass


def logging_path():
    with wiretap.info_scope() as s:
        s.log_info(path=pathlib.Path("c:/temp/test.log"))


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.dict_config(config)

    # can_everything()

    logging_without_scope()
    logging_with_defaults()
    logging_nested_activities()
    log_with_none_block()
    logging_empty_loop()
    logging_single_loop()
    logging_multiple_loops()
    logging_multiple_times()
    logging_multiple_times()
    logging_exception_with_stack()
    logging_exception_without_stack()
    logging_with_custom_correlation()
    logging_multiple_times()
    logging_path()
