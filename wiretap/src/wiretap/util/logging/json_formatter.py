import json
import logging
from json import JSONEncoder
from typing import Any

from wiretap.meta.type_factory import create_instance
from wiretap.util.activity_scope import ActivityScope
from wiretap.util.logging.json_encoding import DefaultEncode
from wiretap.util.logging.json_middleware import JSONMiddleware, JSONMiddlewareContext


class JSONFormatter(logging.Formatter):

    def __init__(
            self,
            encoders: list[str | dict] | None = None,
            middleware: list[str | dict] | None = None
    ) -> None:
        super().__init__()

        if encoders is not None:
            self.default_encode = DefaultEncode([create_instance(e, JSONEncoder) for e in encoders])

        if middleware is not None:
            self.middleware = [create_instance(p, JSONMiddleware) for p in middleware]

    def format(self, record: logging.LogRecord) -> str:
        # core: Apply each modifier.
        activity_extra = self.get_closest_activity_extra(record)

        entry: dict[str, Any] = {}
        for middleware in self.middleware:
            try:
                entry = middleware(JSONMiddlewareContext(record, entry, activity_extra))
            except Exception as error:
                raise RuntimeError(
                    f"{type(middleware).__name__} failed formatting a record "
                    f"from {record.name} at {record.pathname}:{record.lineno}."
                ) from error

        return json.dumps(
            entry,
            sort_keys=False,
            allow_nan=False,
            default=self.default_encode
        )

    @staticmethod
    def get_closest_activity_extra(record: logging.LogRecord) -> dict[str, Any] | None:
        # core: Prefer explicitly attached activity data from wiretap status logs.
        if data := getattr(record, "wiretap", None):
            return data

        # core: Plain logs inside an activity inherit the nearest active scope.
        if scope := ActivityScope.current():
            return scope.to_extra(status=None, state=None)

        return None
