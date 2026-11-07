"""Demo logging configuration, matching demo/cfg/wiretap.yml."""

import logging
from logging.handlers import TimedRotatingFileHandler

from wiretap.util.logging import JsonFormatter, TextFormatter


config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console_full": {
            "()": TextFormatter,
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "fmt": (
                '{asctime}.{msecs:03.0f} [{levelname:7s}] '
                '{indent}{activity[about]}: "{message}", '
                'properties: {properties}, trc={trace}, src={source}'
            ),
        },
        "console_lite": {
            "()": TextFormatter,
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "fmt": (
                '{asctime}.{msecs:03.0f} [{levelname:7s}] '
                '{activity[buzzing]}: {indent}{activity[about]}[{activity[event]}]: '
                '"{message}", properties: {properties}'
            ),
        },
        "elastic_json": {
            "()": JsonFormatter,
            # JsonFormatter resolves encoder and pipeline definitions by import path.
            "encoders": [
                "wiretap.util.encoding.EncodeDateTime",
                "wiretap.util.encoding.EncodeUUID",
                "wiretap.util.encoding.EncodeSet",
                "wiretap.util.encoding.EncodePath",
                "wiretap.util.encoding.EncodeToDict",
            ],
            "pipeline": [
                "wiretap.util.rendering.AddTimestamp",
                "wiretap.util.rendering.AddMessage",
                "wiretap.util.rendering.AddActivity",
                "wiretap.util.rendering.AddProperties",
                "wiretap.util.rendering.AddTrace",
                {
                    "()": "wiretap.util.rendering.AddSource",
                    "include_when": [logging.DEBUG, logging.ERROR, logging.CRITICAL],
                },
                "wiretap.util.rendering.AddException",
                "wiretap.util.rendering.RemoveNoneOrEmpty",
            ],
        },
    },
    "handlers": {
        "console_full": {
            "()": logging.StreamHandler,
            "formatter": "console_full",
        },
        "console_lite": {
            "()": logging.StreamHandler,
            "formatter": "console_lite",
        },
        "console_file": {
            "()": TimedRotatingFileHandler,
            "when": "d",
            "interval": 1,
            "filename": r"c:\temp\wiretap_console.log",
            "formatter": "console_full",
        },
        "elastic_file": {
            "()": logging.FileHandler,
            "filename": r"c:\temp\wiretap_elastic.log",
            "formatter": "elastic_json",
        },
    },
    "root": {
        "handlers": ["console_lite", "console_file", "elastic_file"],
        "level": logging.DEBUG,
    },
    "loggers": {
        "PIL": {"level": logging.WARNING},
    },
}
