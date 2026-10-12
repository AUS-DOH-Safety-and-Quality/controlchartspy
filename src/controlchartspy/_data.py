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
TitleSettings = dict[str, Scalar]
InputSettings = dict[str, dict[str, Scalar | dict[str, Scalar]]]
Record = dict[str, Scalar]
Limits = list[Record] | dict[str, "Limits"]
ChartType = Literal["spc", "funnel"]
ValueName = Literal["numerators", "denominators", "groupings", "xbar_sds", "labels"]


class _RawData(TypedDict):
    crosstalk_identities: list[str]
    categories: list[str | None]


class RawData(_RawData, total=False):
    numerators: list[Scalar]
    denominators: list[Scalar]
    groupings: list[Scalar]
    xbar_sds: list[Scalar]
    labels: list[Scalar]
    indicators: dict[str, list[str | None]]
    tooltips: dict[str, list[str | None]]


# Only the key category (index 0) carries objects.
class Category(TypedDict):
    objects: list[dict[str, SettingsGroup]]


class Categorical(TypedDict):
    categories: list[Category]


class DataView(TypedDict):
    categorical: Categorical


AGGREGATIONS: dict[str, str] = {
    "numerators": "sum",
    "denominators": "sum",
    "groupings": "first",
    "xbar_sds": "first",
    "tooltips": "first",
    "labels": "first",
}
TITLE: TitleSettings = {
    "text": None,
    "font_size": "16px",
    "font_weight": "bold",
    "font_family": "'Arial', sans-serif",
    "x": "50%",
    "y": 5,
    "text_anchor": "middle",
    "dominant_baseline": "hanging",
    "subtitle": None,
    "subtitle_font_size": "12px",
    "subtitle_font_weight": "normal",
}


def missing(value: object) -> bool:
    return value is None or (isinstance(value, Real) and math.isnan(value))


def is_sequence(value: object) -> TypeGuard[Iterable[object]]:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def is_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def validate_mapping(value: object, message: str) -> None:
    if not isinstance(value, Mapping):
        raise TypeError(message)


def number(settings: Mapping[str, Scalar], name: str) -> float:
    value = settings[name]
    if not isinstance(value, (int, float)):
        raise TypeError(f"Setting '{name}' must be a number.")
    return value


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
) -> tuple[RawData, list[int]]:
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

    def sort_key(index: int) -> tuple[tuple[bool, object], ...]:
        values: list[object] = [values[index] for values in groups.values()]
        key = key_values[index]
        if date_keys:
            key = label(key)
        values.append(key)
        return tuple((missing(value), value) for value in values)

    order = sorted(range(n), key=sort_key)
    raw: RawData = {
        "crosstalk_identities": [str(i + 1) for i in order],
        "categories": [label(key_values[i]) for i in order],
    }
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
        raw[name] = [values[i] for i in order]
    if groups:
        raw["indicators"] = {
            name: [values[i] for i in order] for name, values in groups.items()
        }
    if tips:
        raw["tooltips"] = {
            name: [values[i] for i in order] for name, values in tips.items()
        }
    return raw, order


def prepare_settings(
    settings: Mapping[str, Settings | None],
    defaults: Mapping[str, SettingsGroup],
    order: Sequence[int],
) -> tuple[InputSettings, bool]:
    result: InputSettings = {}
    conditional = False
    n = len(order)
    for group, entries in settings.items():
        if entries is None:
            continue
        validate_mapping(entries, f"{group} settings must be a mapping.")
        result[group] = {}
        for name, value in entries.items():
            if name not in defaults[group]:
                raise ValueError(f"Invalid setting '{name}' in group '{group}'.")
            if is_sequence(value):
                items = list(value)
                if len(items) == 1:
                    value = items[0]
                elif len(items) == n:
                    conditional = True
                    result[group][name] = {
                        str(i + 1): scalar(items[i]) for i in order
                    }
                    continue
                else:
                    raise ValueError(f"Setting '{name}' must have one or {n} values.")
            result[group][name] = scalar(value)
    return result, conditional


def prepare_aggregations(aggregations: Mapping[str, str] | None) -> dict[str, str]:
    result = AGGREGATIONS.copy()
    if aggregations is None:
        return result
    validate_mapping(aggregations, "aggregations must be a mapping.")
    valid = {"first", "last", "sum", "mean", "min", "max", "median", "count"}
    for name, value in aggregations.items():
        if name not in result:
            raise ValueError(f"'{name}' is not a valid variable to aggregate.")
        if value not in valid:
            raise ValueError(f"'{value}' is not a valid aggregation.")
        result[name] = value
    return result


def prepare_title(title: str | Mapping[str, object] | None) -> TitleSettings:
    result = TITLE.copy()
    if isinstance(title, str):
        result["text"] = title
    elif title is not None:
        validate_mapping(title, "title must be a string or a mapping.")
        for name, value in title.items():
            if name not in result:
                raise ValueError(f"Invalid title setting '{name}'.")
            if value is not None:
                result[name] = scalar(value)
    return result


def apply_padding(
    chart_type: ChartType,
    views: list[DataView],
    defaults: Mapping[str, SettingsGroup],
    title: TitleSettings,
) -> None:
    title_padding = 0.0
    if title["text"] is not None:
        title_padding = float(str(title["font_size"]).removesuffix("px")) + number(title, "y")
        if title["subtitle"] is not None:
            title_padding += float(str(title["subtitle_font_size"]).removesuffix("px"))
    for settings in views[0]["categorical"]["categories"][0]["objects"]:
        canvas = {**defaults["canvas"], **settings.get("canvas", {})}
        axis = {**defaults["x_axis"], **settings.get("x_axis", {})}
        canvas["upper_padding"] = number(canvas, "upper_padding") + title_padding
        canvas["left_padding"] = number(canvas, "left_padding") + 50
        pad = 10 + number(axis, "xlimit_tick_size")
        if axis["xlimit_tick_rotation"] != 0:
            pad += 15
        if chart_type == "spc" and axis["xlimit_label"]:
            pad += 20
        canvas["lower_padding"] = number(canvas, "lower_padding") + pad
        settings["canvas"] = canvas
