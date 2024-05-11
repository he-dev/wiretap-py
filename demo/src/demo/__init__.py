import asyncio
import datetime
import logging
import logging.config
import logging.handlers
import time
import yaml
import wiretap


# @wiretap.telemetry()
async def bar(value: int, scope: wiretap.process.ActivityScope = None):
    scope.other.trace_info(details=dict(name=f"sync-{value}")).log_trace()
    await asyncio.sleep(2.0)
    # foo(0)


# @wiretap.telemetry()
async def baz(value: int, scope: wiretap.process.ActivityScope = None):
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
    with wiretap.begin_activity():
        raise ZeroDivisionError


def can_everything():
    logging.info("There is no scope here!")
    with wiretap.begin_activity(message="This is the main scope!", snapshot=dict(foo="bar"), tags={"qux"}) as s1:
        time.sleep(0.2)
        s1.log_info("200ms later...", snapshot=dict(bar="baz"))
        with wiretap.begin_activity(name="can_cancel") as s2:
            time.sleep(0.3)
            logging.warning("Didn't use wiretap!")
            s2.log_exit("There wasn't anything to do here!")
            # wiretap.log_info("This won't work!")
        s1.log_trace("click", "Check!")
        time.sleep(0.3)

        with wiretap.begin_activity("catches") as s3:
            try:
                will_fail()
            except ZeroDivisionError as e:
                s3.log_exit("Caught ZeroDivisionError!")


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.dict_config(config)

    can_everything()
