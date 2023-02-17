from typing import Dict
from .wiretap import AttachDetails


def _layer(name: str) -> AttachDetails:
    def attach_layer(details: Dict) -> None:
        details["layer"] = name.lower()

    return attach_layer


def presentation() -> AttachDetails:
    return _layer(presentation.__name__)


def application() -> AttachDetails:
    return _layer(application.__name__)


def business() -> AttachDetails:
    return _layer(business.__name__)


def persistence() -> AttachDetails:
    return _layer(persistence.__name__)


def database() -> AttachDetails:
    return _layer(database.__name__)
