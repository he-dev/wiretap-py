"""Demo logging configuration, matching demo/cfg/wiretap.yml."""

import logging
from logging.handlers import TimedRotatingFileHandler

from wiretap.util.buzz.logging import JsonFormatter, TextFormatter


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
                '{activity[channel]}: {indent}{activity[about]}[{activity[event]}]: '
                '"{message}", properties: {properties}'
            ),
        },
        "elastic_json": {
            "()": JsonFormatter,
            # JsonFormatter resolves encoder and pipeline definitions by import path.
            "encoders": [
                "wiretap.util.buzz.EncodeDateTime",
                "wiretap.util.buzz.EncodeUUID",
                "wiretap.util.buzz.EncodeSet",
                "wiretap.util.buzz.EncodePath",
                "wiretap.util.buzz.EncodeToDict",
            ],
            "pipeline": [
                "wiretap.util.buzz.AddTimestamp",
                "wiretap.util.buzz.AddMessage",
                "wiretap.util.buzz.AddActivity",
                "wiretap.util.buzz.AddProperties",
                "wiretap.util.buzz.AddTrace",
                {
                    "()": "wiretap.util.buzz.AddSource",
                    "include_when": [logging.DEBUG, logging.ERROR, logging.CRITICAL],
                },
                "wiretap.util.buzz.AddException",
                "wiretap.util.buzz.RemoveNoneOrEmpty",
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
