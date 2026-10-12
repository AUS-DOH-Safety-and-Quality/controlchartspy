"""Public chart constructors mirroring the R package."""

from collections.abc import Iterable, Mapping
from typing import overload

from ._data import (
    ChartType,
    Column,
    Columns,
    Data,
    DataView,
    RawData,
    Settings,
    SettingsGroup,
    TitleSettings,
    ValueName,
    apply_padding,
    prepare_aggregations,
    prepare_data,
    prepare_settings,
    prepare_title,
)
from ._engine import FunnelResult, SPCResult, engine, render, update_values
from ._limits import funnel_limits, funnel_lines, misc_limits, spc_limits
from ._result import ControlChart, StaticPlot, dimension

Title = str | Mapping[str, object] | None
ReturnObjs = str | Iterable[str]
Defaults = dict[str, SettingsGroup]


@overload
def _defaults(chart_type: ChartType, group: None) -> Defaults: ...


@overload
def _defaults(chart_type: ChartType, group: str) -> SettingsGroup: ...


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
    return_objs: ReturnObjs,
) -> ControlChart:
    if isinstance(return_objs, str):
        outputs = {return_objs}
    else:
        outputs = set(return_objs)
    prepared = prepare_data(
        data, keys, numerators, optional, indicators, tooltips, chart_type == "spc"
    )
    raw_data = prepared[0]
    order = prepared[1]
    indicator_columns = raw_data.get("indicators")
    if (
        chart_type == "spc"
        and "static_plot" in outputs
        and indicator_columns
        and any(len(set(column)) > 1 for column in indicator_columns.values())
    ):
        raise ValueError(
            "Grouped SPC charts support limits only; use return_objs='limits'."
        )
    aggregations = prepare_aggregations(aggregations)
    valid = {"static_plot", "limits"}
    if chart_type == "funnel" and not raw_data.get("indicators"):
        valid.add("limit_lines")
    if outputs - valid:
        raise ValueError(f"Invalid return_objs: {', '.join(sorted(outputs - valid))}.")
    width = dimension(width, 640)
    height = dimension(height, 400)
    prepared_views = _prepare_views(
        chart_type, raw_data, order, aggregations, title, settings
    )
    views = prepared_views[0]
    title_settings = prepared_views[1]
    result = ControlChart()
    if not outputs:
        return result
    static = "static_plot" in outputs
    limits = bool(outputs & {"limits", "limit_lines"})
    raw: SPCResult | FunnelResult
    if chart_type == "spc":
        raw = render(chart_type, views, title_settings, width, height, static, limits)
        if "limits" in outputs:
            result.limits = spc_limits(raw)
            result.indicator_names = raw["indicatorVarNames"]
    else:
        raw = render(chart_type, views, title_settings, width, height, static, limits)
        if raw_data.get("indicators"):
            if "limits" in outputs:
                result.limits = misc_limits(raw)
        elif limits:
            if "limit_lines" in outputs:
                result.limit_lines = funnel_lines(raw, settings.get("lines") or {})
            if "limits" in outputs:
                result.limits = funnel_limits(raw, settings.get("lines") or {})
    if static:
        result.static_plot = StaticPlot(
            chart_type, raw["svg"], width, height, views, title_settings
        )
    return result


def _prepare_views(
    chart_type: ChartType,
    raw_data: RawData,
    order: list[int],
    aggregations: Mapping[str, str],
    title: Title,
    settings: Mapping[str, Settings | None],
) -> tuple[list[DataView], TitleSettings]:
    defaults = _defaults(chart_type, None)
    prepared = prepare_settings(settings, defaults, order)
    input_settings = prepared[0]
    conditional = prepared[1]
    title_settings = prepare_title(title)
    views = update_values(raw_data, input_settings, aggregations, conditional)
    apply_padding(chart_type, views, defaults, title_settings)
    return views, title_settings


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
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs = ("static_plot", "limits"),
) -> ControlChart:
    """Generate a funnel plot, or a sigma chart when indicators are supplied."""
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
        },
        width,
        height,
        return_objs,
    )
