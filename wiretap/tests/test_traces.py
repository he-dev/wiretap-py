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
            "fmt": "{asctime}.{msecs:03.0f} {indent} {subject}/{activity} | {trace} | {elapsed:.3f}s | {message} | {details} | {attachment}",
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
            "()": wiretap.filters.SerializeDetailsExtra
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
        assert expected == len(Dumpster.logs())

    @staticmethod
    def assert_record_values(index: int, **expected):
        record = Dumpster.logs()[index]

        a_keys = [k for k in expected.keys()]
        e_keys = [k for k in expected.keys() if k in record.__dict__]
        assert e_keys == a_keys, "Some keys are missing!"

        actual = {k: record.__dict__[k] for k, v in expected.items()}
        assert expected == actual, "Some values aren't equal!"


@pytest.fixture(autouse=True)
def dumpster():
    return Dumpster()


def test_can_log_defaults(dumpster: Dumpster):
    @wiretap.telemetry()
    def case01():
        pass

    case01()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, subject="test_traces", activity="case01", trace="begin", details={}, attachment=None, indent="_", const_extra="const_value")
    dumpster.assert_record_values(1, subject="test_traces", activity="case01", trace="end", details={}, attachment=None, indent="_", const_extra="const_value")


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
