"""Focused application pages, each backed by the shared serialized controller."""

from .dashboard import Dashboard
from .optimization import Optimization
from .gaming import Gaming
from .monitor import Monitor
from .benchmarks import Benchmarks
from .restore import RestoreCenter
from .settings import Settings
from .common import ActionCard

__all__ = [
    "Dashboard",
    "Optimization",
    "Gaming",
    "Monitor",
    "Benchmarks",
    "RestoreCenter",
    "Settings",
    "ActionCard",
]
