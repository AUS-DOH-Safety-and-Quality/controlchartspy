"""Calculate and visualise statistical process control charts and funnel plots."""

from ._api import funnel, funnel_default_settings, spc, spc_default_settings
from ._result import ControlChart, StaticPlot

__all__ = [
    "ControlChart",
    "StaticPlot",
    "funnel",
    "funnel_default_settings",
    "spc",
    "spc_default_settings",
]
