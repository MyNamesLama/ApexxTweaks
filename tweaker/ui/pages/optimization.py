"""Product page. Controls delegate to the controller, never Windows writes."""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
)
from ...branding import branded_text
from ..widgets import (
    Card,
    label,
    button,
    clear_layout,
)


from .common import (
    Page,
    details,
    confirm,
    page_header,
    row,
    control,
    ActionCard,
    CATEGORY,
)


class Optimization(Page):
    def __init__(self, window):
        super().__init__(window)
        self.selected = set()
        page_header(
            self.box,
            "Optimization",
            "Less guesswork. More control. Every automatic change is backed up and verified.",
        )
        self.box.addLayout(
            row(
                control(self, "Inspect compatibility", self.c.inspect_states, True),
                control(self, "Discover optional apps", self.c.discover, windows=True),
                button(
                    "Discovery details",
                    lambda: details(
                        window,
                        "Optional-app discovery",
                        self.c.discovery_report
                        or "Run discovery to see approved and read-only entries.",
                    ),
                ),
            )
        )
        self.recommended = Card(hero=True)
        self.recommended_label = label("Start with a compatibility check", "heading")
        self.recommended.box.addWidget(self.recommended_label)
        self.recommended.box.addWidget(
            label(
                "Power changes are hardware-dependent experiments. Optional apps are individual opt-ins. A recommendation is not a promised FPS improvement.",
                "muted",
            )
        )
        self.box.addWidget(self.recommended)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search optimizations…")
        self.search.setAccessibleName("Search optimizations")
        self.search.setClearButtonEnabled(True)
        self.category = QComboBox()
        self.category.addItems(
            [
                "All categories",
                "System",
                "Power",
                "Startup",
                "Background Applications",
                "Gaming",
                "Network Diagnostics",
                "Advanced",
            ]
        )
        self.category.setAccessibleName("Optimization category")
        self.sort = QComboBox()
        self.sort.addItems(["Recommended", "Name", "Risk", "Status"])
        self.sort.setAccessibleName("Sort optimizations")
        self.applied = QCheckBox("Applied only")
        filters.addWidget(self.search, 2)
        filters.addWidget(self.category, 1)
        filters.addWidget(self.sort)
        filters.addWidget(self.applied)
        self.box.addLayout(filters)
        self.batch = QCheckBox("Select multiple")
        self.batch.toggled.connect(self.refresh)
        self.selection_label = label("0 selected", "muted")
        self.batch_apply = control(self, "Review selection", self.apply_selection)
        self.batch_apply.setEnabled(False)
        self.clear_selection = button("Clear", self.clear_selected)
        self.box.addLayout(
            row(
                self.batch, self.selection_label, self.batch_apply, self.clear_selection
            )
        )
        self.list = QVBoxLayout()
        self.list.setSpacing(12)
        self.box.addLayout(self.list)
        self.guided = Card()
        self.guided.box.addWidget(label("Guided Windows settings", "heading"))
        self.guided.box.addWidget(
            label(
                "These open Windows Settings. You make the change there; it is not part of the automatic rollback journal.",
                "muted",
            )
        )
        self.guided.box.addLayout(
            row(
                *[
                    control(
                        self,
                        name,
                        lambda checked=False, u=uri: window.open_settings(u),
                        windows=True,
                    )
                    for name, uri in [
                        ("Game Mode", "gaming-gamemode"),
                        ("Captures", "gaming-gamedvr"),
                        ("Graphics / GPU", "display-advancedgraphics"),
                        ("Display", "display-advanced"),
                    ]
                ]
            )
        )
        self.guided.box.addLayout(
            row(
                control(
                    self,
                    "Inspect settings status",
                    lambda: self.c.gaming_settings(
                        lambda result: details(
                            window, "Guided Windows settings status", result
                        )
                    ),
                    windows=True,
                )
            )
        )
        self.box.addWidget(self.guided)
        self.network = Card()
        self.network.box.addWidget(label("Network diagnostics · read only", "heading"))
        self.network.box.addWidget(
            label(
                "Probe your gateway and a remote endpoint separately. ICMP responses measure neither Fortnite packet loss nor rendering/input latency.",
                "muted",
            )
        )
        self.host = QLineEdit()
        self.host.setPlaceholderText("Hostname or IP address")
        self.host.setAccessibleName("ICMP target")
        self.network.box.addLayout(
            row(
                self.host,
                control(
                    self,
                    "Probe 20 packets",
                    lambda: self.c.probe(self.host.text()),
                    windows=True,
                ),
            )
        )
        self.net_result = label("No probe has been run.", "muted")
        self.network.box.addWidget(self.net_result)
        self.box.addWidget(self.network)
        self.box.addStretch()
        for signal in (
            self.search.textChanged,
            self.category.currentTextChanged,
            self.sort.currentTextChanged,
            self.applied.toggled,
        ):
            signal.connect(self.refresh)

    def select(self, key, checked):
        if checked:
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self.selection_label.setText(f"{len(self.selected)} selected")
        self.batch_apply.setEnabled(bool(self.selected) and not self.c.busy)

    def clear_selected(self):
        self.selected.clear()
        self.refresh()

    def apply_selection(self):
        ids = sorted(self.selected)
        text = "\n\n".join(
            branded_text(
                self.c.engine.actions[k].title + "\n" + self.c.engine.actions[k].risk
            )
            for k in ids
        )
        if ids and confirm(
            self.window,
            "Review selected actions",
            text
            + "\n\nPersistent batches are per-action, not atomic. Earlier changes remain undoable if a later action fails. Apply?",
        ):
            self.c.apply_many(ids)

    def apply_one(self, key):
        a = self.c.engine.actions[key]
        if confirm(
            self.window,
            "Review optimization",
            branded_text(a.title + "\n\n" + a.description + "\n\n" + a.risk)
            + "\n\nSave the original setting, apply, and verify?",
        ):
            self.c.apply(key)

    def restore_one(self, index):
        if confirm(
            self.window,
            "Restore original setting",
            "Restore this journal-owned setting? External conflicts will be preserved.",
        ):
            self.c.restore(index)

    def refresh(self, *_):
        self.selection_label.setText(f"{len(self.selected)} selected")
        self.batch_apply.setEnabled(bool(self.selected) and not self.c.busy)
        self.selection_label.setVisible(self.batch.isChecked())
        self.batch_apply.setVisible(self.batch.isChecked())
        self.clear_selection.setVisible(self.batch.isChecked())
        clear_layout(self.list)
        query = self.search.text().casefold()
        category = self.category.currentText()
        actions = []
        for a in self.c.engine.actions.values():
            state = self.c.states.get(a.id, {})
            if (
                category != "All categories"
                and CATEGORY.get(a.category, "Advanced") != category
            ):
                continue
            if (
                query
                and query
                not in (a.title + " " + a.description + " " + a.category).casefold()
            ):
                continue
            if self.applied.isChecked() and not state.get("active"):
                continue
            actions.append(a)
        sort = self.sort.currentText()
        actions.sort(
            key=lambda a: (
                a.risk
                if sort == "Risk"
                else self.c.states.get(a.id, {}).get("reason", "")
                if sort == "Status"
                else a.title
            ).casefold()
        )
        if sort == "Recommended":
            actions.sort(
                key=lambda a: (
                    a.category != "Power",
                    not self.c.states.get(a.id, {}).get("available", False),
                    a.title,
                )
            )
        if actions:
            for a in actions:
                self.list.addWidget(ActionCard(self, a))
        elif category != "Network Diagnostics":
            empty = Card()
            empty.box.addWidget(label("No matching optimizations", "heading"))
            empty.box.addWidget(
                label(
                    "Try another filter, inspect compatibility, or discover approved optional apps.",
                    "muted",
                )
            )
            self.list.addWidget(empty)
        ready = [
            a
            for a in self.c.engine.actions.values()
            if a.category == "Power"
            and self.c.states.get(a.id, {}).get("available")
            and not self.c.states[a.id].get("active")
        ]
        self.recommended_label.setText(
            "Available experiment: " + ready[0].title
            if ready
            else (
                "No compatible power experiment identified"
                if self.c.states
                else "Start with a compatibility check"
            )
        )
        self.guided.setVisible(category in ("All categories", "Gaming"))
        self.network.setVisible(category == "Network Diagnostics")
        if self.c.network_result:
            r = self.c.network_result
            fmt = lambda v: "Unavailable" if v is None else f"{v:.1f} ms"
            self.net_result.setText(
                f"RTT {fmt(r['mean_ms'])}  ·  Jitter {fmt(r['jitter_mean_adjacent_ms'])}  ·  Response loss {r['loss_percent']:.1f}%\n"
                + r["note"]
            )
