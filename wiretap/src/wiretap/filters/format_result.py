import logging
from typing import Callable, cast

from ..types import DefaultExtra


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
