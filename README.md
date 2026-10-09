# pycontrolcharts

Python port of the R [controlcharts](https://github.com/AUS-DOH-Safety-and-Quality/controlcharts)
package: SPC and funnel limits plus static SVG plots, run through the same
JavaScript engine via `quickjs-ng`. No interactive plots.

```sh
uv add /path/to/pycontrolcharts
```

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

Arguments, settings names and values follow the R package; see its documentation.
`data` is a mapping of columns or a list of records. Column arguments are a name
in `data` or a sequence in row order. `spc_default_settings()` and
`funnel_default_settings()` list the available settings. SPC keys must be dates or
ISO date strings. SPC `indicators` return nested limits and do not render.

## Development

```sh
uv run python tools/sync_assets.py ../controlcharts   # copy JS assets from the R checkout
Rscript tests/generate_reference.R tests/reference    # regenerate R fixtures
uv run python -m unittest discover -s tests
```
