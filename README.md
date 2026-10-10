# pycontrolcharts

Python port of the R [controlcharts](https://github.com/AUS-DOH-Safety-and-Quality/controlcharts)
package: SPC and funnel limits plus static SVG plots. Charts display in notebooks.
Python 3.10 or later is required. R is needed only to regenerate reference fixtures.

## Installation

After the first PyPI release:

```sh
uv add pycontrolcharts
```

For the current development version, use `uv add /path/to/pycontrolcharts`.

## Usage

```python
from datetime import date
from pycontrolcharts import spc, funnel

chart = spc(
    {"month": [date(2024, m, 1) for m in range(1, 7)], "n": [8, 11, 10, 12, 9, 13]},
    keys="month", numerators="n", spc_settings={"chart_type": "i"},
)
chart.limits            # list of dicts, same columns as R
chart.save_plot("spc.svg", width=960, height=600)

chart = funnel(
    {"org": ["A", "B", "C"], "n": [12, 18, 9], "d": [100, 150, 80]},
    keys="org", numerators="n", denominators="d",
    return_objs=("limits", "limit_lines"),
)
```

## Inputs and chart types

`data` accepts a mapping of columns or a sequence of records. Column arguments
accept a column name or a sequence in the original row order. SPC keys accept
Python `date` objects and ISO date strings (`YYYY-MM-DD`), including mixtures in
one column. Rows are sorted by key, within indicator groups when supplied.
Funnel keys identify organisations or other groups.

Set `spc_settings={"chart_type": ...}` or `funnel_settings={"chart_type": ...}`:

| Function | Chart types | Additional inputs |
| --- | --- | --- |
| `spc` | `run`, `i` (default), `i_m`, `i_mm`, `mr`, `c`, `g`, `t` | None |
| `spc` | `p`, `pp` (proportions), `u`, `up` (rates) | `denominators` |
| `spc` | `xbar` (sample means), `s` (sample standard deviations) | `denominators`, `xbar_sds` |
| `funnel` | `PR` (proportions, default), `SR` (standardised ratios), `RC` (rates/counts) | `denominators` |

`i_m` uses a median centreline; `i_mm` also uses median moving-range limits.
`pp` and `up` apply a large-sample correction. Choose a chart type appropriate
to your measure; calculations follow the R package.

Numeric `None` and `NaN` values are treated as missing. Infinite values are
rejected. Repeated keys are aggregated: numerators and denominators
default to `sum`, while other input fields default to `first`. Override these
with `aggregations`, using `first`, `last`, `sum`, `mean`, `min`, `max`, `median`,
or `count`.

## Settings

Settings use the R package's names. Retrieve the complete defaults or one group:

```python
from pycontrolcharts import spc_default_settings, funnel_default_settings

spc_defaults = spc_default_settings()
date_defaults = spc_default_settings("dates")
funnel_defaults = funnel_default_settings("funnel")
```

Common arguments include `spc_settings`/`funnel_settings` for calculations,
`outlier_settings` for signal flags, `scatter_settings` for point appearance,
`line_settings` for limit lines, and `x_axis_settings`/`y_axis_settings` for axes.
SPC also accepts `date_settings` and `nhs_icon_settings`. Each settings argument
is a mapping; values can be scalars, one-element sequences, or sequences aligned
with the original input rows.

For example, show SPC signals and give each observation its own colour:

```python
chart = spc(
    {"month": ["2024-01-01", "2024-02-01", "2024-03-01"], "n": [8, 11, 10]},
    keys="month", numerators="n",
    outlier_settings={"astronomical": True, "shift": True, "trend": True},
    scatter_settings={"colour": ["#333333", "#336699", "#333333"]},
    title={"text": "Monthly count", "subtitle": "Example SPC chart"},
)
```

## Phases and grouped limits

Use `groupings` to calculate separate limits for phases of one time series:

```python
data = {
    "month": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"],
    "n": [8, 11, 10, 12],
    "phase": ["Before", "Before", "After", "After"],
    "site": ["A", "A", "B", "B"],
}
phased = spc(data, "month", "n", groupings="phase")
grouped = spc(data, "month", "n", indicators="site", return_objs="limits")
site_a_limits = grouped.limits["A"]
```

`indicators` create separate series and nested limits. A mapping such as
`indicators={"Region": "region", "Site": "site"}` creates a nested mapping in
that order, with names available through `chart.indicator_names`. A single
indicator group can render a plot; multiple groups require `return_objs="limits"`.

## Results and export

Both constructors return a `ControlChart`. `return_objs` accepts one output name
or an iterable; its default is `("static_plot", "limits")`.

| Attribute | Contents |
| --- | --- |
| `static_plot` | `StaticPlot` with `to_svg()` and notebook SVG display |
| `limits` | A list of records, or nested mappings for grouped SPC series |
| `limit_lines` | Funnel limit-line records; request `"limit_lines"` explicitly |
| `indicator_names` | SPC indicator names in nesting order |

Unrequested outputs are `None`. SPC records include the formatted `date`,
`value`, `target`, and applicable lower/upper limits (`ll68`, `ll95`, `ll99`,
`ul68`, `ul95`, `ul99`). Columns depend on chart type and requested signal flags.
Funnel records include `group`, `numerator`, `denominator`, `value`, `z`, `target`,
and limits. Proportion charts use percentage values under the default settings.

`chart.save_plot("chart.svg")` writes a complete SVG. Specify `width` and `height`
to rerender at a different size, or use `chart.static_plot.to_svg()` to get the SVG
as a string. The default size is 640 × 400; export supports SVG.

The [R package documentation](https://aus-doh-safety-and-quality.github.io/controlcharts/)
provides further information about the shared calculation and display settings.
