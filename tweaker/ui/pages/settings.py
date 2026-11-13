"""Product page. Controls delegate to the controller, never Windows writes."""

from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QComboBox,
    QFileDialog,
    QSlider,
)
from ...branding import APP_NAME
from ... import __version__
from ..controller import PAGES
from ..widgets import (
    Card,
    Switch,
    label,
    button,
)


from .common import Page, details, page_header, row, control


class Settings(Page):
    def __init__(self, window):
        super().__init__(window)
        page_header(
            self.box, "Settings", "A quieter app, configured around your workflow."
        )
        appearance = Card()
        appearance.box.addWidget(label("Appearance & startup", "heading"))
        appearance.box.addWidget(
            label(
                "Apexx Dark · near-black surfaces with electric lime accents", "muted"
            )
        )
        self.motion = Switch(
            "Reduce interface motion", self.c.preferences["reduce_motion"]
        )
        self.minimized = Switch(
            "Start minimized", self.c.preferences["start_minimized"]
        )
        for text, widget in [
            ("Reduce interface motion", self.motion),
            ("Start minimized", self.minimized),
        ]:
            r = QHBoxLayout()
            r.addWidget(label(text), 1)
            r.addWidget(widget)
            appearance.box.addLayout(r)
        self.motion.toggled.connect(lambda value: self.save("reduce_motion", value))
        self.minimized.toggled.connect(
            lambda value: self.save("start_minimized", value)
        )
        startup = QHBoxLayout()
        startup.addWidget(label("Startup page"), 1)
        self.startup = QComboBox()
        self.startup.addItems(PAGES)
        self.startup.setCurrentText(self.c.preferences["startup_page"])
        startup.addWidget(self.startup)
        appearance.box.addLayout(startup)
        self.startup.currentTextChanged.connect(
            lambda value: self.save("startup_page", value)
        )
        self.box.addWidget(appearance)
        monitor = Card()
        monitor.box.addWidget(label("Monitoring", "heading"))
        monitor.box.addWidget(
            label(
                "Monitoring is opt-in and pauses away from System Monitor. Longer intervals reduce collection overhead.",
                "muted",
            )
        )
        self.interval = QSlider(Qt.Orientation.Horizontal)
        self.interval.setRange(3, 15)
        self.interval.setValue(self.c.preferences["monitor_interval"])
        self.interval.setAccessibleName("Monitoring interval in seconds")
        self.interval_text = label(str(self.interval.value()) + " seconds", "tag")
        self.interval.valueChanged.connect(
            lambda v: self.interval_text.setText(str(v) + " seconds")
        )
        self.interval.valueChanged.connect(
            lambda value: self.save("monitor_interval", value)
        )
        monitor.box.addLayout(row(self.interval, self.interval_text))
        self.box.addWidget(monitor)
        data = Card()
        data.box.addWidget(label("Data, backups & diagnostics", "heading"))
        data.box.addWidget(
            label(
                "Safety and error logs are always retained. Settings and rollback history remain local. No telemetry is sent.",
                "muted",
            )
        )
        data.box.addWidget(label(str(self.c.data), "muted"))
        data.box.addLayout(
            row(
                button(
                    "Open data folder",
                    lambda: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(self.c.data))
                    ),
                ),
                button("View diagnostic log", self.logs),
                control(self, "Export diagnostic bundle", self.export_diagnostics),
            )
        )
        self.box.addWidget(data)
        about = Card()
        about.box.addWidget(label(APP_NAME + " " + __version__, "heading"))
        about.box.addWidget(
            label(
                "Windows gaming performance lab. Built for measured changes and reversible control.\nNo unsupported performance claims. No game injection or anti-cheat bypass.",
                "muted",
            )
        )
        about.box.addLayout(
            row(
                button(
                    "GitHub repository",
                    lambda: QDesktopServices.openUrl(
                        QUrl("https://github.com/MyNamesLama/ApexxTweaks")
                    ),
                ),
                button("Licenses & application information", self.about),
            )
        )
        self.box.addWidget(about)
        self.box.addStretch()

    def save(self, key, value):
        try:
            self.c.preference(key, value)
            self.window.update_timers()
        except Exception as error:
            for widget, key in [
                (self.motion, "reduce_motion"),
                (self.minimized, "start_minimized"),
            ]:
                widget.blockSignals(True)
                widget.setChecked(self.c.preferences[key])
                widget.blockSignals(False)
            self.startup.blockSignals(True)
            self.startup.setCurrentText(self.c.preferences["startup_page"])
            self.startup.blockSignals(False)
            self.interval.blockSignals(True)
            self.interval.setValue(self.c.preferences["monitor_interval"])
            self.interval.blockSignals(False)
            self.interval_text.setText(
                str(self.c.preferences["monitor_interval"]) + " seconds"
            )
            self.window.show_error(str(error))

    def logs(self):
        path = self.c.data / "events.log"

        def tail():
            if not path.exists():
                return "No events logged yet."
            with path.open("rb") as file:
                file.seek(0, 2)
                length = file.tell()
                file.seek(max(0, length - 262144))
                text = file.read().decode("utf-8", errors="replace")
            return (
                "Showing the last 256 KiB. Full log remains in the data folder.\n\n"
                if length > 262144
                else ""
            ) + text

        self.c.submit(
            "Reading diagnostic log",
            tail,
            lambda text: details(self.window, "Diagnostic log", text),
        )

    def export_diagnostics(self):
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Export diagnostics", "", "JSON (*.json)"
        )
        if path:
            from ..engine import atomic_json

            try:
                atomic_json(
                    Path(path),
                    {
                        "version": __version__,
                        "hardware": self.c.hardware,
                        "sample": self.c.sample,
                        "telemetry": self.c.last_telemetry,
                        "history": self.c.records,
                    },
                )
                self.window.toast(
                    "Diagnostics exported. Review local paths and usernames before sharing."
                )
            except Exception as error:
                self.window.show_error(str(error))

    def about(self):
        details(
            self.window,
            "About " + APP_NAME,
            f"{APP_NAME} {__version__}\n\nPython and Qt for Python (PySide6 Essentials). Qt is provided under its applicable LGPL/commercial terms; see bundled license notices. Application source is MIT licensed.\n\nSystem changes require Windows validation. No anti-cheat certification or FPS improvement is claimed.\n\nApplication data: {self.c.data}",
        )
