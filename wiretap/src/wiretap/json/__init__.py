from .json_multi_encoder import JSONMultiEncoder


def json_key(value: str) -> str:
    return f"${value}"
