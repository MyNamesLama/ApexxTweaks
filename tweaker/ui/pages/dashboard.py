"""Product page. Controls delegate to the controller, never Windows writes."""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)
from ...analysis import rows
from ..controller import measurements
from ..widgets import (
    Card,
    MetricCard,
    ResponsiveGrid,
    label,
    button,
)


from .common import Page, page_header, row, control


class Dashboard(Page):
    def __init__(self, window):
        super().__init__(window)
        self.box.addWidget(label("YOUR SYSTEM. CLEARER DECISIONS.", "eyebrow"))
        page_header(
            self.box,
            "Welcome to ApexxTweaks",
            "A clearer view of your system. A deliberate approach to performance.",
        )
        self.recovery = Card()
        self.recovery.box.addWidget(
            label("Changes are waiting in Restore Center", "heading")
        )
        self.recovery.box.addWidget(
            label(
                "Previous settings remain backed up. Review pending or applied changes before your next experiment.",
                "muted",
            )
        )
        self.recovery.box.addLayout(
            row(
                button("Open Restore Center", lambda: window.navigate("Restore Center"))
            )
        )
        self.box.addWidget(self.recovery)
        self.grid = ResponsiveGrid(max_columns=3, preferred_width=240)
        self.grid.setSpacing(14)
        self.metrics = {}
        for i, name in enumerate(
            [
                "Processor",
                "Graphics",
                "Memory",
                "Operating system",
                "Power configuration",
                "Gaming Mode",
            ]
        ):
            card = MetricCard(name)
            self.metrics[name] = card
            self.grid.addWidget(card)
        self.box.addLayout(self.grid)
        self.summary = Card()
        self.summary_grid = ResponsiveGrid(max_columns=3, preferred_width=160)
        self.counts = []
        for title in ["Available to apply", "Applied · verified", "Changes to restore"]:
            panel = QWidget()
            box = QVBoxLayout(panel)
            box.setContentsMargins(0, 0, 0, 0)
            value = label("—", "metric")
            box.addWidget(value)
            box.addWidget(label(title, "muted"))
            self.counts.append(value)
            self.summary_grid.addWidget(panel)
        self.summary.box.addLayout(self.summary_grid)
        self.box.addWidget(self.summary)
        hero = Card(hero=True)
        hero.box.addWidget(label("BUILD A BETTER BASELINE", "eyebrow"))
        hero.box.addWidget(label("Optimize Your Experience", "heading"))
        hero.box.addWidget(
            label(
                "Find compatible changes, understand the tradeoffs, and compare what actually improves your game.",
                "muted",
            )
        )
        hero.box.addLayout(
            row(
                button(
                    "Explore optimizations",
                    lambda: window.navigate("Optimization"),
                    True,
                ),
                control(self, "Inspect system", self.c.inspect_system, windows=True),
                button("System diagnostics", lambda: window.navigate("System Monitor")),
            )
        )
        self.box.addWidget(hero)
        bottom = row()
        bottom.addWidget(
            label("Last-read snapshots · No automatic settings changes", "muted")
        )
        bottom.addWidget(label("SAFE BY DESIGN", "limeTag"))
        self.box.addLayout(bottom)
        self.box.addStretch()

    def refresh(self):
        h = self.c.hardware
        m = measurements(h, self.c.sample)
        cpus = rows(h.get("cpu"))
        gpus = rows(h.get("gpu"))
        pct = lambda v: f"{v:.0f}%" if v is not None else "Unavailable"
        self.metrics["Processor"].set(
            pct(m["cpu"]),
            cpus[0].get("Name", "Model unavailable")
            if cpus
            else "Inspect your system to identify the processor",
        )
        # Engine peak is explicitly labelled; it is not presented as overall GPU usage.
        self.metrics["Graphics"].set(
            pct(m["gpu_engine"]),
            (
                "Peak 3D engine across adapters · "
                + " / ".join(g.get("Name", "Unknown GPU") for g in gpus)
            )
            if gpus
            else "GPU model and counters not inspected",
        )
        self.metrics["Memory"].set(
            f"{m['total_mb'] / 1024:.1f} GiB" if m["total_mb"] else "Unavailable",
            f"{m['used_mb'] / 1024:.1f} GiB used · {m['ram_percent']:.0f}%"
            if m["used_mb"] is not None
            else "Memory usage not inspected",
        )
        self.metrics["Operating system"].set(
            h.get("platform", "Not inspected"),
            ("Build " + str(h["build"]))
            if h.get("build")
            else "Windows information requires inspection",
        )
        p = h.get("power", {})
        power = p.get("power")
        names = {
            "381b4222-f694-41f0-9685-ff5bb260df2e": "Balanced",
            "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "High performance",
        }
        self.metrics["Power configuration"].set(
            names.get(power, "Custom plan" if power else "Not inspected"),
            (
                {
                    "00000000-0000-0000-0000-000000000000": "Requested AC mode: Balanced",
                    "ded574b5-45a0-4f42-8737-46345c09c238": "Requested AC mode: Best performance",
                    "961cc777-2547-4f9d-8174-7d86181b8a7a": "Requested AC mode: Best efficiency",
                }.get(p.get("ac-mode"), "AC mode unavailable")
            )
            if power
            else "Inspect system to read the current configuration",
        )
        self.metrics["Gaming Mode"].set(
            "ON" if self.c.session.active else "OFF",
            "Temporary changes active"
            if self.c.session.active
            else "Ready when you are",
        )
        for name in ["Operating system", "Power configuration", "Gaming Mode"]:
            self.metrics[name].value.setStyleSheet("font-size: 19px; font-weight: 600;")
        self.counts[0].setText(
            str(
                sum(
                    s.get("available") and not s.get("active")
                    for s in self.c.states.values()
                )
            )
            if self.c.states
            else "—"
        )
        self.counts[1].setText(
            str(sum(s.get("active", False) for s in self.c.states.values()))
            if self.c.states
            else "—"
        )
        self.counts[2].setText(str(len(self.c.owned())))
        self.recovery.setVisible(bool(self.c.owned()))
