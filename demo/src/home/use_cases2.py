import asyncio
import logging
import logging.config
import logging.handlers
import pathlib
import random
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from time import sleep

import yaml

import wiretap
from wiretap.util.activity_scope import WithMessageParts, AppendMessagePart, with_zero_status


class Workflow:
    @dataclass(frozen=True, slots=True)
    class ExecutingStep(wiretap.Core):
        step_index: wiretap.StateItem[int]

        @dataclass(frozen=True, slots=True)
        class Beep(wiretap.Beep):
            pass

        @dataclass(frozen=True, slots=True)
        class Okay(wiretap.Okay):
            items_processed: wiretap.StateItem[int]

        @dataclass(frozen=True, slots=True)
        class Fail(wiretap.Fail):
            pass


@with_zero_status
@dataclass(frozen=True)
class DeletingFile(wiretap.Buzz):
    path: str = wiretap.state_item()

    def message_parts(self, append: AppendMessagePart) -> None:
        append("Path: {path}")

    @dataclass(frozen=True)
    class Okay2(wiretap.Okay):
        pass



def demo_begin_scope():
    wiretap.log_note("This is a note outside a scope.")
    with wiretap.begin_scope(Workflow.ExecutingStep(step_index=1)) as scope:
        wiretap.log_note("This is a note inside a scope.")
        try:
            # busy...
            # wiretap.note.log_debug("This is a note".)
            scope.log_status(Workflow.ExecutingStep.Beep(message="Step is being processed..."))
            with wiretap.begin_scope(DeletingFile(path="/path/to/file.txt")) as y:
                y.log_status(DeletingFile.Okay2())

            # sleep(random.uniform(0.5, 1.0))
            scope.log_status(Workflow.ExecutingStep.Okay(items_processed=100))
        except Exception as e:
            scope.log_status(Workflow.ExecutingStep.Fail(exception=e))

    with wiretap.begin_scope(wiretap.Prototyping(activity_name="Testing", state=None)) as scope:
        scope.log_status(wiretap.Prototyping.Beep(message="This is a beep."))
        # scope.log_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.log_status(Prototyping.Fail(message="This is a fail.", exception=None))


if __name__ == "__main__":
    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)
    demo_begin_scope()
