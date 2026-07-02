from dataclasses import dataclass
from typing import Annotated

import wiretap


class Workflow:
    @dataclass
    class ExecuteStep(wiretap.Buzz):
        step_index: Annotated[int, wiretap.Detail(cascade=True)]

        @dataclass
        class Okay(wiretap.Okay["Workflow.ExecuteStep"]):
            items_processed: Annotated[int, wiretap.Detail()]

        @dataclass
        class Fail(wiretap.Fail["Workflow.ExecuteStep"]):
            pass


@dataclass
class DeleteFile(wiretap.Buzz):
    tags = ["io"]
    path: Annotated[str, wiretap.Detail(), wiretap.Remark("Path")]

    # core: Bulk items are Buzz activities because they have an item duration and contribute to a parent summary.
    # case: Shadows Remark annotation that causes a warning.
    def remarks(self, push: wiretap.PushItem) -> None:
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
class ImportDocument(wiretap.Buzz):
    tags = ["import"]
    # core: Emits Ready at information level so a long-running import is visible as soon as it starts.
    source: Annotated[str, wiretap.Detail(cascade=True), wiretap.Remark("Source")]

    # case: Intentionally shadows Remark to show that explicit feeds win over annotations.
    def remarks(self, push: wiretap.PushItem) -> None:
        push("Import", "{state[source]}")

    @dataclass
    class Okay(wiretap.Okay["ImportDocument"]):
        records_saved: Annotated[int, wiretap.Detail(), wiretap.Remark("Saved")]

        # util: Uses an explicit feed to format a derived summary from a structured detail.
        def remarks(self, push: wiretap.PushItem) -> None:
            push("Result", "{state[records_saved]} records saved")

    @dataclass
    class Fail(wiretap.Fail["ImportDocument"]):
        pass


@dataclass
class ReadFile(wiretap.Buzz):
    tags = ["io"]
    path: Annotated[str, wiretap.Detail(), wiretap.Remark("Path")]

    # core: This activity is annotation-only; no feed method is implemented on purpose.

    @dataclass
    class Okay(wiretap.Okay["ReadFile"]):
        bytes_read: Annotated[int, wiretap.Detail(), wiretap.Remark("Bytes")]
        line_count: Annotated[int, wiretap.Detail(), wiretap.Remark("Lines")]

        # core: Shadows remark annotations to demonstrate a compact, custom success message.
        def remarks(self, push: wiretap.PushItem) -> None:
            push("Read", "{state[line_count]} lines / {state[bytes_read]} bytes")


@dataclass
class DownloadFile(wiretap.Buzz):
    tags = ["io", "network"]
    url: Annotated[str, wiretap.Detail(), wiretap.Remark("URL")]
    target_path: Annotated[str, wiretap.Detail(), wiretap.Remark("Target")]

    # case: Intentionally shadows Detail annotations; only selected fields enter state.
    def details(self, push: wiretap.PushDetail) -> None:
        push("download_url", self.url)

    @dataclass
    class Okay(wiretap.Okay["DownloadFile"]):
        status_code: Annotated[int, wiretap.Detail()]
        bytes_received: Annotated[int, wiretap.Detail(), wiretap.Remark("Bytes")]

        def remarks(self, push: wiretap.PushItem) -> None:
            push("Status", "{state[status_code]}")
            push("Bytes", "{state[bytes_received]}")

    @dataclass
    class Noop(wiretap.Noop["DownloadFile"]):
        # core: Models a download that intentionally did no transfer work.
        pass

    @dataclass
    class NoChange(wiretap.Okay["DownloadFile"]):
        # case: Intentionally invalid custom status name; only canonical names are logged.
        pass


@dataclass
class ValidateRecord(wiretap.Buzz):
    tags = ["validation"]
    row_index: Annotated[int, wiretap.Detail(), wiretap.Remark("Row")]

    # core: ValidateRecord is a Buzz because it is used as a counted bulk item inside ParseDocument.

    @dataclass
    class Okay(wiretap.Okay["ValidateRecord"]):
        # core: Marker-only status; useful for clean bulk counts.
        pass

    @dataclass
    class Fail(wiretap.Fail["ValidateRecord"]):
        field_name: Annotated[str, wiretap.Detail(), wiretap.Remark("Field")]

        # case: Shadows field_name's message annotation to include the exception message too.
        def remarks(self, push: wiretap.PushItem) -> None:
            push("Invalid field", "{state[field_name]}")
            super().remarks(push)


@dataclass
class ParseDocument(wiretap.Bulk[ValidateRecord]):
    tags = ["parse"]
    # core: Bulk item statuses are still counted, but item Ready logs are suppressed to reduce noise.
    _item_status_log_policy = wiretap.StatusLogOptions.LAST
    document_type: Annotated[str, wiretap.Detail(), wiretap.Remark("Type")]

    @dataclass
    class Okay(wiretap.Okay["ParseDocument"]):
        records_parsed: Annotated[int, wiretap.Detail(), wiretap.Remark("Records")]


@dataclass
class SaveRecord(wiretap.Snap):
    tags = ["storage"]
    row_index: Annotated[int, wiretap.Detail(), wiretap.Remark("Row")]
    record_id: Annotated[str, wiretap.Detail(), wiretap.Remark("Record")]

    # util: Uses an explicit remark feed while keeping annotations for details.
    def remarks(self, push: wiretap.PushItem) -> None:
        push("Save", "row {state[row_index]} as {state[record_id]}")

    @dataclass
    class Okay(wiretap.Okay["SaveRecord"]):
        # core: SaveRecord only exposes Okay/Fail, showing a strict snap contract without Void.
        pass


@dataclass
class UpdateFile(wiretap.Snap):
    tags = ["io"]
    path: Annotated[str, wiretap.Detail(), wiretap.Remark("Path")]

    @dataclass
    class Noop(wiretap.Noop["UpdateFile"]):
        reason: Annotated[str, wiretap.Detail(), wiretap.Remark("Reason")]
