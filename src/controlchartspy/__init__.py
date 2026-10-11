"""Calculate and visualise SPC, funnel, and multi-indicator sigma charts."""

from ._api import (
    funnel,
    funnel_default_settings,
    misc_default_settings,
    spc,
    spc_default_settings,
)
from ._misc import misc
from ._result import ControlChart, StaticPlot

__all__ = [
    "ControlChart",
    "StaticPlot",
    "funnel",
    "funnel_default_settings",
    "misc",
    "misc_default_settings",
    "spc",
    "spc_default_settings",
]
