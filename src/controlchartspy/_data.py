"""Normalize Python columns and R-compatible chart settings."""

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from numbers import Integral, Real
from typing import Literal, TypedDict, TypeGuard

Scalar = str | bool | int | float | None
Column = str | Iterable[object]
Columns = Column | Mapping[str, Column]
Data = Mapping[str, object] | Sequence[Mapping[str, object]]
Settings = Mapping[str, object]
SettingsGroup = dict[str, Scalar]
Title = str | Mapping[str, object] | None
JSON = Scalar | list["JSON"] | dict[str, "JSON"]
Record = dict[str, Scalar]
Limits = list[Record] | dict[str, "Limits"]
ChartType = Literal["spc", "funnel"]
ValueName = Literal["numerators", "denominators", "groupings", "xbar_sds", "labels"]


class _RawData(TypedDict):
    categories: list[Scalar]


class RawData(_RawData, total=False):
    numerators: list[Scalar]
    denominators: list[Scalar]
    groupings: list[Scalar]
    xbar_sds: list[Scalar]
    labels: list[Scalar]
    indicators: dict[str, list[str | None]]
    tooltips: dict[str, list[str | None]]


def missing(value: object) -> bool:
    return value is None or (isinstance(value, Real) and math.isnan(value))


def is_sequence(value: object) -> TypeGuard[Iterable[object]]:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def is_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def scalar(value: object) -> Scalar:
    if missing(value):
        return None
    if isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        if not math.isfinite(value):
            raise ValueError("Infinite values are not supported.")
        return float(value)
    if isinstance(value, (date, datetime)):
        return label(value)
    raise TypeError(f"Unsupported value type: {type(value).__name__}")


def label(value: object) -> str | None:
    if missing(value):
        return None
    if isinstance(value, bool):
        return str(value).upper()
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Real):
        return format(value, ".15g")
    return str(value)


# Numbers stay numeric so that the engine orders them by value
def category(value: object) -> Scalar:
    if isinstance(value, Real) and not isinstance(value, bool):
        return scalar(value)
    return label(value)


def column(
    data: Data, value: object, name: str, length: int | None = None
) -> list[object]:
    if isinstance(value, str):
        if isinstance(data, Sequence):
            value = [row[value] for row in data]
        else:
            value = data[value]
    if not is_sequence(value):
        raise TypeError(f"{name} must be a column name or a sequence.")
    result = list(value)
    if length is not None and len(result) != length:
        raise ValueError(f"{name} must have one value per observation ({length}).")
    return result


def named_columns(
    data: Data, value: Columns | None, name: str, length: int
) -> dict[str, list[str | None]]:
    if value is None:
        return {}
    columns: Mapping[object, object]
    if is_mapping(value):
        columns = value
    elif isinstance(value, str):
        columns = {value: value}
    else:
        columns = {name: value}
    if not columns:
        raise ValueError(f"{name} must contain at least one column.")
    return {
        str(key): [label(item) for item in column(data, values, name, length)]
        for key, values in columns.items()
    }


def prepare_data(
    data: Data,
    keys: Column,
    numerators: Column,
    optional: Mapping[ValueName, Column | None],
    indicators: Columns | None,
    tooltips: Columns | None,
    date_keys: bool,
) -> RawData:
    key_values = column(data, keys, "keys")
    n = len(key_values)
    if n == 0:
        raise ValueError("No data present")
    if date_keys:
        for key in key_values:
            if not (missing(key) or isinstance(key, (str, date))):
                raise TypeError("SPC keys must be dates or strings.")
    groups = named_columns(data, indicators, "indicators", n)
    tips = named_columns(data, tooltips, "tooltips", n)
    raw: RawData = {"categories": [category(value) for value in key_values]}
    fields: dict[ValueName, Column | None] = {"numerators": numerators, **optional}
    for name, value in fields.items():
        if value is None:
            continue
        items = column(data, value, name, n)
        values: list[Scalar]
        if name in ("groupings", "labels"):
            values = [label(item) for item in items]
        else:
            values = [scalar(item) for item in items]
            if any(
                item is not None and not isinstance(item, (int, float))
                for item in values
            ):
                raise TypeError(f"{name} must contain numeric values.")
        raw[name] = values
    if groups:
        raw["indicators"] = groups
    if tips:
        raw["tooltips"] = tips
    return raw


def json_value(value: object) -> JSON:
    if is_mapping(value):
        return {str(key): json_value(item) for key, item in value.items()}
    if is_sequence(value):
        return [json_value(item) for item in value]
    return scalar(value)
