import logging
from dataclasses import dataclass, field
from typing import Annotated

import yaml

import wiretap


class Workflow:
    @dataclass(frozen=True)
    class ExecuteStep(wiretap.Activity):
        step_index: Annotated[int, wiretap.StateItem()]

        @dataclass(frozen=True)
        class Okay(wiretap.Okay["Workflow.ExecuteStep"]):
            items_processed: Annotated[int, wiretap.StateItem()]

        @dataclass(frozen=True)
        class Fail(wiretap.Fail["Workflow.ExecuteStep"]):
            pass


@dataclass(frozen=True)
class DeleteFile(wiretap.Flag["DeleteFile"]):
    path: Annotated[str, wiretap.StateItem(), wiretap.MessagePart()]

    # note: Handled by StateItem annotation.
    # def state_item(self, set: wiretap.SetStateItem) -> None:
    #    set("Path", self.path)

    # case: Shadows MessagePart annotation and causes a warning.
    def message_parts(self, append: wiretap.AppendMessagePart) -> None:
        append("Path: {path}")


def scenarios():
    wiretap.log_note("This message is outside a scope.")
    with wiretap.begin_scope(Workflow.ExecuteStep(step_index=1)) as scope:
        wiretap.log_note("This is a plain message inside a scope.")
        try:
            # busy...
            # wiretap.note.log_debug("This is a note".)
            wiretap.log_note("Step is being processed...")
            wiretap.log_flag(DeleteFile(path="/path/to/file.txt"))

            # sleep(random.uniform(0.5, 1.0))
            scope.log_buzz(Workflow.ExecuteStep.Okay(items_processed=100))
        except Exception as e:
            scope.log_buzz(Workflow.ExecuteStep.Fail(exception=e))

    with wiretap.begin_scope(wiretap.Prototyping(activity_name="Testing", state=None)) as scope:
        wiretap.log_note("This is a beep.")
        # scope.log_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.log_status(Prototyping.Fail(message="This is a fail.", exception=None))


if __name__ == "__main__":
    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)
    scenarios()
