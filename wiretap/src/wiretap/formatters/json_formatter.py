import functools
import json
import logging
from typing import Any, Tuple

from _reusable import resolve_class
from wiretap.json import JSONMultiEncoder


class JSONFormatter(logging.Formatter):

    def __init__(self, encoders: list[str], properties: list[str]) -> None:
        super().__init__()
        self.encoders = encoders

        def parse(item: Any) -> Tuple[str, dict[str, Any]]:
            """Parses JSONProperty into type name and parameters."""
            if isinstance(item, str):
                return item, {}

            if isinstance(item, dict):
                if "()" not in item:
                    raise KeyError(f"Constructor key '()' missing in: {item}")
                return item["()"], {k: v for k, v in item.items() if k != "()"}

            raise TypeError(f"Cannot parse JSONProperty due to an unexpected type '{type(item)}'. Only [str | dict] are supported. Value: {item}")

        self.properties = [resolve_class(class_name)(**params) for class_name, params in [parse(p) for p in properties]]

    def format(self, record):
        # Merges each new dictionary with the previous one.
        entry = functools.reduce(lambda e, p: e | p.emit(record), self.properties, {})

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            cls=JSONMultiEncoder,
            encoders=self.encoders
        )
