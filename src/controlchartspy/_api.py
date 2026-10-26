"""Public chart constructors mirroring the R package."""

import warnings
from collections.abc import Iterable, Mapping
from typing import overload

from ._data import (
    ChartType,
    Column,
    Columns,
    Data,
    Settings,
    SettingsGroup,
    Title,
    ValueName,
    category,
    is_sequence,
    json_value,
    missing,
    prepare_data,
)
from ._engine import Inputs, engine, render
from ._result import ControlChart, StaticPlot, dimension, tooltip_limits

ReturnObjs = str | Iterable[str]
Defaults = dict[str, SettingsGroup]


def _defaults(chart_type: ChartType, group: str | None) -> Defaults | SettingsGroup:
    settings = engine().defaults(chart_type)
    if group is None:
        return settings
    if group not in settings:
        raise ValueError(f"'{group}' is not a valid settings group.")
    return settings[group]


@overload
def spc_default_settings(group: None = None) -> Defaults: ...


@overload
def spc_default_settings(group: str) -> SettingsGroup: ...


def spc_default_settings(group: str | None = None) -> Defaults | SettingsGroup:
    """Return the default settings for SPC charts, optionally for one group."""
    return _defaults("spc", group)


@overload
def funnel_default_settings(group: None = None) -> Defaults: ...


@overload
def funnel_default_settings(group: str) -> SettingsGroup: ...


def funnel_default_settings(group: str | None = None) -> Defaults | SettingsGroup:
    """Return the default settings for funnel plots, optionally for one group."""
    return _defaults("funnel", group)


@overload
def misc_default_settings(group: None = None) -> Defaults: ...


@overload
def misc_default_settings(group: str) -> SettingsGroup: ...


def misc_default_settings(group: str | None = None) -> Defaults | SettingsGroup:
    """Return the default settings for sigma charts, optionally for one group."""
    return funnel_default_settings(group)


def _create(
    chart_type: ChartType,
    data: Data,
    keys: Column,
    numerators: Column,
    optional: Mapping[ValueName, Column | None],
    indicators: Columns | None,
    tooltips: Columns | None,
    aggregations: Mapping[str, str] | None,
    title: Title,
    settings: Mapping[str, Settings | None],
    width: float | None,
    height: float | None,
    return_objs: ReturnObjs | None,
) -> ControlChart:
    if return_objs is None:
        # Tables have no static plot; funnel indicators show the MISC chart instead of one
        table = settings.get("summary_table") or {}
        shows_table = (chart_type == "spc" and indicators is not None) or (
            indicators is None and table.get("show_table") is True
        )
        return_objs = "limits" if shows_table else ("static_plot", "limits")
    if isinstance(return_objs, str):
        outputs = {return_objs}
    else:
        outputs = set(return_objs)
    raw_data, tooltip_values = prepare_data(
        data, keys, numerators, optional, indicators, tooltips, chart_type == "spc"
    )
    valid = {"static_plot", "limits"}
    if chart_type == "funnel" and not raw_data.get("indicators"):
        valid.add("limit_lines")
    if outputs - valid:
        raise ValueError(f"Invalid return_objs: {', '.join(sorted(outputs - valid))}.")
    width = dimension(width, 640)
    height = dimension(height, 400)
    inputs: Inputs = {
        "raw_data": raw_data,
        "settings": json_value(settings),
        "aggregations": json_value(aggregations),
        "title": json_value(title),
    }
    result = ControlChart()
    if not outputs:
        return result
    static = "static_plot" in outputs
    limits = bool(outputs & {"limits", "limit_lines"})
    raw = render(chart_type, inputs, width, height, static, limits)
    for message in raw["warnings"]:
        warnings.warn(message, stacklevel=3)
    if "limits" in outputs:
        result.limits = tooltip_limits(
            raw["limits"],
            raw["rowIds"],
            raw["source_rows"],
            tooltip_values,
            (aggregations or {}).get("tooltips", "first"),
        )
    if "limit_lines" in outputs:
        result.limit_lines = raw["limitLines"]
    if static:
        result.static_plot = StaticPlot(chart_type, raw["svg"], width, height, inputs)
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
    summary_table_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs | None = None,
) -> ControlChart:
    """Generate a statistical process control (SPC) chart and calculate control limits.

    return_objs defaults to limits only when indicators are supplied or a summary
    table is shown, as tables have no static plot.
    """
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
            "summary_table": summary_table_settings,
        },
        width,
        height,
        return_objs,
    )


def funnel(
    data: Data,
    keys: Column,
    numerators: Column,
    denominators: Column,
    indicators: Columns | None = None,
    tooltips: Columns | None = None,
    labels: Column | None = None,
    aggregations: Mapping[str, str] | None = None,
    title: Title = None,
    canvas_settings: Settings | None = None,
    funnel_settings: Settings | None = None,
    misc_settings: Settings | None = None,
    outlier_settings: Settings | None = None,
    scatter_settings: Settings | None = None,
    line_settings: Settings | None = None,
    x_axis_settings: Settings | None = None,
    y_axis_settings: Settings | None = None,
    label_settings: Settings | None = None,
    summary_table_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs | None = None,
) -> ControlChart:
    """Generate a funnel plot, or a sigma chart when indicators are supplied.

    return_objs defaults to limits only when a summary table is shown without
    indicators, as tables have no static plot.
    """
    return _create(
        "funnel",
        data,
        keys,
        numerators,
        {"denominators": denominators, "labels": labels},
        indicators,
        tooltips,
        aggregations,
        title,
        {
            "canvas": canvas_settings,
            "funnel": funnel_settings,
            "misc": misc_settings,
            "outliers": outlier_settings,
            "scatter": scatter_settings,
            "lines": line_settings,
            "x_axis": x_axis_settings,
            "y_axis": y_axis_settings,
            "labels": label_settings,
            "summary_table": summary_table_settings,
        },
        width,
        height,
        return_objs,
    )


def misc(
    data: Data,
    keys: Column,
    numerators: Column,
    denominators: Column,
    indicators: Columns,
    target: object,
    *,
    tooltips: Columns | None = None,
    labels: Column | None = None,
    aggregations: Mapping[str, str] | None = None,
    title: Title = None,
    canvas_settings: Settings | None = None,
    funnel_settings: Settings | None = None,
    misc_settings: Settings | None = None,
    outlier_settings: Settings | None = None,
    scatter_settings: Settings | None = None,
    line_settings: Settings | None = None,
    x_axis_settings: Settings | None = None,
    y_axis_settings: Settings | None = None,
    label_settings: Settings | None = None,
    summary_table_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs | None = None,
) -> ControlChart:
    """Delegate to funnel with indicator columns and a selected group.

    Numeric targets match numeric keys by value.
    """
    if missing(target) or is_sequence(target) or isinstance(target, Mapping):
        raise ValueError("target must be a single non-missing value.")
    return funnel(
        data,
        keys,
        numerators,
        denominators,
        indicators=indicators,
        tooltips=tooltips,
        labels=labels,
        aggregations=aggregations,
        title=title,
        canvas_settings=canvas_settings,
        funnel_settings=funnel_settings,
        # Written as the keys are, so the engine names both alike
        misc_settings={**(misc_settings or {}), "group": category(target)},
        outlier_settings=outlier_settings,
        scatter_settings=scatter_settings,
        line_settings=line_settings,
        x_axis_settings=x_axis_settings,
        y_axis_settings=y_axis_settings,
        label_settings=label_settings,
        summary_table_settings=summary_table_settings,
        width=width,
        height=height,
        return_objs=return_objs,
    )
