import pytest
import logging
import logging.config
from logging.handlers import MemoryHandler
from typing import cast

import wiretap

config = {
    "version": 1,
    "formatters": {
        "wiretap": {
            "()": logging.Formatter,
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "fmt": "{asctime}.{msecs:03.0f} {indent} {activity} | {trace} | {elapsed:.3f}s | {message} | {details} | {attachment}",
        }
    },
    "filters": {
        "const_extra": {
            "()": wiretap.filters.AddConstExtra,
            "name": "const_extra",
            "value": "const_value"
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
            ]
        },
        "memory": {
            "class": "logging.handlers.MemoryHandler",
            "capacity": 100,
            "formatter": "wiretap",
            "level": "DEBUG",
            "filters": [
                "indent",
                "timestamp_local",
                "strip_exc_info",
                "const_extra"
            ]
        }
    },
    "loggers": {
        "": {
            "handlers": ["memory", "console"],
            "level": "DEBUG"
        }
    }
}


@pytest.fixture(autouse=True)
def reset_config():
    wiretap.dict_config(config)


class Dumpster:

    @staticmethod
    def logs() -> list[logging.LogRecord]:
        return cast(MemoryHandler, logging.root.handlers[0]).buffer

    @staticmethod
    def assert_record_count(expected: int):
        assert len(Dumpster.logs()) == expected

    @staticmethod
    def assert_record_values(index: int, **expected):
        record = Dumpster.logs()[index]

        a_keys = [k for k in expected.keys()]
        e_keys = [k for k in expected.keys() if k in record.__dict__]
        assert e_keys == a_keys, "Some keys are missing!"

        actual = {k: record.__dict__[k] for k, v in expected.items()}
        assert actual == expected, "Some values aren't equal!"


@pytest.fixture(autouse=True)
def dumpster():
    return Dumpster()


def test_can_log_defaults(dumpster: Dumpster):
    @wiretap.telemetry()
    def case01():
        pass

    case01()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, activity="case01", trace="begin", details={}, attachment=None, indent="_", const_extra="const_value")
    dumpster.assert_record_values(1, activity="case01", trace="end", details={}, attachment=None, indent="_", const_extra="const_value")


def test_can_log_args_and_result_raw(dumpster: Dumpster):
    @wiretap.telemetry(include_args=True, include_result=True)
    def case02(x: int, y: int):
        return x + y

    case02(1, 2)

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", details=dict(args=dict(x="1", y="2")))
    dumpster.assert_record_values(1, trace="end", details=dict(result="3"))


def test_can_log_selected_args(dumpster: Dumpster):
    @wiretap.telemetry(include_args=dict(y=None), include_result=True)
    def case03(x: int, y: int):
        return x + y

    case03(1, 2)

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", details=dict(args=dict(y="2")))
    dumpster.assert_record_values(1, trace="end", details=dict(result="3"))


def test_can_log_other_traces(dumpster: Dumpster):
    @wiretap.telemetry()
    def case04(logger: wiretap.TraceLogger = None):
        logger.other.log_info(message="This is an info.")
        logger.other.log_item(message="This is an item.")
        logger.other.log_skip(message="This is a skip.")
        logger.other.log_metric(message="This is a metric.")

    case04()

    dumpster.assert_record_count(6)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="info", message="This is an info.")
    dumpster.assert_record_values(2, trace="item", message="This is an item.")
    dumpster.assert_record_values(3, trace="skip", message="This is a skip.")
    dumpster.assert_record_values(4, trace="metric", message="This is a metric.")
    dumpster.assert_record_values(5, trace="end")


def test_can_suppress_duplicate_traces(dumpster: Dumpster):
    @wiretap.telemetry()
    def case05(logger: wiretap.TraceLogger = None):
        logger.final.log_end(message="This is the end.")

    case05()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="end", message="This is the end.")


def test_can_log_noop(dumpster: Dumpster):
    @wiretap.telemetry()
    def case06(logger: wiretap.TraceLogger = None):
        logger.final.log_noop()

    case06()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="noop")


def test_can_log_abort(dumpster: Dumpster):
    @wiretap.telemetry()
    def case07(logger: wiretap.TraceLogger = None):
        logger.final.log_abort()

    case07()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="abort")


def test_can_log_error(dumpster: Dumpster):
    @wiretap.telemetry()
    def case08(logger: wiretap.TraceLogger = None):
        raise ZeroDivisionError

    try:
        case08()
    except:
        pass

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="error", message="Unhandled exception has occurred.")
    assert isinstance(dumpster.logs()[1].exc_info[1], ZeroDivisionError)


def test_can_disable_begin(dumpster: Dumpster):
    @wiretap.telemetry(auto_begin=False)
    def case09(logger: wiretap.TraceLogger = None):
        logger.initial.log_begin(message="This is a begin.")
        logger.final.log_end(message="This is an end.")

    case09()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", message="This is a begin.")
    dumpster.assert_record_values(1, trace="end", message="This is an end.")


def test_can_format_args_and_result_by_str(dumpster: Dumpster):
    @wiretap.telemetry(include_args=dict(x=".1"), include_result=".2")
    def case10(x: float):
        return x

    case10(0.15)

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", details=dict(args=dict(x="0.1")))
    dumpster.assert_record_values(1, trace="end", details=dict(result="0.15"))


def test_can_format_args_and_result_by_callable(dumpster: Dumpster):
    def one_dec_place(value):
        return format(value, ".1")

    def two_dec_places(value):
        return format(value, ".2")

    @wiretap.telemetry(include_args=dict(x=one_dec_place), include_result=two_dec_places)
    def case11(x: float):
        return x

    case11(0.15)

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", details=dict(args=dict(x="0.1")))
    dumpster.assert_record_values(1, trace="end", details=dict(result="0.15"))


def test_can_log_begin_extra(dumpster: Dumpster):
    @wiretap.telemetry(message="This is a begin.", details=dict(foo="bar"), attachment="baz")
    def case12():
        pass

    case12()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", message="This is a begin.", details=dict(foo="bar"), attachment="baz")
    dumpster.assert_record_values(1, trace="end", attachment=None)


def test_can_log_const_extra(dumpster: Dumpster):
    @wiretap.telemetry()
    def case13():
        pass

    case13()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", const_extra="const_value")
    dumpster.assert_record_values(1, trace="end", const_extra="const_value")


def test_can_log_abort_on_exception(dumpster: Dumpster):
    @wiretap.telemetry(on_error=wiretap.LogAbortWhen(ZeroDivisionError))
    def case14():
        raise ZeroDivisionError()

    try:
        case14()
    except:  # noqa
        pass

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", )
    dumpster.assert_record_values(1, trace="abort", message="Unable to complete.")
