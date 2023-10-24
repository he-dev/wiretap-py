import logging
from collections.abc import Callable
from typing import cast

from ..types import DefaultExtra


class InvalidArgFormat(Exception):
    pass


class ArgNotFound(Exception):
    pass


class FormatArgs(logging.Filter):
    def __init__(self):
        super().__init__("format_args")

    def filter(self, record: logging.LogRecord) -> bool:
        default = cast(DefaultExtra, record)
        args_native = default.details.pop("args_native", {})
        args_format = default.details.pop("args_format", {})

        if isinstance(args_format, bool):
            # True means all args should be formatted with the default format.
            args_format = {k: "" for k in args_native} if args_format else {}

        args_formatted = {}
        for arg_name, arg_format in args_format.items():
            try:
                arg = args_native[arg_name]
                while arg is not None:

                    arg_format = arg_format or ""

                    if isinstance(arg_format, str):
                        args_formatted[arg_name] = format(arg, arg_format)
                        break

                    if callable(arg_format):  # isinstance(arg_format, Callable):
                        args_formatted[arg_name] = arg_format(arg)
                        break

                    raise InvalidArgFormat(
                        f"Cannot format arg <{arg_name}> of <{default.activity}> in module <{default.subject}>. "
                        f"Its spec is invalid. "
                        f"It must be [str | Callable | None], but found <{type(arg_format)}>."
                    )
            except KeyError as e:
                raise ArgNotFound(
                    f"Cannot format arg <{arg_name}>. "
                    f"The <{default.activity}> activity in module <{default.subject}> does not have a parameter with this name."
                ) from e
        if args_formatted:
            cast(DefaultExtra, record).details["args"] = args_formatted

        return True
