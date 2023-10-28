import pytest
import logging
import logging.config
from logging.handlers import MemoryHandler
from typing import cast

import wiretap
import wiretap.tracing

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
        record.__dict__["details"].pop("source", None)  # this is not checkable because it contains a dynamic line-number

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
    def case04(logger: wiretap.tracing.Activity = None):
        logger.other.trace_info("This is an info.").log()
        logger.other.trace_item("foo", "This is an item.").log()
        logger.other.trace_skip("Had to skip this!").log()
        logger.other.trace_metric("bar", "baz").log()

    case04()

    dumpster.assert_record_count(6)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="info", message="This is an info.")
    dumpster.assert_record_values(2, trace="item", details=dict(foo="This is an item."))
    dumpster.assert_record_values(3, trace="skip", message="Had to skip this!")
    dumpster.assert_record_values(4, trace="metric", details=dict(bar="baz"))
    dumpster.assert_record_values(5, trace="end")


# def test_can_suppress_duplicate_traces(dumpster: Dumpster):
#     @wiretap.telemetry()
#     def case05(activity: wiretap.Activity = None):
#         activity.start.trace_begin().with_message("This is the begin.").log()
#         activity.final.trace_end().with_message("This is the end.").log()
#
#     case05()
#
#     dumpster.assert_record_count(2)
#     dumpster.assert_record_values(0, trace="begin")
#     dumpster.assert_record_values(1, trace="end", message="This is the end.")


def test_can_log_noop(dumpster: Dumpster):
    @wiretap.telemetry()
    def case06(activity: wiretap.tracing.Activity = None):
        activity.final.trace_noop("This didn't go well.").log()

    case06()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="noop", message="This didn't go well.")


def test_can_log_abort(dumpster: Dumpster):
    @wiretap.telemetry()
    def case07(activity: wiretap.tracing.Activity = None):
        activity.final.trace_abort("This didn't go well.").log()

    case07()

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="abort", message="This didn't go well.")


def test_can_log_error(dumpster: Dumpster):
    @wiretap.telemetry()
    def case08():
        raise ZeroDivisionError

    try:
        case08()
    except:
        pass

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin")
    dumpster.assert_record_values(1, trace="error", message="Unhandled <ZeroDivisionError> has occurred: <N/A>")
    assert isinstance(dumpster.logs()[1].exc_info[1], ZeroDivisionError)


def test_can_disable_begin(dumpster: Dumpster):
    @wiretap.telemetry(auto_begin=False)
    def case09(activity: wiretap.tracing.Activity = None):
        activity.start.trace_begin().with_message("This is a begin.").log()
        activity.final.trace_end().with_message("This is an end.").log()

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
    @wiretap.telemetry(on_begin=lambda t: t.with_message("This is a begin.").with_details(foo="bar").with_attachment("baz"))
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
    @wiretap.telemetry(on_error=wiretap.tracing.LogAbortWhen(ZeroDivisionError))
    def case14():
        raise ZeroDivisionError("This is a test message.")

    try:
        case14()
    except:  # noqa
        pass

    dumpster.assert_record_count(2)
    dumpster.assert_record_values(0, trace="begin", )
    dumpster.assert_record_values(1, trace="abort", message="Unable to complete due to <ZeroDivisionError>: This is a test message.")


def test_raises_when_not_initialized():
    @wiretap.telemetry(auto_begin=False)
    def case15(activity: wiretap.tracing.Activity = None):
        activity.other.trace_info("This is an info.").log()

    with pytest.raises(wiretap.tracing.ActivityStartMissing):
        case15()


def test_raises_when_duplicate_start(dumpster: Dumpster):
    @wiretap.telemetry()
    def case16(activity: wiretap.tracing.Activity = None):
        activity.start.trace_begin().with_message("This is the begin.").log()

    with pytest.raises(wiretap.tracing.ActivityAlreadyStarted):
        case16()


def test_can_log_custom_traces(dumpster: Dumpster):
    @wiretap.telemetry(auto_begin=False)
    def case17(activity: wiretap.tracing.Activity = None):
        activity.start.trace("one").log()
        activity.other.trace("two").log()
        activity.final.trace("three").log()

    case17()

    dumpster.assert_record_count(3)
    dumpster.assert_record_values(0, trace="one", )
    dumpster.assert_record_values(1, trace="two")
    dumpster.assert_record_values(2, trace="three")


def test_raises_when_trace_not_logged(dumpster: Dumpster):
    @wiretap.telemetry()
    def case18(activity: wiretap.tracing.Activity = None):
        activity.other.trace_info("This is an info.")  # not logged so end will raise

    with pytest.raises(wiretap.tracing.PreviousTraceNotLogged):
        case18()
