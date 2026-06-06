from __future__ import annotations


class _Forgiving(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"  # core: leave the hole visible rather than raise.
