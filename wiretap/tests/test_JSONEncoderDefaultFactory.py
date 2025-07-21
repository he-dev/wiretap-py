import json
import pathlib

from wiretap.util.logging import UUIDEncoder, PathEncoder, DateTimeEncoder, JSONEncoderDefaultFactory


def test_create_func_uses_custom_encoders():
    encoders = [UUIDEncoder(), PathEncoder(), DateTimeEncoder()]
    default_func = JSONEncoderDefaultFactory.create_func(encoders)

    j = json.dumps(
        {"path": pathlib.Path("c:/foo/bar/baz.txt")},
        default=default_func
    )
    assert j == '{"path": "c:/foo/bar/baz.txt"}'
