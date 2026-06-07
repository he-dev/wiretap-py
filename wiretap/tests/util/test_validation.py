from dataclasses import dataclass

import pytest

import wiretap
from wiretap.util.validation import (
    InvalidStatusActivityReference,
    StatusDoesNotMatchActivity,
    ensure_status_matches_activity,
    InvalidStatusBaseDeclaration,
)


@dataclass
class ReadFile(wiretap.Buzz):
    path: str

    @dataclass
    class Okay(wiretap.Okay["ReadFile"]):
        pass


@dataclass
class DeleteFile(wiretap.Buzz):
    path: str

    @dataclass
    class Okay(wiretap.Okay["DeleteFile"]):
        pass


def test_ensure_status_matches_activity_accepts_status_declared_for_activity():
    ensure_status_matches_activity(ReadFile(path="input.txt"), ReadFile.Okay())


def test_ensure_status_matches_activity_rejects_status_declared_for_another_activity():
    with pytest.raises(StatusDoesNotMatchActivity) as error:
        ensure_status_matches_activity(ReadFile(path="input.txt"), DeleteFile.Okay())

    assert "DeleteFile.Okay" in str(error.value)


def test_ensure_status_matches_activity_rejects_unbound_status():
    with pytest.raises(StatusDoesNotMatchActivity) as error:
        ensure_status_matches_activity(ReadFile(path="input.txt"), wiretap.Okay())

    assert isinstance(error.value.__cause__, InvalidStatusBaseDeclaration)
