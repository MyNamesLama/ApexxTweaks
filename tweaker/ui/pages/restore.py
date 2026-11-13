"""Product page. Controls delegate to the controller, never Windows writes."""

import json
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
)
from ...branding import branded_text
from ..widgets import (
    Card,
    label,
    button,
    clear_layout,
)


from .common import Page, details, confirm, page_header, row, control


class RestoreCenter(Page):
    def __init__(self, window):
        super().__init__(window)
        page_header(
            self.box,
            "Restore Center",
            "Every owned change has a history. Return to your original configuration with confidence.",
        )
        self.summary = label("No changes to restore", "heading")
        self.box.addWidget(self.summary)
        self.check_button = control(
            self, "Check for conflicts", self.c.inspect_recovery, True
        )
        self.all_button = control(
            self, "Restore all changes", self.restore_all, danger=True
        )
        self.box.addLayout(
            row(
                self.check_button,
                self.all_button,
                control(
                    self,
                    "Offer Windows restore point",
                    self.restore_point,
                    windows=True,
                ),
            )
        )
        self.history = QCheckBox("Include restored history")
        self.history.toggled.connect(self.refresh)
        self.box.addWidget(self.history)
        self.list = QVBoxLayout()
        self.box.addLayout(self.list)
        self.box.addStretch()

    def restore_one(self, index):
        record = self.c.records[index]
        if confirm(
            self.window,
            "Restore original setting",
            f"Restore {record['action']}?\n\nPrevious value:\n"
            + json.dumps(record["original"], ensure_ascii=False)
            + "\n\nAny external conflict will be preserved.",
        ):
            self.c.restore(index)

    def restore_all(self):
        if confirm(
            self.window,
            "Restore all owned changes",
            "Restore all journal-owned changes in reverse order? Independent failures and outside conflicts will be reported, not overwritten.",
        ):
            self.c.restore_all()

    def restore_point(self):
        if confirm(
            self.window,
            "Windows restore point",
            "Ask Windows to create a restore point? Administrator, System Protection and Windows rate-limit requirements apply. Snapshots remain required for every action.",
        ):
            self.c.restore_point()

    def refresh(self, *_):
        clear_layout(self.list)
        owned = self.c.owned()
        eligible = bool(owned) and self.c.engine.backend.supported() and not self.c.busy
        self.check_button.setEnabled(eligible)
        self.all_button.setEnabled(eligible)
        self.summary.setText(
            f"{len(owned)} change"
            + ("s" if len(owned) != 1 else "")
            + " available for recovery"
            if owned
            else "Your journal has no pending changes"
        )
        records = [
            (i, r)
            for i, r in enumerate(self.c.records)
            if r["status"] != "restored" or self.history.isChecked()
        ]
        if not records:
            card = Card()
            card.box.addWidget(label("A clean slate", "heading"))
            card.box.addWidget(
                label(
                    "When you apply an automatic optimization, its original value and recovery controls will appear here. No changes are made automatically.",
                    "muted",
                )
            )
            self.list.addWidget(card)
        for index, r in reversed(records):
            card = Card()
            top = QHBoxLayout()
            title = branded_text(r.get("definition", {}).get("title", r["action"]))
            top.addWidget(label(title, "heading"), 1)
            top.addWidget(label(r["status"].replace("_", " "), "tag"))
            card.box.addLayout(top)
            when = (
                datetime.fromtimestamp(r["timestamp"]).strftime("%d %b %Y · %H:%M")
                if r.get("timestamp")
                else "Time unavailable"
            )
            card.box.addWidget(label(when, "muted"))
            original = json.dumps(r["original"], ensure_ascii=False)
            card.box.addWidget(
                label(
                    "Previous value: "
                    + (original[:180] + "…" if len(original) > 180 else original),
                    "muted",
                )
            )
            state, reason = self.c.restore_states.get(
                index,
                (
                    "unchecked",
                    "Not checked for conflicts. Restore verifies the current value before writing.",
                ),
            )
            card.box.addWidget(label(reason, "muted"))
            restore = button(
                "Restored" if r["status"] == "restored" else "Restore original",
                lambda checked=False, i=index: self.restore_one(i),
            )
            self.window.bind_busy(
                restore,
                lambda r=r, state=state: (
                    r["status"] != "restored"
                    and state not in ("conflict", "unavailable")
                    and self.c.engine.backend.supported()
                ),
            )
            card.box.addLayout(
                row(
                    button(
                        "Full history & backup",
                        lambda checked=False, record=r: details(
                            self.window, "Original journal record", record
                        ),
                    ),
                    restore,
                )
            )
            self.list.addWidget(card)
