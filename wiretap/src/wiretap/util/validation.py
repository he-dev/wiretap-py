import sys
from types import get_original_bases
from typing import Any, ForwardRef, TypeVar, evaluate_forward_ref, get_args

from wiretap.core.activity import Buzz, Snap
from wiretap.util.activity import Activity, ActivityStatus

_STATUS_DECLARATION_HINT = 'Declare it with a string activity reference, for example: class Okay(wiretap.Okay["MyActivity"]).'
T = TypeVar("T")


class ValidationError(TypeError):
    pass


class ValueNotActivity(ValidationError):
    pass


class ValueNotBuzz(ValidationError):
    pass


class ValueNotSnap(ValidationError):
    pass


class ValueNotStatus(ValidationError):
    pass


class InvalidStatusBaseDeclaration(ValidationError):
    pass


class MissingStatusActivityDeclaration(ValidationError):
    pass


class InvalidStatusActivityReference(ValidationError):
    pass


class StatusActivityReferenceNotActivity(ValidationError):
    pass


class StatusDoesNotMatchActivity(ValidationError):
    pass


def ensure_is_of(value: Any, expected_type: type[T], error_type: type[ValidationError]) -> None:
    if not isinstance(value, expected_type):
        raise error_type(f"Expected {expected_type.__qualname__}, got {type(value).__qualname__}.")


def ensure_is_activity(value: Any) -> None:
    ensure_is_of(value, Activity, ValueNotActivity)


def ensure_is_buzz(value: Any) -> None:
    ensure_is_of(value, Buzz, ValueNotBuzz)


def ensure_is_snap(value: Any) -> None:
    ensure_is_of(value, Snap, ValueNotSnap)


def ensure_is_status(value: Any) -> None:
    ensure_is_of(value, ActivityStatus, ValueNotStatus)


def ensure_status_matches_activity(activity: Activity, status: ActivityStatus[Any]) -> None:
    ensure_is_activity(activity)
    ensure_is_status(status)

    # note: For DeleteFile(path="x") and DeleteFile.Okay(), these are DeleteFile and DeleteFile.Okay.
    activity_type = type(activity)
    status_type = type(status)
    required_activity_name = activity_type.__qualname__

    try:
        status_activity_name = get_status_activity_name(status_type)
    except ValidationError as error:
        raise StatusDoesNotMatchActivity(
            f"{status_type.__qualname__} cannot be used while logging {required_activity_name}. "
            "Wiretap could not determine which activity the status belongs to."
        ) from error

    if status_activity_name != required_activity_name:
        raise StatusDoesNotMatchActivity(
            f"The current activity is {required_activity_name}, so it can only log statuses declared for "
            f"{required_activity_name}. {status_type.__qualname__} is declared for {status_activity_name}."
        )


def get_status_activity_name(status_type: type[ActivityStatus[Any]]) -> str:
    # note: Return a tuple like: (wiretap.core.activity_status.Okay[ForwardRef('ReadFile')],)
    bases = get_original_bases(status_type)

    # note: Status is expected to have exactly one base like wiretap.Okay[ForwardRef("DeleteFile")]
    if len(bases) != 1:
        raise InvalidStatusBaseDeclaration(
            f"Activity status are expected to have exactly one base but {status_type.__qualname__} does not follow this pattern: "
            f"It has {len(bases)} base declarations. {_STATUS_DECLARATION_HINT}"
        )

    # note: Return a tuple like: (ForwardRef('ReadFile'),)
    args = get_args(bases[0])
    if len(args) != 1:
        raise MissingStatusActivityDeclaration(
            f"{status_type.__qualname__} does not say which activity it belongs to. "
            f"{_STATUS_DECLARATION_HINT}"
        )

    # note: A wiretap status uses one generic argument: the activity contract, e.g., ForwardRef("DeleteFile").
    activity_arg = args[0]

    if not isinstance(activity_arg, ForwardRef):
        raise InvalidStatusActivityReference(
            f"{status_type.__qualname__} uses {activity_arg!r} as its activity reference. "
            f"Wiretap needs a string reference so nested activity contracts can resolve correctly. "
            f"{_STATUS_DECLARATION_HINT}"
        )

    # note: Resolve ForwardRef("DeleteFile") in the module where DeleteFile.Okay was declared.
    module = sys.modules.get(status_type.__module__)
    resolved = evaluate_forward_ref(
        activity_arg,
        owner=status_type,
        globals=vars(module) if module is not None else None,
        locals=vars(module) if module is not None else None,
    )

    if not isinstance(resolved, type):
        raise StatusActivityReferenceNotActivity(
            f"The activity reference on {status_type.__qualname__} resolved to {resolved!r}, "
            f"not an activity type. Check the name in the status declaration."
        )

    # note: __qualname__ preserves nested names like Workflow.ExecuteStep.
    return resolved.__qualname__
