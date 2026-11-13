"""Seven focused product pages. Controls delegate to the controller, never Windows writes."""

import json
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QMessageBox,
)
from ...branding import branded_text
from ...platform import WINDOWS
from ..widgets import (
    Card,
    FlowLayout,
    label,
    button,
    scroll_page,
)

CATEGORY = {
    "Services": "System",
    "Power": "Power",
    "Startup": "Startup",
    "Background": "Background Applications",
    "Recording": "Gaming",
    "Tasks": "Advanced",
}


def details(parent, title, text):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(680, 510)
    box = QVBoxLayout(dialog)
    browser = QTextBrowser()
    browser.setPlainText(
        text
        if isinstance(text, str)
        else json.dumps(text, indent=2, ensure_ascii=False)
    )
    box.addWidget(browser)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    box.addWidget(buttons)
    dialog.exec()


def confirm(parent, title, text):
    return (
        QMessageBox.question(
            parent,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        == QMessageBox.StandardButton.Yes
    )


def page_header(layout, title, subtitle):
    layout.addWidget(label(title, "title"))
    layout.addWidget(label(subtitle, "subtitle"))


def row(*widgets):
    layout = FlowLayout()
    for w in widgets:
        layout.addWidget(w)
    return layout


def control(parent, text, callback, primary=False, danger=False, windows=False):
    w = button(text, callback, primary, danger)
    parent.window.bind_busy(w, lambda: not windows or WINDOWS)
    if windows:
        w.setToolTip(
            "Requires Windows 10/11. No Windows operations are simulated on Linux."
        )
    return w


class Page:
    def __init__(self, window):
        self.window = window
        self.c = window.controller
        self.widget, self.body, self.box = scroll_page()

    def refresh(self):
        pass


class ActionCard(Card):
    def __init__(self, page, action, session=False):
        super().__init__()
        self.action = action
        self.page = page
        c = page.c
        state = c.states.get(action.id, {})
        owned = c.owned(action.id)
        top = QHBoxLayout()
        title = label(branded_text(action.title), "heading")
        top.addWidget(title, 1)
        risk = action.risk.split(":")[0]
        top.addWidget(label(risk + " risk", "tag"))
        self.box.addLayout(top)
        short = branded_text(action.description.split(". ")[0].rstrip(".") + ".")
        self.box.addWidget(label(short, "muted"))
        footer = QHBoxLayout()
        status = (
            "Applied · verified"
            if state.get("active")
            else (
                "Ready to apply"
                if state.get("available")
                else ("Unavailable" if state else "Not inspected")
            )
        )
        if owned and owned[-1][1]["status"] != "applied":
            status = "Recovery required"
        footer.addWidget(label(status, "limeTag" if state.get("active") else "tag"))
        if "Administrator" in action.permissions:
            footer.addWidget(label("Administrator", "tag"))
        if owned:
            footer.addWidget(label("Backup saved", "tag"))
        footer.addStretch()
        more = button(
            "Details",
            lambda: details(
                page.window,
                action.title,
                branded_text(
                    f"{action.description}\n\nExpected effect\n{action.benefit}\n\nRisk\n{action.risk}\n\nRequirements\n{action.windows}\n{action.hardware}\n{action.permissions}\n\nEvidence\n{action.evidence}"
                )
                + "\n\nCurrent status\n"
                + state.get("reason", "Run compatibility inspection first."),
            ),
        )
        footer.addWidget(more)
        if session:
            pick = QCheckBox("Use in session")
            pick.setAccessibleName("Use " + action.title + " in gaming session")
            pick.setChecked(action.id in page.selected)
            page.window.bind_busy(
                pick, lambda: bool(state.get("available")) and not c.session.active
            )
            pick.setToolTip(state.get("reason", "Inspect compatibility first"))
            pick.toggled.connect(lambda checked: page.select(action.id, checked))
            footer.addWidget(pick)
        else:
            if page.batch.isChecked():
                pick = QCheckBox("Select")
                pick.setChecked(action.id in page.selected)
                page.window.bind_busy(
                    pick,
                    lambda: (
                        bool(state.get("available"))
                        and not state.get("active")
                        and not owned
                    ),
                )
                pick.toggled.connect(lambda value: page.select(action.id, value))
                footer.addWidget(pick)
            if owned:
                apply = button("Restore", lambda: page.restore_one(owned[-1][0]))
                page.window.bind_busy(apply)
            else:
                apply = button(
                    "Already configured" if state.get("active") else "Apply",
                    lambda: page.apply_one(action.id),
                    primary=bool(state.get("available") and not state.get("active")),
                )
                page.window.bind_busy(
                    apply,
                    lambda: bool(state.get("available") and not state.get("active")),
                )
            apply.setToolTip(
                state.get("reason", "Inspect compatibility before applying.")
            )
            footer.addWidget(apply)
        self.box.addLayout(footer)
