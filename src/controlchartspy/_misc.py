"""Multi-indicator sigma charts delegated to the native Funnel visual."""

from collections.abc import Mapping

from ._api import ReturnObjs, Title, funnel
from ._data import Column, Columns, Data, Settings, is_sequence, label, missing
from ._result import ControlChart


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
    tooltip_settings: Settings | None = None,
    width: float | None = None,
    height: float | None = None,
    return_objs: ReturnObjs = ("static_plot", "limits"),
) -> ControlChart:
    """Delegate to funnel with indicator columns and a selected group."""
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
        misc_settings={**(misc_settings or {}), "group": label(target)},
        outlier_settings=outlier_settings,
        scatter_settings=scatter_settings,
        line_settings=line_settings,
        x_axis_settings=x_axis_settings,
        y_axis_settings=y_axis_settings,
        label_settings=label_settings,
        tooltip_settings=tooltip_settings,
        width=width,
        height=height,
        return_objs=return_objs,
    )
