"""Chart results and standalone SVG export."""

import math
import os
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path

from ._data import ChartType, DataView, Limits, Record, TitleSettings
from ._engine import render


def dimension(value: object, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("Chart dimensions must be positive numbers.")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Chart dimensions must be positive numbers.")
    return float(value)


def svg_string(svg: str, width: float, height: float) -> str:
    svg = svg.replace('dominant-baseline="hanging"', 'dy="0.8em"')
    svg = svg.replace('dominant-baseline="middle"', 'dy="0.35em"')
    return (
        f'<svg viewBox="0 0 {width:g} {height:g}" width="{width:g}px" '
        f'height="{height:g}px" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="0" y="0" width="100%" height="100%" fill="white"/>'
        f"{svg}</svg>"
    )


@dataclass
class StaticPlot:
    """A static SVG plot with its dimensions and rendering settings."""

    type: ChartType
    svg: str
    width: float
    height: float
    data_views: list[DataView] = field(repr=False)
    title_settings: TitleSettings = field(repr=False)

    def to_svg(self, width: float | None = None, height: float | None = None) -> str:
        """Return a complete SVG document, optionally rendered at a new size."""
        svg = self.svg
        if width is not None or height is not None:
            width = dimension(width, self.width)
            height = dimension(height, self.height)
            svg = render(
                self.type,
                self.data_views,
                self.title_settings,
                width,
                height,
                True,
                False,
            )["svg"]
        else:
            width = self.width
            height = self.height
        return svg_string(svg, width, height)

    def _repr_svg_(self) -> str:
        return self.to_svg()


@dataclass
class ControlChart:
    """A control chart containing the requested plot and calculated limits."""

    static_plot: StaticPlot | None = None
    limits: Limits | None = None
    limit_lines: list[Record] | None = None
    indicator_names: list[str] = field(default_factory=list[str])

    def save_plot(
        self,
        file: str | os.PathLike[str],
        width: float | None = None,
        height: float | None = None,
    ) -> None:
        """Save the static plot as SVG, optionally rendering at a new size."""
        if self.static_plot is None:
            raise ValueError(
                "This object has no static plot; request 'static_plot' in return_objs."
            )
        path = Path(file)
        if path.suffix.lower() != ".svg":
            raise ValueError("Only SVG output is supported.")
        path.write_text(self.static_plot.to_svg(width, height) + "\n", encoding="utf-8")

    def _repr_svg_(self) -> str | None:
        if self.static_plot is not None:
            return self.static_plot.to_svg()
        return None
