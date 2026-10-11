"""Multi-indicator sigma charts based on per-indicator funnel calculations."""

from collections.abc import Mapping
from typing import Any

from ._api import ReturnObjs, Title, _create_chart, _prepare_views, funnel_default_settings
from ._data import (
    Column,
    Columns,
    Data,
    Record,
    Settings,
    column,
    is_sequence,
    label,
    missing,
    named_columns,
    prepare_aggregations,
    prepare_data,
)
from ._engine import render
from ._limits import funnel_limits, funnel_lines
from ._result import ControlChart


def _normalise_settings(settings: Settings | None, n: int) -> dict[str, Any]:
    if settings is None:
        return {}
    if not isinstance(settings, Mapping):
        raise TypeError("Settings must be a mapping.")
    result = {}
    for name, value in settings.items():
        if is_sequence(value):
            value = list(value)
            if len(value) == 1:
                value = value[0]
            elif len(value) != n:
                raise ValueError(f"Setting '{name}' must have one or {n} values.")
        result[name] = value
    return result


def _slice_settings(settings: Settings, rows: list[int]) -> dict[str, Any]:
    result = {}
    for name, value in settings.items():
        if isinstance(value, list):
            value = [value[i] for i in rows]
        result[name] = value
    return result


def _value_suffix(settings: Settings) -> str:
    defaults = funnel_default_settings("funnel")
    values = defaults.copy()
    for name, value in settings.items():
        if isinstance(value, list):
            value = value[0]
        if value is not None:
            values[name] = value
    percent_labels = values["perc_labels"].lower()
    chart_type = values["chart_type"]
    multiplier = values["multiplier"]
    if percent_labels == "yes" or (
        percent_labels == "automatic" and chart_type == "PR" and multiplier in (1, 100)
    ):
        return "%"
    if chart_type == "PR" and multiplier != 1:
        return f" per {multiplier:,.0f}"
    return ""


def misc(
    data: Data,
    keys: Column,
    numerators: Column,
    denominators: Column,
    indicators: Column,
    target: object,
    groupings: Column | None = None,
    tooltips: Columns | None = None,
    aggregations: Mapping[str, str] | None = None,
    title: Title = None,
    funnel_settings: Settings | None = None,
    outlier_settings: Settings | None = None,
    canvas_settings: Settings | None = None,
    misc_settings: Settings | None = None,
    bar_settings: Settings | None = None,
    line_settings: Settings | None = None,
    x_axis_settings: Settings | None = None,
    y_axis_settings: Settings | None = None,
    tooltip_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs = ("static_plot", "limits"),
) -> ControlChart:
    """Plot a target's funnel z-scores by indicator, positive for improvement."""
    if missing(target) or is_sequence(target) or isinstance(target, Mapping):
        raise ValueError("target must be a single non-missing value.")
    target = label(target)
    key_values = [label(value) for value in column(data, keys, "keys")]
    n = len(key_values)
    if n == 0:
        raise ValueError("No data present")
    numerator_values = column(data, numerators, "numerators", n)
    denominator_values = column(data, denominators, "denominators", n)
    indicator_values = column(data, indicators, "indicators", n)
    grouping_values = [""] * n
    if groupings is not None:
        grouping_values = [
            label(value) for value in column(data, groupings, "groupings", n)
        ]
    tooltip_values = named_columns(data, tooltips, "tooltips", n)
    funnel_settings = _normalise_settings(funnel_settings, n)
    outlier_settings = _normalise_settings(outlier_settings, n)
    direction = outlier_settings.get("improvement_direction")
    if direction is None:
        direction = funnel_default_settings("outliers")["improvement_direction"]
    if not isinstance(direction, list):
        direction = [direction] * n
    groups: dict[str | None, list[int]] = {}
    for i in range(n):
        groups.setdefault(label(indicator_values[i]), []).append(i)
    aggregation_settings = prepare_aggregations(aggregations)
    records: list[Record] = []
    extras: dict[str, list[Any]] = {name: [] for name in tooltip_values}
    for indicator, rows in groups.items():
        directions = {direction[i] for i in rows}
        if len(directions) != 1 or not directions <= {"increase", "decrease"}:
            raise ValueError(
                "Each indicator must have one improvement_direction: "
                f"'increase' or 'decrease'. Invalid indicator: '{indicator}'."
            )
        funnel_rows = sorted(rows, key=lambda i: (missing(key_values[i]), key_values[i]))
        indicator_funnel = _slice_settings(funnel_settings, funnel_rows)
        indicator_outliers = _slice_settings(outlier_settings, funnel_rows)
        indicator_outliers["improvement_direction"] = direction[rows[0]]
        indicator_outliers["three_sigma"] = True
        population = {
            "key": [key_values[i] for i in funnel_rows],
            "numerator": [numerator_values[i] for i in funnel_rows],
            "denominator": [denominator_values[i] for i in funnel_rows],
        }
        tips = {
            name: [values[i] for i in funnel_rows]
            for name, values in tooltip_values.items()
        }
        prepared = prepare_data(
            population, "key", "numerator", {"denominators": "denominator"},
            None, tips or None, False,
        )
        prepared_views = _prepare_views(
            "funnel", prepared[0], prepared[1], aggregation_settings, None,
            {"funnel": indicator_funnel, "outliers": indicator_outliers},
        )
        views = prepared_views[0]
        raw = render("funnel", views, prepared_views[1], 640, 400, False, True)
        limits = funnel_limits(raw, funnel_lines(raw, {}), indicator_outliers)
        selected = None
        for row in limits:
            if row["group"] == target:
                selected = row
                break
        if selected is None:
            continue
        target_row = next(i for i in rows if key_values[i] == target)
        score = selected["z"]
        if direction[rows[0]] == "decrease":
            score = -score
        sig_figs = indicator_funnel.get("sig_figs")
        if sig_figs is None:
            sig_figs = funnel_default_settings("funnel")["sig_figs"]
        if isinstance(sig_figs, list):
            sig_figs = sig_figs[0]
        record = {
            "indicator": indicator,
            "grouping": grouping_values[target_row],
            "group": selected["group"],
            "z": selected["z"],
            "score": score,
            "outlier": selected["three_sigma"],
            "numerator": selected["numerator"],
            "denominator": selected["denominator"],
            "value": selected["value"],
            "ll99": selected["ll99"],
            "target": selected["target"],
            "ul99": selected["ul99"],
            "suffix": _value_suffix(indicator_funnel),
            "sig_figs": sig_figs,
        }
        records.append(record)
        categorical = views[0]["categorical"]
        target_index = categorical["categories"][0]["values"].index(target)
        for values in categorical["values"]:
            if values["source"]["roles"].get("tooltips"):
                extras[values["source"]["displayName"]].append(
                    values["values"][target_index]
                )
    if not records:
        raise ValueError(f"target '{target}' is not present in any indicator.")
    fields = {
        "categories": "indicator",
        "groupings": "grouping",
        "groups": "group",
        "scores": "score",
        "z_scores": "z",
        "outliers": "outlier",
        "numerators": "numerator",
        "denominators": "denominator",
        "values": "value",
        "ll99": "ll99",
        "targets": "target",
        "ul99": "ul99",
        "suffixes": "suffix",
        "sig_figs": "sig_figs",
    }
    raw_data: Record = {
        name: [row[field] for row in records] for name, field in fields.items()
    }
    raw_data["crosstalk_identities"] = [str(i + 1) for i in range(len(records))]
    raw_data["tooltips"] = extras
    result = _create_chart(
        "misc", raw_data, list(range(len(records))),
        {**dict.fromkeys(fields, "first"), "tooltips": "first"}, title,
        {
            "canvas": canvas_settings, "misc": misc_settings, "bars": bar_settings,
            "lines": line_settings, "x_axis": x_axis_settings, "y_axis": y_axis_settings,
        },
        tooltip_settings, width, height, return_objs,
    )
    result.target = target
    return result
