from typing import Dict


def _layer(details: Dict, name: str):
    details["layer"] = name.lower()


def presentation(details: Dict) -> None:
    return _layer(details, presentation.__name__)


def application(details: Dict) -> None:
    return _layer(details, application.__name__)


def business(details: Dict) -> None:
    return _layer(details, business.__name__)


def persistence(details: Dict) -> None:
    return _layer(details, persistence.__name__)


def database(details: Dict) -> None:
    return _layer(details, database.__name__)
