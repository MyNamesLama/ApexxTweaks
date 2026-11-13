"""Product page. Controls delegate to the controller, never Windows writes."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QWidget,
)
from ...platform import WINDOWS
from ...analysis import rows
from ..controller import measurements
from ..widgets import (
    Card,
    ResponsiveGrid,
    Switch,
    Chart,
    label,
    button,
)


from .common import Page, details, page_header, row, control


class Monitor(Page):
    def __init__(self, window):
        super().__init__(window)
        self.history = {"cpu": [], "gpu_engine": [], "ram_percent": []}
        page_header(
            self.box,
            "System Monitor",
            "Real counters. Clear units. No fabricated temperatures or benchmark scores.",
        )
        self.live = Switch("Enable live monitoring")
        self.live.setEnabled(WINDOWS)
        self.live.toggled.connect(lambda _: window.update_timers())
        controls = row()
        controls.addWidget(
            control(self, "Inspect system", self.c.inspect_system, windows=True)
        )
        controls.addWidget(
            control(self, "Read one sample", self.c.inspect_activity, windows=True)
        )
        controls.addWidget(
            control(self, "Sustained diagnostics", self.c.sustained, windows=True)
        )
        live_group = QWidget()
        live_box = QHBoxLayout(live_group)
        live_box.setContentsMargins(0, 0, 0, 0)
        live_box.addWidget(label("Live monitoring", "muted"))
        live_box.addWidget(self.live)
        controls.addWidget(live_group)
        self.box.addLayout(controls)
        self.monitor_note = label(
            "Monitoring is off. It pauses when this page is hidden or the window is minimized.",
            "muted",
        )
        self.box.addWidget(self.monitor_note)
        self.grid = grid = ResponsiveGrid(max_columns=2, preferred_width=280)
        grid.setSpacing(14)
        self.cards = {}
        self.charts = {}
        for i, (key, title) in enumerate(
            [
                ("cpu", "CPU utilization"),
                ("gpu_engine", "GPU · peak 3D engine"),
                ("ram_percent", "RAM utilization"),
            ]
        ):
            card = Card()
            card.box.addWidget(label(title, "heading"))
            value = label("Unavailable", "metric")
            card.box.addWidget(value)
            chart = Chart(title)
            card.box.addWidget(chart)
            foot = label("No sample yet", "muted")
            card.box.addWidget(foot)
            self.cards[key] = (value, foot)
            self.charts[key] = chart
            grid.addWidget(card)
        self.box.addLayout(grid)
        info = Card()
        info.box.addWidget(label("Hardware & diagnostics", "heading"))
        self.hardware = label(
            "Inspect the system for CPU, GPU, driver, storage and network information.",
            "muted",
        )
        info.box.addWidget(self.hardware)
        info.box.addLayout(
            row(
                button(
                    "System details",
                    lambda: details(
                        window,
                        "System information",
                        self.c.hardware or "No system inspection yet.",
                    ),
                ),
                button(
                    "Sustained findings",
                    lambda: details(
                        window,
                        "Sustained screening",
                        self.c.last_telemetry or "No sustained collection yet.",
                    ),
                ),
                button(
                    "Background processes",
                    lambda: details(
                        window,
                        "Read-only activity",
                        self.c.sample or "No activity sample yet.",
                    ),
                ),
            )
        )
        self.box.addWidget(info)
        self.box.addStretch()
        self.c.sample_ready.connect(self.sample_received)

    def sample_received(self, sample):
        m = measurements(self.c.hardware, sample)
        for key in self.history:
            # Missing values are not zero. Clear the series rather than connect across a data gap.
            if m[key] is None:
                self.history[key] = []
            else:
                self.history[key] = (self.history[key] + [m[key]])[-90:]
            self.charts[key].set_values(self.history[key])

    def refresh(self):
        m = measurements(self.c.hardware, self.c.sample)
        for key, (value, foot) in self.cards.items():
            value.setText(f"{m[key]:.1f}%" if m[key] is not None else "Unavailable")
        cpu = rows(self.c.hardware.get("cpu"))
        gpu = rows(self.c.hardware.get("gpu"))
        self.cards["cpu"][1].setText(
            (cpu[0].get("Name", "CPU") if cpu else "Model not inspected")
            + "\nTemperature: Unavailable"
        )
        self.cards["gpu_engine"][1].setText(
            (
                " / ".join(g.get("Name", "GPU") for g in gpu)
                if gpu
                else "Model not inspected"
            )
            + "\nMaximum across reported 3D engines, not whole-GPU utilization. Temperature: Unavailable"
        )
        self.cards["ram_percent"][1].setText(
            f"{m['used_mb'] / 1024:.1f} GiB used · {m['available_mb'] / 1024:.1f} GiB available · {m['total_mb'] / 1024:.1f} GiB total"
            if m["used_mb"] is not None
            else "Inspect memory capacity and read counters for used/available RAM."
        )
        if self.c.hardware:
            self.hardware.setText(
                " · ".join(
                    str(self.c.hardware.get(k, ""))
                    for k in ("platform", "build")
                    if self.c.hardware.get(k)
                )
                + "\nFull driver, disk and adapter inventory is available in System details."
            )
        self.monitor_note.setText(
            (
                "Live sampling every "
                + str(self.c.preferences["monitor_interval"])
                + " seconds while visible. "
                if self.live.isChecked()
                else "Monitoring is off. "
            )
            + "Sampling adds overhead; use identical monitoring in A/B runs."
        )
