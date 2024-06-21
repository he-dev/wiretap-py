import asyncio
import datetime
import logging
import logging.config
import logging.handlers
import os
import random
import time
from enum import Enum

import yaml
import wiretap


# @wiretap.telemetry()
async def bar(value: int):
    scope.other.trace_info(details=dict(name=f"sync-{value}")).log_trace()
    await asyncio.sleep(2.0)
    # foo(0)


# @wiretap.telemetry()
async def baz(value: int):
    scope.other.trace_info(details=dict(name=f"sync-{value}")).log_trace()
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
    with wiretap.log_activity(tags={"baz", "bar"}) as t:
        t.log_info(message="This is an ordinary info.")
        t.log_branch(name="test_branch")
        t.log_metric(name="test_metric", value=1)
        t.log_snapshot(name="test_snapshot", foo="bar")
        t.log_trace(code="test", name="test", message="This is a custom trace.")
        logging.info("This is a plain info.")


def logging_nested_activities():
    with wiretap.log_activity(tags={"foo"}) as foo:
        foo.log_info("This is the first activity")
        with wiretap.log_activity(tags={"bar"}) as bar:
            bar.log_info("This is the second activity")
            with wiretap.log_activity(tags={"baz"}) as baz:
                baz.log_info("This is the third activity")
                baz.log_exit("This activity didn't end.")


def logging_empty_loop():
    with wiretap.log_activity() as t, t.log_loop(name="test_loop_0") as l:
        pass


def logging_single_loop():
    with wiretap.log_activity() as t, t.log_loop(name="test_loop_1") as l:
        with l.iteration():
            pass


def logging_multiple_loops():
    with wiretap.log_activity() as t, t.log_loop(name="test_loop_n") as l:
        for i in range(5):
            with l.iteration():
                time.sleep(random.randint(1, 100) / 1000)  # waits for a random time between 1 and 100 milliseconds


def logging_exception_with_stack():
    def always_fails():
        with wiretap.log_activity() as t:
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.log_activity() as t:
        try:
            always_fails()
        except:
            pass


def logging_exception_without_stack():
    def always_fails():
        with wiretap.log_activity() as t:
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.log_activity() as t:
        try:
            always_fails()
        except:
            t.log_error(exc_info=wiretap.no_exc_info_if(TestException))


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
    logging_empty_loop()
    logging_single_loop()
    logging_multiple_loops()
    logging_exception_with_stack()
    logging_exception_without_stack()
