"""Thread-local access to the shared chart engine."""

import json
import threading
import warnings
from collections.abc import Callable, Mapping
from importlib.resources import files
from typing import TypedDict, cast

import quickjs

from ._data import (
    ChartType,
    DataView,
    InputSettings,
    Limits,
    RawData,
    Record,
    Scalar,
    SettingsGroup,
    TitleSettings,
)

_STATE = threading.local()
SCRIPTS = (
    "minidom.js",
    "ccCore.js",
    "PBISPC.js",
    "PBIFUN.js",
    "commonUtils.js",
    "headlessUtils.js",
)


# Keys are only present for the requested outputs and chart mode.
class Result(TypedDict, total=False):
    svg: str
    limits: Limits
    limitLines: list[Record]
    indicatorNames: list[str]


class ChartTitle(TypedDict):
    settings: TitleSettings


class ChartAggregations(TypedDict):
    aggregations: dict[str, str]


class UpdateValues(TypedDict):
    dataViews: list[DataView]


def _warn(message: str) -> None:
    warnings.warn(message, RuntimeWarning, stacklevel=3)


class Engine:
    def __init__(self) -> None:
        self.context = quickjs.Context()
        self.context.add_callable("pythonWarning", _warn)
        self.context.eval("""
            globalThis.console = {
                log: (...args) => pythonWarning(args.join(" ")),
                error: (error) => pythonWarning(String(error))
            };
            function pythonReplacer(key, value) {
                if (value === undefined) {
                    return null;
                }
                return value;
            }
            function pythonCall(name, payload) {
                return JSON.stringify(globalThis[name](...JSON.parse(payload)), pythonReplacer);
            }
            function pythonDefaults(type) {
                return JSON.stringify(globalThis[type].defaultSettings, pythonReplacer);
            }
        """)
        assets = files("controlchartspy").joinpath("_vendor")
        for name in SCRIPTS:
            self.context.eval(assets.joinpath(name).read_text(encoding="utf-8"))
        self.context.eval("initialiseHeadless()")
        self._call = cast(Callable[[str, str], str], self.context.get("pythonCall"))
        self._defaults = cast(Callable[[str], str], self.context.get("pythonDefaults"))

    def call(self, name: str, *args: object) -> object:
        try:
            result: object = json.loads(
                self._call(name, json.dumps(args, allow_nan=False))
            )
        except quickjs.JSException as error:
            raise ValueError(str(error)) from error
        # Invalid input is reported as an error object
        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])
        return result

    def defaults(self, chart_type: ChartType) -> dict[str, SettingsGroup]:
        return cast(dict[str, SettingsGroup], json.loads(self._defaults(chart_type)))


def engine() -> Engine:
    instance: Engine | None = getattr(_STATE, "engine", None)
    if instance is None:
        instance = Engine()
        _STATE.engine = instance
    return instance


def update_values(
    raw_data: RawData,
    input_settings: InputSettings,
    aggregations: Mapping[str, str],
) -> list[DataView]:
    updates = cast(
        UpdateValues,
        engine().call("makeUpdateValues", raw_data, input_settings, aggregations),
    )
    return updates["dataViews"]


def chart_title(title: str | Mapping[str, Scalar] | None) -> TitleSettings:
    return cast(ChartTitle, engine().call("chartTitle", title))["settings"]


def chart_aggregations(aggregations: Mapping[str, str] | None) -> dict[str, str]:
    result = engine().call("chartAggregations", aggregations)
    return cast(ChartAggregations, result)["aggregations"]


def render(
    chart_type: ChartType,
    data_views: list[DataView],
    title: TitleSettings,
    width: float,
    height: float,
    static: bool,
    limits: bool,
) -> Result:
    return cast(
        Result,
        engine().call(
            "updateHeadlessVisual",
            chart_type,
            data_views,
            title,
            width,
            height,
            static,
            limits,
        ),
    )
