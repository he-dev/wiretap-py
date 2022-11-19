import logging

import wiretap.src.wiretap.wiretap as wiretap
from wiretap.src.wiretap.wiretap import UnitOfWork, UnitOfWorkScope, telemetry
from wiretap_handlers_sqlite.src.wiretap.handlers.sqlite import SQLiteHandler
from wiretap_handlers_sqlserver.src.wiretap.handlers.sqlserver import SqlServerHandler, SqlServerConnection


def initialize_logger() -> logging.Logger:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(style="{", fmt="{asctime} | {module}.{funcName} | {status} | {extra}", defaults={"status": "<status>", "extra": "<extra>"}))
    # sql_server_handler = SqlServerHandler(
    #    SqlServerConnection(server="localhost,1433", database="master", username="sa", password="blub123!"),
    #    "INSERT INTO log([timestamp], [scope], [status], [extra], [comment]) VALUES (?, ?, ?, ?, ?)"
    # )

    # handlers = [stream_handler, sql_server_handler]
    handlers = [stream_handler]

    logging.root.addHandler(stream_handler)

    logger = logging.Logger(UnitOfWork.__name__)
    for h in handlers:
        logger.addHandler(h)

    return logger



# @telemetry(extra={"layer": "application"})
@telemetry(**wiretap.APPLICATION)
def flow_decorator_test(value: int, scope: UnitOfWorkScope = None):
    scope.running(foo=value)
    raise ValueError
    pass


def flow_test():
    with UnitOfWork(module="x", name="custom") as scope:
        # uow.started("Custom flow.")
        # flow.state(foo="bar")
        # if True:
        #    flow.altered("The value was true.")
        scope.running(metadata={"foo": "bar"})
        try:
            raise ValueError
        except:
            scope.canceled()


if __name__ == "__main__":
    flow_test()
    flow_decorator_test(7)
