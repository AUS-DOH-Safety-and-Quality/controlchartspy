"""Thread-local access to the shared chart engine."""

import json
import threading
import warnings
from collections.abc import Mapping
from importlib.resources import files
from typing import Any

import quickjs

_STATE = threading.local()
_SCRIPTS = (
    "minidom.js",
    "ccD3.js",
    "PBISPC.js",
    "PBIFUN.js",
    "MISC.js",
    "commonUtils.js",
    "headlessUtils.js",
)


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
        assets = files("pycontrolcharts").joinpath("_vendor")
        for name in _SCRIPTS:
            self.context.eval(assets.joinpath(name).read_text(encoding="utf-8"))
        self.context.eval("initialiseHeadless()")
        self._call = self.context.get("pythonCall")
        self._defaults = self.context.get("pythonDefaults")

    def call(self, name: str, *args: object) -> Any:
        try:
            return json.loads(self._call(name, json.dumps(args, allow_nan=False)))
        except quickjs.JSException as error:
            raise ValueError(str(error)) from error

    def defaults(self, chart_type: str) -> dict[str, Any]:
        defaults: dict[str, Any] = json.loads(self._defaults(chart_type))
        return defaults


def engine() -> Engine:
    instance: Engine | None = getattr(_STATE, "engine", None)
    if instance is None:
        instance = Engine()
        _STATE.engine = instance
    return instance


def render(
    chart_type: str,
    data_views: list[Any],
    title: Mapping[str, Any],
    width: float,
    height: float,
    static: bool,
    limits: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = engine().call(
        "updateHeadlessVisual",
        chart_type,
        data_views,
        title,
        width,
        height,
        static,
        limits,
    )
    if "error" in result:
        raise ValueError(result["error"])
    return result
