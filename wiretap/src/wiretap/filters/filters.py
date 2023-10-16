import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Callable, Any, Protocol, Optional, cast
from ..data import current_tracer, ContextExtra, TraceExtra, InitialExtra, DefaultExtra, FinalExtra


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
        if tracer:
            setattr(record, self.name, self.char * (logger.depth or 1))
        else:
            setattr(record, self.name, self.char)
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
        initial = cast(InitialExtra, record)
        can_format = \
            hasattr(record, "inputs") and \
            hasattr(record, "inputs_spec") and \
            initial.inputs and \
            initial.inputs_spec
        if can_format:
            args = {}
            for k, f in initial.inputs_spec.items():
                try:
                    arg = initial.inputs[k]
                    if arg is not None:
                        f = f or ""
                        if isinstance(f, str):
                            args[k] = format(arg, f)
                        if isinstance(f, Callable):
                            args[k] = f(arg)
                except KeyError as e:
                    source_fun = record.__dict__.get('activity', None) or record.funcName
                    source_mod = record.__dict__.get('subject', None) or record.module
                    raise KeyError(f"Cannot format arg <{k}> because <{source_fun}> in module <{source_mod}> does not have a parameter with this name.") from e
            if args:
                cast(DefaultExtra, record).details["args"] = args

        return True


class FormatResult(logging.Filter):
    def __init__(self):
        super().__init__("format_result")

    def filter(self, record: logging.LogRecord) -> bool:
        final = cast(FinalExtra, record)
        can_format = \
            hasattr(record, "output") and \
            hasattr(record, "output_spec") and \
            final.output is not None and \
            final.output_spec is not None
        if can_format:
            result: str = ""
            f = final.output_spec
            if isinstance(f, str):
                result = format(final.output, f)
            if isinstance(f, Callable):
                result = f(final.output)

            if result:
                cast(DefaultExtra, record).details["result"] = result

        return True


class SkipDuplicateTrace(logging.Filter):
    def __init__(self):
        super().__init__("skip_duplicate_trace")

    def filter(self, record: logging.LogRecord) -> bool:
        tracer = current_tracer.get()
        trace_extra = cast(DefaultExtra, record)
        return trace_extra.trace not in tracer.traces
