import logging

import yaml

import wiretap

from core.contracts import (
    DeleteFile,
    DeleteFileItem,
    DeleteFiles,
    DownloadFile,
    ImportDocument,
    ParseDocument,
    ReadFile,
    SaveRecord,
    ValidateRecord,
    Workflow,
)


def scenario_batch():
    logging.info("This is a log message outside of any activity.")

    with wiretap.begin_buzz(DeleteFiles()) as batch:
        for path in [
            "/path/to/one.txt",
            "/path/to/two.txt",
            "/path/to/archive.tmp",
        ]:
            try:
                with batch.begin_item(DeleteFileItem(path=path)) as item:
                    if path.endswith(".tmp"):
                        raise ValueError("Temporary files are not deleted by this workflow.")

                    item.set_status(DeleteFileItem.Okay()).log()
            except Exception as e:
                pass

        batch.log_status(DeleteFiles.Okay())


def scenario_scope():
    with wiretap.begin_buzz(Workflow.ExecuteStep(step_index=1)) as scope:
        try:
            # busy...
            logging.info("This is a log message.")
            wiretap.log_status(DeleteFile(path="/path/to/file.txt"), DeleteFile.Okay())

            # sleep(random.uniform(0.5, 1.0))
            scope.log_status(Workflow.ExecuteStep.Okay(items_processed=100))
        except Exception as e:
            scope.log_status(Workflow.ExecuteStep.Fail(exception=e))


def scenario_document_import():
    with wiretap.begin_buzz(ImportDocument(source="customers.csv")) as document:
        with wiretap.begin_buzz(ReadFile(path="/data/in/customers.csv")) as read:
            read.log_status(ReadFile.Okay(bytes_read=1600, line_count=4))

        records_saved = 0
        with wiretap.begin_buzz(ParseDocument(document_type="csv")) as parse:
            for row_index, record_id, is_valid in [
                (1, "customer-001", True),
                (2, "customer-002", False),
                (3, "customer-003", True),
            ]:
                with parse.begin_item(ValidateRecord(row_index=row_index)) as item:
                    if not is_valid:
                        item.set_status(ValidateRecord.Fail(exception=ValueError("Missing email."), field_name="email")).log()
                        continue

                    wiretap.log_status(SaveRecord(row_index=row_index, record_id=record_id), SaveRecord.Okay())
                    records_saved += 1
                    item.set_status(ValidateRecord.Okay()).log()

            # parse.log_status(ParseDocument.Okay(records_parsed=3))

        document.log_status(ImportDocument.Okay(records_saved=records_saved))


def scenario_lifecycle_variants():
    with wiretap.begin_buzz(DownloadFile(url="https://example.test/customers.csv", target_path="/data/in/customers.csv")) as download:
        download.log_status(DownloadFile.NotModified(status_code=304))

    with wiretap.begin_buzz(ParseDocument(document_type="csv")):
        # core: Intentionally omits the final status so ParseDocument's can_log_void behavior is visible.
        pass


def scenario_prototypes():
    with wiretap.begin_buzz(wiretap.PrototypeBuzz(name="Testing", foo="bar")) as scope:
        # wiretap.log_note("This is a beep.")

        with wiretap.begin_buzz(wiretap.PrototypeBuzz(name="Nested")) as nested:
            nested.log_status(wiretap.PrototypeBuzz.Okay(message="This is an okay."))

        scope.log_status(wiretap.PrototypeBuzz.Okay(message="This is an okay.", bar="baz"))
        pass
        # scope.log_status(wiretap.Prototyping.Okay(message="This is an okay."))
        # scope.log_status(Prototyping.Fail(message="This is a fail.", exception=None))


def scenarios():
    #scenario_batch()
    #scenario_scope()
    scenario_document_import()
    #scenario_lifecycle_variants()
    #scenario_prototypes()


if __name__ == "__main__":
    wiretap.Configure.Logging.from_yaml(r"..\..\cfg\wiretap.yml")
    scenarios()
    # wiretap.util.activity_scope
    #wiretap.util.activity_scope.ActivityScope.compose_message = None

