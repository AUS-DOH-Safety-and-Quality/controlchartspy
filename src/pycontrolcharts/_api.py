"""Public chart constructors mirroring the R package."""

from collections.abc import Iterable, Mapping
from typing import Any

from ._data import (
    TOOLTIPS,
    Column,
    Columns,
    Data,
    Settings,
    apply_padding,
    prepare_aggregations,
    prepare_data,
    prepare_settings,
    prepare_title,
)
from ._engine import engine, render
from ._limits import funnel_limits, funnel_lines, spc_limits
from ._result import ControlChart, StaticPlot, dimension

Title = str | Mapping[str, object] | None
ReturnObjs = str | Iterable[str]


def _defaults(chart_type: str, group: str | None) -> dict[str, Any]:
    settings = engine().defaults(chart_type)
    settings["tooltips"] = TOOLTIPS.copy()
    if group is None:
        return settings
    if group not in settings:
        raise ValueError(f"'{group}' is not a valid settings group.")
    group_settings: dict[str, Any] = settings[group]
    return group_settings


def spc_default_settings(group: str | None = None) -> dict[str, Any]:
    """Return all SPC defaults, or one settings group, as a fresh dictionary."""
    return _defaults("spc", group)


def funnel_default_settings(group: str | None = None) -> dict[str, Any]:
    """Return all funnel defaults, or one settings group, as a fresh dictionary."""
    return _defaults("funnel", group)


def _create(
    chart_type: str,
    data: Data,
    keys: Column,
    numerators: Column,
    optional: Mapping[str, Column | None],
    indicators: Columns | None,
    tooltips: Columns | None,
    aggregations: Mapping[str, str] | None,
    title: Title,
    settings: Mapping[str, Settings | None],
    tooltip_settings: Settings | None,
    width: float | None,
    height: float | None,
    return_objs: ReturnObjs,
) -> ControlChart:
    if isinstance(return_objs, str):
        return_objs = (return_objs,)
    outputs = set(return_objs)
    valid = {"static_plot", "limits"}
    if chart_type == "funnel":
        valid.add("limit_lines")
    if outputs - valid:
        raise ValueError(f"Invalid return_objs: {', '.join(sorted(outputs - valid))}.")
    width = dimension(width, 640)
    height = dimension(height, 400)
    if tooltip_settings is not None:
        if not isinstance(tooltip_settings, Mapping):
            raise TypeError("tooltip_settings must be a mapping.")
        if set(tooltip_settings) - TOOLTIPS.keys():
            raise ValueError("Invalid tooltip setting.")
    raw_data, order = prepare_data(
        data, keys, numerators, optional, indicators, tooltips, chart_type == "spc"
    )
    if "static_plot" in outputs and raw_data.get("indicators"):
        groups = set(zip(*raw_data["indicators"].values()))
        if len(groups) > 1:
            raise ValueError(
                "Grouped SPC charts support limits only; use return_objs='limits'."
            )
    defaults = _defaults(chart_type, None)
    input_settings, conditional = prepare_settings(settings, defaults, order)
    title_settings = prepare_title(title)
    updates = engine().call(
        "makeUpdateValues",
        raw_data,
        input_settings,
        prepare_aggregations(aggregations),
        conditional,
        list(dict.fromkeys(raw_data["categories"])),
    )
    views = updates["dataViews"]
    apply_padding(chart_type, views, defaults, title_settings)
    result = ControlChart()
    if not outputs:
        return result
    raw = render(
        chart_type,
        views,
        title_settings,
        width,
        height,
        "static_plot" in outputs,
        bool(outputs & {"limits", "limit_lines"}),
    )
    if "static_plot" in outputs:
        result.static_plot = StaticPlot(
            chart_type, raw["svg"], width, height, views, title_settings
        )
    if chart_type == "funnel" and outputs & {"limits", "limit_lines"}:
        lines = funnel_lines(raw, settings.get("lines") or {})
        if "limit_lines" in outputs:
            result.limit_lines = lines
        if "limits" in outputs:
            result.limits = funnel_limits(raw, lines, settings.get("outliers") or {})
    elif chart_type == "spc" and "limits" in outputs:
        result.limits = spc_limits(raw, settings.get("outliers") or {})
        result.indicator_names = raw["indicatorVarNames"]
    return result


def spc(
    data: Data,
    keys: Column,
    numerators: Column,
    denominators: Column | None = None,
    groupings: Column | None = None,
    indicators: Columns | None = None,
    xbar_sds: Column | None = None,
    tooltips: Columns | None = None,
    labels: Column | None = None,
    aggregations: Mapping[str, str] | None = None,
    title: Title = None,
    canvas_settings: Settings | None = None,
    spc_settings: Settings | None = None,
    outlier_settings: Settings | None = None,
    nhs_icon_settings: Settings | None = None,
    scatter_settings: Settings | None = None,
    line_settings: Settings | None = None,
    x_axis_settings: Settings | None = None,
    y_axis_settings: Settings | None = None,
    date_settings: Settings | None = None,
    label_settings: Settings | None = None,
    tooltip_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs = ("static_plot", "limits"),
) -> ControlChart:
    """Calculate SPC limits and/or a static SVG using R's argument and settings names."""
    return _create(
        "spc",
        data,
        keys,
        numerators,
        {
            "denominators": denominators,
            "groupings": groupings,
            "xbar_sds": xbar_sds,
            "labels": labels,
        },
        indicators,
        tooltips,
        aggregations,
        title,
        {
            "canvas": canvas_settings,
            "spc": spc_settings,
            "outliers": outlier_settings,
            "nhs_icons": nhs_icon_settings,
            "scatter": scatter_settings,
            "lines": line_settings,
            "x_axis": x_axis_settings,
            "y_axis": y_axis_settings,
            "dates": date_settings,
            "labels": label_settings,
        },
        tooltip_settings,
        width,
        height,
        return_objs,
    )


def funnel(
    data: Data,
    keys: Column,
    numerators: Column,
    denominators: Column,
    tooltips: Columns | None = None,
    labels: Column | None = None,
    aggregations: Mapping[str, str] | None = None,
    title: Title = None,
    canvas_settings: Settings | None = None,
    funnel_settings: Settings | None = None,
    outlier_settings: Settings | None = None,
    scatter_settings: Settings | None = None,
    line_settings: Settings | None = None,
    x_axis_settings: Settings | None = None,
    y_axis_settings: Settings | None = None,
    label_settings: Settings | None = None,
    tooltip_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs = ("static_plot", "limits"),
) -> ControlChart:
    """Calculate funnel limits, limit lines, and/or a static SVG using R's settings."""
    return _create(
        "funnel",
        data,
        keys,
        numerators,
        {"denominators": denominators, "labels": labels},
        None,
        tooltips,
        aggregations,
        title,
        {
            "canvas": canvas_settings,
            "funnel": funnel_settings,
            "outliers": outlier_settings,
            "scatter": scatter_settings,
            "lines": line_settings,
            "x_axis": x_axis_settings,
            "y_axis": y_axis_settings,
            "labels": label_settings,
        },
        tooltip_settings,
        width,
        height,
        return_objs,
    )
