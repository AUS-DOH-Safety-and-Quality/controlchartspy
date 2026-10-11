"""Normalize Python columns and R-compatible chart settings."""

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from html import escape
from numbers import Integral, Real
from typing import Any, TypeGuard

Scalar = str | bool | int | float | None
Column = str | Iterable[object]
Columns = Column | Mapping[str, Column]
Data = Mapping[str, Column] | Sequence[Mapping[str, object]]
Settings = Mapping[str, Any]
Record = dict[str, Any]

AGGREGATIONS = {
    "numerators": "sum",
    "denominators": "sum",
    "groupings": "first",
    "xbar_sds": "first",
    "tooltips": "first",
    "labels": "first",
}
TOOLTIPS = {
    "ttip_font_size": 12,
    "ttip_font": "Arial, sans-serif",
    "ttip_font_color": "#000000",
    "ttip_background_color": "#E0E0E0",
    "ttip_opacity": 1,
    "ttip_border_radius": 5,
    "ttip_border_color": "#000000",
    "ttip_border_width": 1,
}
TITLE: dict[str, Any] = {
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
    data: Data, value: Column, name: str, length: int | None = None
) -> list[Any]:
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
    columns: Mapping[str, Column]
    if isinstance(value, Mapping):
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
    optional: Mapping[str, Column | None],
    indicators: Columns | None,
    tooltips: Columns | None,
    date_keys: bool,
) -> tuple[Record, list[int]]:
    keys = column(data, keys, "keys")
    n = len(keys)
    if n == 0:
        raise ValueError("No data present")
    if date_keys:
        for key in keys:
            if not (missing(key) or isinstance(key, (str, date))):
                raise TypeError("SPC keys must be dates or strings.")
    groups = named_columns(data, indicators, "indicators", n)
    tips = named_columns(data, tooltips, "tooltips", n)

    def sort_key(index: int) -> tuple[tuple[bool, Any], ...]:
        values: list[Any] = [values[index] for values in groups.values()]
        key = keys[index]
        if date_keys:
            key = label(key)
        values.append(key)
        return tuple((missing(value), value) for value in values)

    order = sorted(range(n), key=sort_key)
    raw: Record = {
        "crosstalk_identities": [str(i + 1) for i in order],
        "categories": [label(keys[i]) for i in order],
    }
    fields = {"numerators": numerators, **optional}
    for name, value in fields.items():
        if value is None:
            continue
        values = column(data, value, name, n)
        if name in ("groupings", "labels"):
            values = [label(item) for item in values]
            if name == "labels":
                values = [
                    escape(item, quote=False) if item is not None else None
                    for item in values
                ]
        else:
            values = [scalar(item) for item in values]
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
    defaults: Mapping[str, Settings],
    order: Sequence[int],
) -> tuple[dict[str, dict[str, Any]], bool]:
    result: dict[str, dict[str, Any]] = {}
    conditional = False
    n = len(order)
    for group, entries in settings.items():
        if entries is None:
            continue
        if not isinstance(entries, Mapping):
            raise TypeError(f"{group} settings must be a mapping.")
        result[group] = {}
        for name, value in entries.items():
            if name not in defaults[group]:
                raise ValueError(f"Invalid setting '{name}' in group '{group}'.")
            if is_sequence(value):
                value = list(value)
                if len(value) == 1:
                    value = value[0]
                elif len(value) == n:
                    conditional = True
                    result[group][name] = {
                        str(i + 1): setting_value(name, value[i]) for i in order
                    }
                    continue
                else:
                    raise ValueError(f"Setting '{name}' must have one or {n} values.")
            result[group][name] = setting_value(name, value)
    return result, conditional


def setting_value(name: str, value: object) -> Scalar:
    value = scalar(value)
    if name.endswith("_label") and value is not None:
        return escape(str(value), quote=False)
    return value


def prepare_aggregations(aggregations: Mapping[str, str] | None) -> dict[str, str]:
    result = AGGREGATIONS.copy()
    if aggregations is None:
        return result
    if not isinstance(aggregations, Mapping):
        raise TypeError("aggregations must be a mapping.")
    valid = {"first", "last", "sum", "mean", "min", "max", "median", "count"}
    for name, value in aggregations.items():
        if name not in result:
            raise ValueError(f"'{name}' is not a valid variable to aggregate.")
        if value not in valid:
            raise ValueError(f"'{value}' is not a valid aggregation.")
        result[name] = value
    return result


def prepare_title(title: str | Mapping[str, object] | None) -> dict[str, Any]:
    result = TITLE.copy()
    if isinstance(title, str):
        result["text"] = title
    elif title is not None:
        if not isinstance(title, Mapping):
            raise TypeError("title must be a string or a mapping.")
        for name, value in title.items():
            if name not in result:
                raise ValueError(f"Invalid title setting '{name}'.")
            if value is not None:
                result[name] = scalar(value)
    for name in ("text", "subtitle"):
        if result[name] is not None:
            result[name] = escape(str(result[name]), quote=False)
    return result


def apply_padding(
    chart_type: str,
    views: list[Any],
    defaults: Mapping[str, Settings],
    title: Mapping[str, Any],
) -> None:
    title_padding = 0.0
    if title["text"] is not None:
        title_padding = float(str(title["font_size"]).removesuffix("px")) + title["y"]
        if title["subtitle"] is not None:
            title_padding += float(str(title["subtitle_font_size"]).removesuffix("px"))
    for settings in views[0]["categorical"]["categories"][0]["objects"]:
        canvas = {**defaults["canvas"], **settings.get("canvas", {})}
        axis = {**defaults["x_axis"], **settings.get("x_axis", {})}
        canvas["upper_padding"] += title_padding
        canvas["left_padding"] += 50
        pad = 10 + axis["xlimit_tick_size"]
        if chart_type != "misc" and axis["xlimit_tick_rotation"] != 0:
            pad += 15
        if chart_type == "spc" and axis["xlimit_label"]:
            pad += 20
        canvas["lower_padding"] += pad
        settings["canvas"] = canvas
