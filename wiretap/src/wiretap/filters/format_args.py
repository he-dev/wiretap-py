import logging
from typing import Callable, cast

from ..types import DefaultExtra


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
