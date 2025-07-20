import asyncio
import logging
import logging.config
import logging.handlers
import os
import pathlib
import random
import time
from enum import Enum
from time import sleep

import yaml

import wiretap
from wiretap import *
from wiretap.util.stats.basic import BasicStats


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
    with wiretap.begin_scope(state={"foo": "bar"}):
        wiretap.log_info("This is a core event.")
        wiretap.log_debug("This is a util event.")
        wiretap.log_trace("This is a meta event.")
        logging.info("This is a plain info.")


def log_with_scope():
    with wiretap.begin_scope(state={"foo": "bar"}), wiretap.log_scope():
        wiretap.log_info("This is a core event.")


def log_nested_activities():
    with wiretap.begin_scope(name="first", state={"foo": "foo"}):
        wiretap.log_info("This is the first activity.")
        with wiretap.begin_scope(name="second", state={"bar": "bar"}):
            wiretap.log_info("This is the second activity.")
            with wiretap.begin_scope(name="third", state={"baz": "baz"}):
                wiretap.log_info("This is the third activity.")
            with wiretap.begin_scope(name="other"):
                wiretap.log_info("This is a transaction.")


def log_with_none_block():
    with wiretap.begin_scope(tags={"foo"}):
        wiretap.log_info("This is the info block.")
        with wiretap.begin_scope(name="nope", tags={"bar"}):
            wiretap.log_info("This is the lite scope.")
            wiretap.log_debug("This is the lite scope.")


def log_empty_loop():
    with begin_scope() as t, begin_loop(name="empty_loop", tags={"test_loop_0"}):
        pass


def log_single_loop():
    with begin_scope(), begin_loop(name="one_iteration", tags={"test_loop_1"}) as loop:
        with loop.begin_iteration():
            pass


def log_single_loop_3():
    with begin_scope():
        sms_stats = BasicStats()
        for i in [1, 2, 3]:
            with begin_scope(index=i) as iter_scope:
                sleep(random.uniform(0.5, 1.5))
                sms_stats.count_item(iter_scope.elapsed)
                log_debug("This item is complete.")
        log_info("Fake sms stats.", sms_stats=sms_stats)


def log_multiple_loops():
    with begin_scope(), begin_loop(name="find_email", message="This is a test loop!", tags={"loop_wide_tag"}) as loop:
        for i in range(5):
            # noinspection PyBroadException
            try:
                with loop.begin_iteration(email_id=f"foo-{i}", tags={i}) as iteration:
                    iteration.log_event(message=f"This is the {iteration.index}-th iteration.")
                    time.sleep(random.randint(1, 100) / 1000)  # waits for a random time between 1 and 100 milliseconds
                    if i in [2, 4]:
                        raise ValueError("This interation has failed!")
            except Exception:
                pass


def log_exception_with_stack():
    def always_fails():
        with wiretap.begin_scope():
            raise TestException("Uses the message!", other="Has some custom value!")

    with wiretap.begin_scope():
        try:
            always_fails()
        except:
            wiretap.log_error("There was an error!")


def log_error_without_stack():
    def always_fails():
        with wiretap.begin_scope():
            raise TestException("This is a test exception  message.!", other="Has some custom value!")

    with wiretap.begin_scope():
        try:
            always_fails()
        except Exception as e:
            wiretap.log_error(message=str(e))


def log_with_custom_correlation():
    with wiretap.begin_scope(id="this-is-custom-id"):
        pass


def log_multiple_times():
    with wiretap.begin_scope():
        pass


def log_path():
    with wiretap.begin_scope():
        wiretap.log_info("Logs paths", path=pathlib.Path("c:/temp/test.log"))


def log_error():
    with wiretap.begin_scope():
        wiretap.log_error(message="This is an error message.")


def demo():
    log_without_scope()
    log_with_defaults()
    log_with_scope()
    log_nested_activities()
    log_with_none_block()
    # log_empty_loop()
    # log_single_loop()
    log_single_loop_3()
    # log_multiple_loops()
    log_multiple_times()
    log_multiple_times()
    log_exception_with_stack()
    log_error_without_stack()
    log_with_custom_correlation()
    log_multiple_times()
    log_path()
    log_error()


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"
    app_root = pathlib.Path(__file__).resolve().parent

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)

    # can_everything()
    demo()
