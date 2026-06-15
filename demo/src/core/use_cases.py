import logging

import wiretap

from core.contracts import (
    DeleteFile,
    DeleteFiles,
    DownloadFile,
    ImportDocument,
    ParseDocument,
    ReadFile,
    SaveRecord,
    ValidateRecord,
    Workflow,
)
from wiretap import StatusLogOptions


def scenario_bulk():
    logging.info("This is a log message outside of any activity.")

    with wiretap.begin_bulk(DeleteFiles()) as bulk:
        for path in [
            "/path/to/one.txt",
            "/path/to/two.txt",
            "/path/to/archive.tmp",
        ]:
            try:
                with bulk.begin_item(DeleteFile(path=path)) as item:
                    if path.endswith(".tmp"):
                        raise ValueError("Temporary files are not deleted by this workflow.")

                    item.set_status(DeleteFile.Okay())
            except Exception as e:
                pass

        bulk.set_status(DeleteFiles.Okay())


def scenario_scope():
    with wiretap.begin_buzz(Workflow.ExecuteStep(step_index=1)) as scope:
        try:
            # busy...
            logging.info("This is a log message.")
            with wiretap.begin_buzz(DeleteFile(path="/path/to/file.txt")) as delete:
                delete.set_status(DeleteFile.Okay())

            # sleep(random.uniform(0.5, 1.0))
            scope.set_status(Workflow.ExecuteStep.Okay(items_processed=100))
        except Exception as e:
            scope.set_status(Workflow.ExecuteStep.Fail(exception=e))


def scenario_document_import():
    with wiretap.begin_buzz(ImportDocument(source="customers.csv")) as document:
        with wiretap.begin_buzz(ReadFile(path="/data/in/customers.csv")) as read:
            read.set_status(ReadFile.Okay(bytes_read=1600, line_count=4))

        records_saved = 0
        with wiretap.begin_bulk(ParseDocument(document_type="csv")) as parse:
            for row_index, record_id, is_valid in [
                (1, "customer-001", True),
                (2, "customer-002", False),
                (3, "customer-003", True),
            ]:
                with parse.begin_item(ValidateRecord(row_index=row_index)) as item:
                    if not is_valid:
                        item.set_status(ValidateRecord.Fail(exception=ValueError("Missing email."), field_name="email"))
                        continue

                    wiretap.log_snap(SaveRecord(row_index=row_index, record_id=record_id), SaveRecord.Okay())
                    records_saved += 1
                    item.set_status(ValidateRecord.Okay())

            # parse.set_status(ParseDocument.Okay(records_parsed=3))

        document.set_status(ImportDocument.Okay(records_saved=records_saved))
        # case: Intentionally overwrites the final status, so the internal logger shows the anomaly.
        document.set_status(ImportDocument.Fail(exception=RuntimeError("Late import failure discovered after summary.")))


def scenario_lifecycle_variants():
    with wiretap.begin_buzz(DownloadFile(url="https://example.test/customers.csv", target_path="/data/in/customers.csv")) as download:
        download.set_status(DownloadFile.NotModified(status_code=304))

    with wiretap.begin_bulk(ParseDocument(document_type="csv")):
        # core: Intentionally omits the final status so ParseDocument's can_log_void behavior is visible.
        pass


def scenario_quick_activities():
    with wiretap.begin_buzz(wiretap.QuickBuzz(name="Testing", foo="bar")) as scope:
        # wiretap.log_note("This is a beep.")

        with wiretap.begin_buzz(wiretap.QuickBuzz(name="Nested")) as nested:
            nested.set_status(wiretap.QuickBuzz.Okay(message="This is an okay."))

        scope.set_status(wiretap.QuickBuzz.Okay(message="This is an okay.", bar="baz"))

        # scope.set_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.set_status(Prototyping.Fail(message="This is a fail.", exception=None))
    wiretap.log_snap(wiretap.QuickSnap(name="Finito"), wiretap.QuickSnap.Okay(message="This is okay.", exception=None))
    wiretap.log_snap(wiretap.QuickSnap(name="CacheLookup", key="customer-004"), wiretap.QuickSnap.Noop(message="No cached record."))
    wiretap.log_snap(wiretap.QuickSnap(name="WebhookSignature"), wiretap.QuickSnap.Fail(message="Invalid signature."))

    with wiretap.begin_bulk(wiretap.QuickBulk(name="QuickImport", source="runtime.csv", item_status_log_policy=StatusLogOptions.LAST)) as bulk:
        for row_index in range(1, 4):
            with bulk.begin_item(wiretap.QuickBuzz(name="QuickValidateRow", row_index=row_index)) as item:
                item.set_status(wiretap.QuickBuzz.Okay(message="row accepted"))

        bulk.set_status(wiretap.QuickBulk.Okay(message="quick bulk complete"))


def scenarios():
    #scenario_bulk()
    #scenario_scope()
    scenario_document_import()
    #scenario_lifecycle_variants()
    scenario_quick_activities()


if __name__ == "__main__":
    wiretap.ConfigureLogging.from_yaml(r"..\..\cfg\wiretap.yml")
    scenarios()
    # with wiretap.Configuration(compose_message=...):
