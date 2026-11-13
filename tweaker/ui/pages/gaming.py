"""Product page. Controls delegate to the controller, never Windows writes."""

from ... import diagnostics
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QCheckBox,
)
from ...branding import branded_text
from ...actions import PROFILES
from ...platform import WINDOWS
from ..widgets import (
    Card,
    Switch,
    label,
    button,
    clear_layout,
)


from .common import Page, details, confirm, page_header, row, control, ActionCard


class Gaming(Page):
    def __init__(self, window):
        super().__init__(window)
        self.selected = set()
        page_header(
            self.box,
            "Gaming Mode",
            "Your session. Your selections. Original settings restored when you finish.",
        )
        hero = Card(hero=True)
        top = QHBoxLayout()
        self.mode = label("OFF", "metric")
        top.addWidget(self.mode)
        top.addStretch()
        self.mode_switch = Switch("Gaming Mode")
        self.mode_switch.clicked.connect(self.toggle_mode)
        top.addWidget(self.mode_switch)
        hero.box.addLayout(top)
        self.session_status = label("No active session", "muted")
        hero.box.addWidget(self.session_status)
        hero.box.addLayout(
            row(
                control(self, "Inspect Fortnite", self.c.inspect_game, windows=True),
                control(self, "Inspect compatibility", self.c.inspect_states),
                control(self, "Discover optional apps", self.c.discover, windows=True),
            )
        )
        self.watch = QCheckBox("Automatically restore after Fortnite exits")
        self.watch.setToolTip(
            "Requires observing Fortnite running, then two absent five-second polls. No game memory or anti-cheat internals are accessed."
        )
        self.watch.setEnabled(WINDOWS)
        self.watch.toggled.connect(self.watch_changed)
        hero.box.addWidget(self.watch)
        self.emergency = control(
            self, "End session & restore", self.end_mode, danger=True
        )
        hero.box.addLayout(row(self.emergency))
        self.box.addWidget(hero)
        profiles = QHBoxLayout()
        profiles.addWidget(label("Profile suggestions", "muted"))
        self.profile = QComboBox()
        self.profile.addItems(list(PROFILES))
        profiles.addWidget(self.profile)
        profiles.addWidget(
            control(self, "Use compatible suggestions", self.select_profile)
        )
        profiles.addStretch()
        self.box.addLayout(profiles)
        self.box.addWidget(label("Session optimizations", "heading"))
        self.box.addWidget(
            label(
                "Only compatible, session-safe actions appear below. Startup, recording policy and Fax remain persistent-only.",
                "muted",
            )
        )
        self.list = QVBoxLayout()
        self.box.addLayout(self.list)
        self.report = Card()
        self.report.box.addWidget(label("Fortnite performance guidance", "heading"))
        self.game = label("Game detection has not been run.", "muted")
        self.report.box.addWidget(self.game)
        self.report.box.addLayout(
            row(
                button(
                    "Read supported settings guidance",
                    lambda: details(window, "Fortnite guidance", diagnostics.GUIDANCE),
                ),
                control(
                    self,
                    "Startup & task inventory",
                    lambda: self.c.inventory(
                        lambda result: details(
                            window, "Startup and task inventory", result
                        )
                    ),
                    windows=True,
                ),
                button("View Fortnite report", self.show_report),
            )
        )
        self.box.addWidget(self.report)
        self.box.addStretch()

    def select_profile(self):
        if self.c.session.active:
            self.window.toast(
                "End the active session before changing its profile selections."
            )
            return
        candidates = PROFILES[self.profile.currentText()]
        if self.profile.currentText() == "Custom":
            self.window.toast("Custom keeps your individual session selections.")
            return
        self.selected = {
            key for key in candidates if self.c.states.get(key, {}).get("available")
        }
        self.refresh()
        self.window.toast(
            f"{len(self.selected)} compatible actions selected. Profiles never apply settings automatically; inspect compatibility if suggestions are unavailable."
        )

    def select(self, key, checked):
        if checked:
            self.selected.add(key)
        else:
            self.selected.discard(key)

    def watch_changed(self, checked):
        self.c.watch_enabled = checked
        self.window.update_timers()

    def toggle_mode(self):
        # The visual switch reflects backend state, not a pending request.
        self.mode_switch.setChecked(bool(self.c.session.active))
        if self.c.session.active:
            self.end_mode()
            return
        ids = sorted(self.selected)
        if not ids:
            self.window.toast(
                "Select at least one compatible session optimization first."
            )
            return
        text = "\n\n".join(
            branded_text(
                self.c.engine.actions[k].title + "\n" + self.c.engine.actions[k].risk
            )
            for k in ids
        )
        if confirm(
            self.window,
            "Start approved Gaming Mode",
            text
            + "\n\nApply temporarily? Failed startup rolls back this session only.",
        ):
            self.c.start_session(ids)

    def end_mode(self):
        if confirm(
            self.window,
            "Restore Gaming Mode",
            "End the session and restore only its owned changes?",
        ):
            self.c.end_session()

    def show_report(self):
        report = self.c.game_report
        if report:
            details(self.window, "Fortnite report", report)
        else:
            self.window.toast("Inspect Fortnite to create a hardware-specific report.")

    def refresh(self):
        active = bool(self.c.session.active)
        self.mode.setText("ON" if active else "OFF")
        self.mode_switch.setChecked(active)
        self.mode_switch.setEnabled(not self.c.busy)
        owned = (
            [r for _, r in self.c.owned() if r.get("session") == self.c.session.active]
            if active
            else []
        )
        self.session_status.setText(
            self.c.game_status
            + " · "
            + (
                f"{len(owned)} session-owned changes · restoration pending"
                if active
                else "Original session settings restored / no active session"
            )
        )
        self.emergency.setEnabled(active and not self.c.busy)
        self.watch.blockSignals(True)
        self.watch.setChecked(self.c.watch_enabled)
        self.watch.blockSignals(False)
        clear_layout(self.list)
        actions = [a for a in self.c.engine.actions.values() if a.session_safe]
        for a in actions:
            self.list.addWidget(ActionCard(self, a, session=True))
        if not actions:
            self.list.addWidget(
                label(
                    "Inspect compatibility and discover optional apps to find eligible actions.",
                    "muted",
                )
            )
        if self.c.game_report:
            self.game.setText(
                self.c.game_status
                + "\n"
                + "\n".join("• " + n for n in self.c.game_report["recommendations"][:3])
            )
        else:
            self.game.setText(
                "Use Inspect Fortnite for installation detection and hardware-specific recommendations."
            )
