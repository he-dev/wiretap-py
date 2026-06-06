import logging
from dataclasses import dataclass, field
from typing import Annotated

import yaml

import wiretap


class Workflow:
    @dataclass#(frozen=True)
    class ExecuteStep(wiretap.Buzz):
        step_index: Annotated[int, wiretap.FeedToStateItem(cascade=True)]

        @dataclass#(frozen=True)
        class Okay(wiretap.Okay["Workflow.ExecuteStep"]):
            items_processed: Annotated[int, wiretap.FeedToStateItem()]

        @dataclass#(frozen=True)
        class Fail(wiretap.Fail["Workflow.ExecuteStep"]):
            pass


@dataclass#(frozen=True)
class DeleteFile(wiretap.Snap):
    tags = ["io"]
    path: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart()]

    # note: Handled by FeedToStateItem annotation.
    # def state_item(self, push: wiretap.PushStateItem) -> None:
    #    push("Path", self.path)

    # case: Shadows FeedToMessagePart annotation that causes a warning.
    def message_parts(self, push: wiretap.PushMessagePart) -> None:
        push("Path: {path}")

    @dataclass#(frozen=True)
    class Okay(wiretap.Okay["DeleteFile"]):
        pass


@dataclass
class DeleteFiles(wiretap.Buzz):
    @dataclass
    class Okay(wiretap.Okay["DeleteFiles"]):
        pass

    @dataclass
    class Fail(wiretap.Fail["DeleteFiles"]):
        pass

    @dataclass
    class Void(wiretap.Void["DeleteFiles"]):
        pass


def scenarios():
    logging.info("This is a log message outside of any activity.")

    with wiretap.begin_buzz(DeleteFiles()) as batch:
        for path in [
            "/path/to/one.txt",
            "/path/to/two.txt",
            "/path/to/archive.tmp",
        ]:
            try:
                with batch.begin_item(DeleteFile(path=path)) as item:
                    if path.endswith(".tmp"):
                        raise ValueError("Temporary files are not deleted by this workflow.")

                    item.set_status(DeleteFile.Okay()).log()
            except Exception as e:
                pass

        batch.log_status(DeleteFiles.Okay())

    with wiretap.begin_buzz(Workflow.ExecuteStep(step_index=1)) as scope:
        try:
            # busy...
            logging.info("This is a log message.")
            wiretap.log_status(DeleteFile(path="/path/to/file.txt"), DeleteFile.Okay())

            # sleep(random.uniform(0.5, 1.0))
            scope.log_status(Workflow.ExecuteStep.Okay(items_processed=100))
        except Exception as e:
            scope.log_status(Workflow.ExecuteStep.Fail(exception=e))

    with wiretap.begin_buzz(wiretap.PrototypeBuzz(name="Testing", foo="bar")) as scope:
        # wiretap.log_note("This is a beep.")

        with wiretap.begin_buzz(wiretap.PrototypeBuzz(name="Nested")) as nested:
            nested.log_status(wiretap.PrototypeBuzz.Okay(message="This is an okay."))

        scope.log_status(wiretap.PrototypeBuzz.Okay(message="This is an okay.", bar="baz"))
        pass
        # scope.log_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.log_status(Prototyping.Fail(message="This is a fail.", exception=None))


if __name__ == "__main__":
    with open(r"..\..\cfg\wiretap.yml", "r") as file:
        config = yaml.safe_load(file)
        # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
        wiretap.configure(config)
    scenarios()
