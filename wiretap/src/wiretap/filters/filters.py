import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Callable, Any, Protocol, Optional, cast
from ..data import current_tracer, ContextExtra, TraceExtra, InitialExtra, DefaultExtra, FinalExtra

INCLUDE = 1


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
                self.tz = timezone.utc
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
        current = current_tracer.get().logger
        if current:
            setattr(record, self.name, self.char * (current.depth or 1))
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
        super().__init__("serialize_details")
        self.serialize = serialize

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "details") and record.details:
            record.details = self.serialize(record.details)
        return True


class AddContextExtra(logging.Filter):
    def __init__(self):
        super().__init__("context_extra")

    def filter(self, record: logging.LogRecord) -> bool:
        current = current_tracer.get().logger
        context_extra = ContextExtra(
            parent_id=current.parent.id if current and current.parent else None,
            unique_id=current.id if current else None,
            subject=current.subject if current else record.module,
            activity=current.activity if current else record.funcName
        )
        extra = vars(context_extra)
        for k, v in extra.items():
            record.__dict__[k] = v

        return True


class AddTraceExtra(logging.Filter):
    def __init__(self):
        super().__init__("trace_extra")

    def filter(self, record: logging.LogRecord) -> bool:
        current = current_tracer.get().logger
        if not hasattr(record, "trace"):
            trace_extra = TraceExtra(
                trace="info",
                elapsed=current.elapsed if current else 0,
                details={},
                attachment=None
            )
            extra = vars(trace_extra)
            for k, v in extra.items():
                record.__dict__[k] = v

        return True


class StripExcInfo(logging.Filter):
    def __init__(self):
        super().__init__("strip_exc_info")

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
                arg = initial.inputs[k]
                if arg is not None:
                    f = f or ""
                    if isinstance(f, str):
                        args[k] = format(arg, f)
                    if isinstance(f, Callable):
                        args[k] = f(arg)
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
            final.output and \
            final.output_spec is not None
        if can_format:
            result = None
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
        trace_extra = cast(TraceExtra, record)
        return trace_extra.trace not in tracer.traces
