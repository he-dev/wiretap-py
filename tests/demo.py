import logging
from typing import List
from src.wiretap.handlers.sqlserver import SqlServerHandler, SqlServerConnection
from src.wiretap.wiretap import UnitOfWork, UnitOfWorkScope


def initialize_logger() -> logging.Logger:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(style="{", fmt="{asctime} | {module}.{funcName} | {flow} | {message}", defaults={"flow": "<flow>", "message": "<message>"}))
    sql_server_handler = SqlServerHandler(
        SqlServerConnection(server="localhost,1433", database="master", username="sa", password="blub123!"),
        "INSERT INTO log([timestamp], [scope], [status], [extra], [comment]) VALUES (?, ?, ?, ?, ?)"
    )

    handlers = [stream_handler, sql_server_handler]

    logger = logging.Logger(UnitOfWork.__name__)
    for h in handlers:
        logger.addHandler(h)

    return logger


UnitOfWork.logger = initialize_logger()


@UnitOfWork(extra={"layer": "application"})
def flow_decorator_test(value: int, scope: UnitOfWorkScope = None):
    scope.running(metadata={"foo": value})
    raise ValueError
    pass


def flow_test():
    with UnitOfWork(name="custom") as scope:
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
