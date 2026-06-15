import logging
import random
import time

import wiretap

from core.contracts import (
    DeleteFile,
    DeleteFiles,
    DownloadFile,
    ImportDocument,
    ParseDocument,
    ReadFile,
    SaveRecord,
    UpdateFile,
    ValidateRecord,
    Workflow,
)
from wiretap import StatusLogOptions


def pause(min_ms: int = 2, max_ms: int = 12) -> None:
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def scenario_buzz_okay() -> None:
    with wiretap.begin_buzz(ReadFile(path="/data/in/customers.csv")) as read:
        pause()
        read.set_status(ReadFile.Okay(bytes_read=1600, line_count=4))


def scenario_buzz_fail() -> None:
    with wiretap.begin_buzz(DeleteFile(path="/data/in/archive.tmp")) as delete:
        try:
            pause()
            raise PermissionError("File is locked by another process.")
        except PermissionError as e:
            delete.set_status(DeleteFile.Fail(exception=e))


def scenario_buzz_void() -> None:
    with wiretap.begin_buzz(DownloadFile(url="https://example.test/customers.csv", target_path="/data/in/customers.csv")):
        # core: Intentionally omits the final status so auto-void is visible.
        pause()


def scenario_buzz_noop() -> None:
    with wiretap.begin_buzz(DownloadFile(url="https://example.test/customers.csv", target_path="/data/in/customers.csv")) as download:
        pause()
        download.set_status(DownloadFile.Noop())


def scenario_buzz_nesting() -> None:
    with wiretap.begin_buzz(Workflow.ExecuteStep(step_index=1)) as step:
        logging.info("This is a native log message inside a wiretap scope.")
        pause()
        step.set_status(Workflow.ExecuteStep.Okay(items_processed=1))


def scenario_buzz_with_state_item() -> None:
    with wiretap.begin_buzz(DownloadFile(url="https://example.test/customers.csv", target_path="/data/in/customers.csv")) as download:
        pause()
        download.set_status(DownloadFile.Okay(status_code=304, bytes_received=0))


def scenario_buzz_with_message_part() -> None:
    with wiretap.begin_buzz(ReadFile(path="/data/in/customers.csv")) as read:
        pause()
        read.set_status(ReadFile.Okay(bytes_read=1600, line_count=4))


def scenario_snap_okay() -> None:
    wiretap.log_snap(SaveRecord(row_index=1, record_id="customer-001"), SaveRecord.Okay())


def scenario_snap_noop() -> None:
    wiretap.log_snap(
        UpdateFile(path="/data/in/customers.csv"),
        UpdateFile.Noop(reason="download response matches local content"),
    )


def scenario_bulk_default() -> None:
    logging.info("This is a log message outside of any activity.")

    with wiretap.begin_bulk(DeleteFiles()) as bulk:
        for path in [
            "/path/to/one.txt",
            "/path/to/two.txt",
            "/path/to/archive.tmp",
        ]:
            with bulk.begin_item(DeleteFile(path=path)) as item:
                pause()
                if path.endswith(".tmp"):
                    item.set_status(DeleteFile.Fail(exception=ValueError("Temporary files are not deleted by this workflow.")))
                    continue

                item.set_status(DeleteFile.Okay())

        bulk.set_status(DeleteFiles.Okay())


def scenario_bulk_options() -> None:
    with wiretap.begin_bulk(ParseDocument(document_type="csv")) as parse:
        for row_index, is_valid in [
            (1, True),
            (2, False),
            (3, True),
        ]:
            with parse.begin_item(ValidateRecord(row_index=row_index)) as item:
                pause()
                if not is_valid:
                    item.set_status(ValidateRecord.Fail(exception=ValueError("Missing email."), field_name="email"))
                    continue

                item.set_status(ValidateRecord.Okay())

        parse.set_status(ParseDocument.Okay(records_parsed=3))


def scenario_quick_buzz() -> None:
    with wiretap.begin_buzz(wiretap.QuickBuzz(name="QuickCheck", path="/tmp/customers.csv")) as scope:
        pause()
        scope.set_status(wiretap.QuickBuzz.Okay(message="quick buzz complete", rows=4))


def scenario_quick_snap() -> None:
    wiretap.log_snap(wiretap.QuickSnap(name="CacheLookup", key="customer-004"), wiretap.QuickSnap.Noop(message="No cached record."))


def scenario_quick_bulk() -> None:
    with wiretap.begin_bulk(
            wiretap.QuickBulk(
                name="QuickImport",
                source="runtime.csv",
                item_status_log_policy=StatusLogOptions.NONE,
            )
    ) as bulk:
        for row_index in range(1, 4):
            with bulk.begin_item(wiretap.QuickBuzz(name="QuickValidateRow", row_index=row_index)) as item:
                pause()
                item.set_status(wiretap.QuickBuzz.Okay(message="row accepted"))

        bulk.set_status(wiretap.QuickBulk.Okay(message="quick bulk complete"))


def scenario_status_overwrite_warning() -> None:
    with wiretap.begin_buzz(ImportDocument(source="customers.csv")) as document:
        pause()
        document.set_status(ImportDocument.Okay(records_saved=2))
        # case: Intentionally overwrites the final status, so the internal logger shows the anomaly.
        document.set_status(ImportDocument.Fail(exception=RuntimeError("Late import failure discovered after summary.")))


def scenario_document_import() -> None:
    with wiretap.begin_buzz(ReadFile(path="/data/in/customers.csv")) as read:
        pause()
        read.set_status(ReadFile.Okay(bytes_read=1600, line_count=4))

    records_saved = 0
    with wiretap.begin_bulk(ParseDocument(document_type="csv")) as parse:
        for row_index, record_id, is_valid in [
            (1, "customer-001", True),
            (2, "customer-002", False),
            (3, "customer-003", True),
        ]:
            with parse.begin_item(ValidateRecord(row_index=row_index)) as item:
                pause()
                if not is_valid:
                    item.set_status(ValidateRecord.Fail(exception=ValueError("Missing email."), field_name="email"))
                    continue

                wiretap.log_snap(SaveRecord(row_index=row_index, record_id=record_id), SaveRecord.Okay())
                records_saved += 1
                item.set_status(ValidateRecord.Okay())

        parse.set_status(ParseDocument.Okay(records_parsed=3))

    with wiretap.begin_buzz(ImportDocument(source="customers.csv")) as document:
        pause()
        document.set_status(ImportDocument.Okay(records_saved=records_saved))


def scenarios() -> None:
    scenario_buzz_okay()
    scenario_buzz_fail()
    scenario_buzz_void()
    scenario_buzz_noop()
    scenario_buzz_nesting()
    scenario_buzz_with_state_item()
    scenario_buzz_with_message_part()
    scenario_snap_okay()
    scenario_snap_noop()
    scenario_bulk_default()
    scenario_bulk_options()
    scenario_quick_buzz()
    scenario_quick_snap()
    scenario_quick_bulk()
    scenario_status_overwrite_warning()
    scenario_document_import()


if __name__ == "__main__":
    wiretap.ConfigureLogging.from_yaml(r"..\..\cfg\wiretap.yml")
    scenarios()
    # with wiretap.Configuration(compose_message=...):
