import logging
from dataclasses import dataclass, field
from typing import Annotated

import yaml

import wiretap


class Workflow:
    @dataclass(frozen=True)
    class ExecuteStep(wiretap.Buzz):
        step_index: Annotated[int, wiretap.StateItem()]

        @dataclass(frozen=True)
        class Okay(wiretap.Okay["Workflow.ExecuteStep"]):
            items_processed: Annotated[int, wiretap.StateItem()]

        @dataclass(frozen=True)
        class Fail(wiretap.Fail["Workflow.ExecuteStep"]):
            pass


@dataclass(frozen=True)
class DeleteFile(wiretap.Snap):
    path: Annotated[str, wiretap.StateItem(), wiretap.MessagePart()]

    # note: Handled by StateItem annotation.
    # def state_item(self, set: wiretap.SetStateItem) -> None:
    #    set("Path", self.path)

    # case: Shadows MessagePart annotation that causes a warning.
    def message_parts(self, append: wiretap.AppendMessagePart) -> None:
        append("Path: {path}")

    @dataclass(frozen=True)
    class Okay(wiretap.Okay["DeleteFile"]):
        pass


def scenarios():
    with wiretap.begin_buzz(Workflow.ExecuteStep(step_index=1)) as scope:
        try:
            # busy...
            logging.info("This is a log message.")
            wiretap.log_status(DeleteFile(path="/path/to/file.txt"), DeleteFile.Okay())

            # sleep(random.uniform(0.5, 1.0))
            scope.log_status(Workflow.ExecuteStep.Okay(items_processed=100))
        except Exception as e:
            scope.log_status(Workflow.ExecuteStep.Fail(exception=e))

    with wiretap.begin_buzz(wiretap.Prototyping(activity_name="Testing", state=None)) as scope:
        #wiretap.log_note("This is a beep.")
        pass
        # scope.log_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.log_status(Prototyping.Fail(message="This is a fail.", exception=None))


if __name__ == "__main__":
    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)
    scenarios()
