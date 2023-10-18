import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Callable, Any, Protocol, Optional, cast
from ..types import current_tracer, ContextExtra, TraceExtra, InitialExtra, DefaultExtra, FinalExtra


class AddConstExtra(logging.Filter):
    def __init__(self, name: str, value: Any):
        self.value = value
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, self.name, self.value)
        return True


class AddTimestampExtra(logging.Filter):
    def __init__(self, tz: str = "utc"):
        super().__init__("timestamp")
        match tz.casefold().strip():
            case "utc":
                self.tz = datetime.now(timezone.utc).tzinfo  # timezone.utc
            case "local" | "lt":
                self.tz = datetime.now(timezone.utc).astimezone().tzinfo

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, self.name, datetime.fromtimestamp(record.created, tz=self.tz))
        return True


class LowerLevelName(logging.Filter):
    def __init__(self):
        super().__init__("level")

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, self.name, record.levelname.lower())
        return True


class AddIndentExtra(logging.Filter):
    def __init__(self, char: str = "."):
        super().__init__("indent")
        self.char = char

    def filter(self, record: logging.LogRecord) -> bool:
        tracer = current_tracer.get()
        logger = tracer.default if tracer else None
        indent = self.char * (logger.depth or 1) if tracer else self.char
        setattr(record, self.name, indent)
        return True


class SerializeDetails(Protocol):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None: ...


class _JsonDateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()


class SerializeDetailsToJson(SerializeDetails):
    def __call__(self, value: Optional[Dict[str, Any]]) -> str | None:
        return json.dumps(value, sort_keys=True, allow_nan=False, cls=_JsonDateTimeEncoder) if value else None


class SerializeDetailsExtra(logging.Filter):
    def __init__(self, serialize: SerializeDetails = SerializeDetailsToJson()):
        super().__init__("details")
        self.serialize = serialize

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, self.name) and record.details:
            record.details = self.serialize(record.details)
        return True


class AddContextExtra(logging.Filter):
    def __init__(self):
        super().__init__("context")

    def filter(self, record: logging.LogRecord) -> bool:
        tracer = current_tracer.get()
        logger = tracer.default if tracer else None
        context_extra = ContextExtra(
            parent_id=logger.parent.id if logger and logger.parent else None,
            unique_id=logger.id if logger else None,
            subject=logger.subject if logger else record.module,
            activity=logger.activity if logger else record.funcName
        )
        extra = vars(context_extra)
        for k, v in extra.items():
            record.__dict__[k] = v

        return True


class AddTraceExtra(logging.Filter):
    def __init__(self):
        super().__init__("trace")

    def filter(self, record: logging.LogRecord) -> bool:
        tracer = current_tracer.get()
        logger = tracer.default if tracer else None
        if not hasattr(record, self.name):
            trace_extra = TraceExtra(
                trace="info",
                elapsed=logger.elapsed if logger else 0,
                details={},
                attachment=None
            )
            extra = vars(trace_extra)
            for k, v in extra.items():
                record.__dict__[k] = v

        return True


class StripExcInfo(logging.Filter):
    def __init__(self):
        super().__init__("exc_info")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_cls, exc, exc_tb = record.exc_info
            # the first 3 frames are the decorator traces; let's get rid of them
            while exc_tb.tb_next:
                exc_tb = exc_tb.tb_next
            record.exc_info = exc_cls, exc, exc_tb
        return True


class FormatArgs(logging.Filter):
    def __init__(self):
        super().__init__("format_args")

    def filter(self, record: logging.LogRecord) -> bool:
        default = cast(DefaultExtra, record)
        args_native = default.details.pop("args_native", None)
        args_format = default.details.pop("args_format", None)
        can_format = args_native and args_format
        if can_format:
            if isinstance(args_format, bool):
                args_format = {k: "" for k in args_native}

            args_formatted = {}
            for arg_name, arg_format in args_format.items():
                try:
                    arg = args_native[arg_name]
                    while arg is not None:

                        arg_format = arg_format or ""

                        if isinstance(arg_format, str):
                            args_formatted[arg_name] = format(arg, arg_format)
                            break

                        if isinstance(arg_format, Callable):
                            args_formatted[arg_name] = arg_format(arg)
                            break

                        raise ValueError(f"Cannot format arg <{arg_name}> of <{default.activity}> in module <{default.subject}> because its spec is invalid. It must be: [str | Callable].")
                except KeyError as e:
                    raise KeyError(f"Cannot format arg <{arg_name}> because <{default.activity}> in module <{default.subject}> does not have a parameter with this name.") from e
            if args_formatted:
                cast(DefaultExtra, record).details["args"] = args_formatted

        return True


class FormatResult(logging.Filter):
    def __init__(self):
        super().__init__("format_result")

    def filter(self, record: logging.LogRecord) -> bool:
        default = cast(DefaultExtra, record)
        result_native = default.details.pop("result_native", None)
        result_format = default.details.pop("result_format", None)

        result_formatted: str = ""
        while result_native is not None:
            if isinstance(result_format, bool):
                if not result_format:
                    break
                else:
                    result_format = ""

            result_format = result_format or ""

            if isinstance(result_format, str):
                result_formatted = format(result_native, result_format)
                break

            if isinstance(result_format, Callable):
                result_formatted = result_format(result_native)
                break

            raise ValueError(f"Cannot format the result of <{default.activity}> in module <{default.subject}> because its spec is invalid. It must be: [str | Callable].")

        if result_formatted:
            default.details["result"] = result_formatted

        return True
