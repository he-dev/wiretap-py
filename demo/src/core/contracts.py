from dataclasses import dataclass
from typing import Annotated

import wiretap


class Workflow:
    @dataclass
    class ExecuteStep(wiretap.Buzz):
        step_index: Annotated[int, wiretap.FeedToStateItem(cascade=True)]

        @dataclass
        class Okay(wiretap.Okay["Workflow.ExecuteStep"]):
            items_processed: Annotated[int, wiretap.FeedToStateItem()]

        @dataclass
        class Fail(wiretap.Fail["Workflow.ExecuteStep"]):
            pass


@dataclass
class DeleteFile(wiretap.Buzz):
    tags = ["io"]
    path: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Path")]

    # core: Bulk items are Buzz activities because they have an item duration and contribute to a parent summary.
    # case: Shadows FeedToMessagePart annotation that causes a warning.
    def message_parts(self, push: wiretap.PushItem) -> None:
        push("Path", "{state[path]}")

    @dataclass
    class Okay(wiretap.Okay["DeleteFile"]):
        pass

    @dataclass
    class Fail(wiretap.Fail["DeleteFile"]):
        pass


@dataclass
class DeleteFiles(wiretap.Bulk[DeleteFile]):
    @dataclass
    class Okay(wiretap.Okay["DeleteFiles"]):
        pass

    @dataclass
    class Fail(wiretap.Fail["DeleteFiles"]):
        pass

    @dataclass
    class Void(wiretap.Noop["DeleteFiles"]):
        pass


@dataclass
class ImportDocument(wiretap.Buzz):
    tags = ["import"]
    # core: Emits Ready at information level so a long-running import is visible as soon as it starts.
    source: Annotated[str, wiretap.FeedToStateItem(cascade=True), wiretap.FeedToMessagePart("Source")]

    # case: Intentionally shadows FeedToMessagePart to show that explicit feeds win over annotations.
    def message_parts(self, push: wiretap.PushItem) -> None:
        push("Import", "{state[source]}")

    @dataclass
    class Okay(wiretap.Okay["ImportDocument"]):
        records_saved: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Saved")]

        # util: Uses an explicit feed to format a derived summary from a structured state item.
        def message_parts(self, push: wiretap.PushItem) -> None:
            push("Result", "{state[records_saved]} records saved")

    @dataclass
    class Fail(wiretap.Fail["ImportDocument"]):
        pass

    @dataclass
    class Void(wiretap.Noop["ImportDocument"]):
        # core: Uses the inherited Void.reason contract; this status exists to show a permitted inconclusive import.
        pass


@dataclass
class ReadFile(wiretap.Buzz):
    tags = ["io"]
    path: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Path")]

    # core: This activity is annotation-only; no feed method is implemented on purpose.

    @dataclass
    class Okay(wiretap.Okay["ReadFile"]):
        bytes_read: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Bytes")]
        line_count: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Lines")]

        # core: Shadows message annotations to demonstrate a compact, custom success message.
        def message_parts(self, push: wiretap.PushItem) -> None:
            push("Read", "{state[line_count]} lines / {state[bytes_read]} bytes")

    @dataclass
    class Fail(wiretap.Fail["ReadFile"]):
        # core: No custom fields; Fail.exception supplies the message part.
        pass


@dataclass
class DownloadFile(wiretap.Buzz):
    tags = ["io", "network"]
    url: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("URL")]
    target_path: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Target")]

    # case: Intentionally shadows FeedToStateItem annotations; only selected fields enter state.
    def state_items(self, push: wiretap.PushItem) -> None:
        push("download_url", self.url)

    @dataclass
    class Okay(wiretap.Okay["DownloadFile"]):
        status_code: Annotated[int, wiretap.FeedToStateItem()]
        bytes_received: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Bytes")]

        # core: Status is annotation-only so state and message annotations can both be seen.

    @dataclass
    class NotModified(wiretap.Okay["DownloadFile"]):
        status_code: Annotated[int, wiretap.FeedToStateItem()]

        # core: Models an expected non-work outcome as Okay because nothing failed.
        def message_parts(self, push: wiretap.PushItem) -> None:
            push("Status", "{state[status_code]}")
            push("Result", "remote file was not modified")

    @dataclass
    class Fail(wiretap.Fail["DownloadFile"]):
        pass


@dataclass
class ValidateRecord(wiretap.Buzz):
    tags = ["validation"]
    row_index: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Row")]

    # core: ValidateRecord is a Buzz because it is used as a counted bulk item inside ParseDocument.

    @dataclass
    class Okay(wiretap.Okay["ValidateRecord"]):
        # core: Marker-only status; useful for clean bulk counts.
        pass

    @dataclass
    class Fail(wiretap.Fail["ValidateRecord"]):
        field_name: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Field")]

        # case: Shadows field_name's message annotation to include the exception message too.
        def message_parts(self, push: wiretap.PushItem) -> None:
            push("Invalid field", "{state[field_name]}")
            super().message_parts(push)


@dataclass
class ParseDocument(wiretap.Bulk[ValidateRecord]):
    tags = ["parse"]
    # core: Bulk item statuses are still counted, but item Ready logs are suppressed to reduce noise.
    item_status_log_policy = wiretap.StatusLogPolicy.LAST
    document_type: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Type")]

    @dataclass
    class Okay(wiretap.Okay["ParseDocument"]):
        records_parsed: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Records")]

    @dataclass
    class Fail(wiretap.Fail["ParseDocument"]):
        pass

    @dataclass
    class Void(wiretap.Noop["ParseDocument"]):
        # core: Keeps the inherited reason as the canonical explanation.
        pass


@dataclass
class SaveRecord(wiretap.Snap):
    tags = ["storage"]
    row_index: Annotated[int, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Row")]
    record_id: Annotated[str, wiretap.FeedToStateItem(), wiretap.FeedToMessagePart("Record")]

    # util: Uses an explicit message feed while keeping annotations for state.
    def message_parts(self, push: wiretap.PushItem) -> None:
        push("Save", "row {state[row_index]} as {state[record_id]}")

    @dataclass
    class Okay(wiretap.Okay["SaveRecord"]):
        # core: SaveRecord only exposes Okay/Fail, showing a strict snap contract without Void.
        pass

    @dataclass
    class Fail(wiretap.Fail["SaveRecord"]):
        pass
