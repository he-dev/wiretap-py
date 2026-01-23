import os

import yaml

import wiretap
from use_cases import *


def demo():
    log_without_scope()
    log_with_defaults()
    log_unknown_type()
    log_child_method()
    log_with_timing_1()
    log_with_timing_2()
    log_nested_activities()
    log_with_none_block()
    log_single_loop_3()
    log_multiple_times()
    log_multiple_times()
    log_exception_with_stack()
    log_error_without_stack()
    log_with_custom_correlation()
    log_multiple_times()
    log_path()
    log_error_()


if __name__ == "__main__":
    # asyncio.run(main())
    # main_proc()

    os.environ["app_id"] = "demo-app"
    app_root = pathlib.Path(__file__).resolve().parent

    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)

    demo()
