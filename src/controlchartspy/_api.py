"""Public chart constructors mirroring the R package."""

from collections.abc import Iterable, Mapping
from typing import Any

from ._data import (
    TOOLTIPS,
    Column,
    Columns,
    Data,
    Record,
    Settings,
    apply_padding,
    prepare_aggregations,
    prepare_data,
    prepare_settings,
    prepare_title,
)
from ._engine import engine, render
from ._limits import funnel_limits, funnel_lines, misc_limits, spc_limits
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
    """Return the default settings for SPC charts, optionally for one group."""
    return _defaults("spc", group)


def funnel_default_settings(group: str | None = None) -> dict[str, Any]:
    """Return the default settings for funnel plots, optionally for one group."""
    return _defaults("funnel", group)


def misc_default_settings(group: str | None = None) -> dict[str, Any]:
    """Return the default settings for sigma charts, optionally for one group."""
    return _defaults("misc", group)


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
    else:
        return_objs = tuple(return_objs)
    prepared = prepare_data(
        data, keys, numerators, optional, indicators, tooltips, chart_type == "spc"
    )
    raw_data = prepared[0]
    order = prepared[1]
    if "static_plot" in return_objs and raw_data.get("indicators"):
        groups = set(zip(*raw_data["indicators"].values()))
        if len(groups) > 1:
            raise ValueError(
                "Grouped SPC charts support limits only; use return_objs='limits'."
            )
    return _create_chart(
        chart_type, raw_data, order, prepare_aggregations(aggregations), title, settings,
        tooltip_settings, width, height, return_objs,
    )


def _prepare_views(
    chart_type: str,
    raw_data: Record,
    order: list[int],
    aggregations: Mapping[str, str],
    title: Title,
    settings: Mapping[str, Settings | None],
) -> tuple[list[Any], dict[str, Any]]:
    defaults = _defaults(chart_type, None)
    prepared = prepare_settings(settings, defaults, order)
    input_settings = prepared[0]
    conditional = prepared[1]
    title_settings = prepare_title(title)
    updates = engine().call(
        "makeUpdateValues",
        raw_data,
        input_settings,
        aggregations,
        conditional,
        list(dict.fromkeys(raw_data["categories"])),
    )
    views = updates["dataViews"]
    apply_padding(chart_type, views, defaults, title_settings)
    return views, title_settings


def _create_chart(
    chart_type: str,
    raw_data: Record,
    order: list[int],
    aggregations: Mapping[str, str],
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
    prepared = _prepare_views(
        chart_type, raw_data, order, aggregations, title, settings
    )
    views = prepared[0]
    title_settings = prepared[1]
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
    elif chart_type == "misc" and "limits" in outputs:
        result.limits = misc_limits(raw)
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
    """Generate a statistical process control (SPC) chart and calculate control limits."""
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
    """Generate a funnel plot and calculate control limits."""
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
