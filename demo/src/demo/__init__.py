import asyncio
import datetime
import logging
import logging.config
import logging.handlers
import os
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


def will_fail():
    with wiretap.log_activity():
        raise TestException("Uses the message!", other="Has some custom value!")


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


def can_everything():
    logging.info("There is no scope here!")

    dispose = wiretap.log_resource("read_nothing", db="test")
    with wiretap.log_activity(message="This is the main scope!", extra=dict(foo="bar"), tags={"qux"}, bar="baz") as s1:
        s1.log_snapshot(some_enum=TestEnum.SOME_NAME)
        time.sleep(0.2)
        s1.log_snapshot("200ms later...", extra=dict(bar="baz"))
        s1.log_metric(name="test_number", row_count=7)
        with wiretap.log_activity(name="can_cancel") as s2:
            with wiretap.log_loop("This is a loop!") as c:
                with c.measure():
                    time.sleep(0.3)
                with c.measure():
                    time.sleep(0.7)
                logging.warning("Didn't use wiretap!")
            s2.log_exit("There wasn't anything to do here!")
            # wiretap.log_info("This won't work!")
        s1.log_trace("click", "Check!")
        time.sleep(0.3)

        with wiretap.log_activity("catches") as s3:
            try:
                will_fail()
            except TestException as e:
                # s3.log_exit("Caught ZeroDivisionError!")
                s3.log_error(exc_info=False)

    dispose()


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.dict_config(config)

    can_everything()
