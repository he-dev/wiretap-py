from typing import Any, Protocol, runtime_checkable

from wiretap.util.data.details import DetailCollection, DetailOptions
from wiretap.util.data.dotted_name import DottedName
from wiretap.util.data.remarks import QuoteMode, QuoteStyle, RemarkCollection, RemarkOptions


class DetailBuilder:
    # core: The builder owns detail namespacing so sources only provide local dotted names.
    def __init__(
        self,
        root: DottedName,
        level: int,
        details: DetailCollection,
    ) -> None:
        self.root = root
        self.level = level
        self.details = details

    def add(
        self,
        name: DottedName,
        value: Any,
        *,
        options: DetailOptions | None = None,
    ) -> None:
        options = options or DetailOptions()
        # core: Ancestor builders have level > 0 and publish only explicitly cascading details.
        if self.level == 0 or options.cascade:
            self.details[_join(self.root, name)] = value


class RemarkBuilder:
    # core: Remarks can render explicit values or reuse values already collected as details.
    def __init__(
        self,
        root: DottedName,
        details: DetailCollection,
        remarks: RemarkCollection,
    ) -> None:
        self.root = root
        self.details = details
        self.remarks = remarks

    def add(
        self,
        name: DottedName,
        value: Any,
        *,
        options: RemarkOptions | None = None,
    ) -> None:
        options = options or RemarkOptions()
        self.remarks[name] = _render_remark(name, value, options)

    def detail(
        self,
        name: DottedName,
        *,
        options: RemarkOptions | None = None,
    ) -> None:
        # core: detail() uses the standard activity.state namespace to turn a detail into a remark.
        key = _join(self.root.activity.state, name)
        self.add(key, self.details.get(key), options=options)


@runtime_checkable
class DetailSource(Protocol):
    # core: User contracts implement this hook when annotations are not expressive enough.
    def details(self, builder: DetailBuilder) -> None: ...


@runtime_checkable
class RemarkSource(Protocol):
    # core: User contracts implement this hook for custom message wording.
    def remarks(self, builder: RemarkBuilder) -> None: ...


def _render_remark(name: DottedName, value: Any, options: RemarkOptions) -> str | None:
    # util: None creates a tracked but non-rendered remark, matching the collection's nullable values.
    if value is None:
        return None

    text = _format_value(value, options)
    text = _quote(text, options)
    label = options.label if options.label is not None else _default_label(name)
    return f"{label}{options.separator}{text}"


def _join(root: DottedName, name: DottedName) -> DottedName:
    return root.append(*name.parts)


def _format_value(value: Any, options: RemarkOptions) -> str:
    # util: Python formatting stays on the value, never on the dotted name.
    if options.format is None:
        return str(value)

    return options.format.format(value)


def _quote(value: str, options: RemarkOptions) -> str:
    if options.quote_mode is QuoteMode.NEVER:
        return value

    if options.quote_mode is QuoteMode.AUTO and not any(character.isspace() for character in value):
        return value

    quote = '"' if options.quote_style is QuoteStyle.DOUBLE else "'"
    return f"{quote}{value}{quote}"


def _default_label(name: DottedName) -> str:
    return name.parts[-1].replace("_", " ").capitalize() if name.parts else ""
