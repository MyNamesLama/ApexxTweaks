"""Desktop shell, navigation and strictly opt-in timer lifecycle."""

import weakref
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QStackedWidget,
    QProgressBar,
    QGraphicsOpacityEffect,
    QScrollArea,
)
from shiboken6 import isValid
from .controller import Controller, PAGES
from .theme import stylesheet, ACCENT
from .widgets import label, FlowLayout, NavigationButton
from .icons import icon
from .pages import (
    Dashboard,
    Optimization,
    Gaming,
    Monitor,
    Benchmarks,
    RestoreCenter,
    Settings,
)
from ..branding import APP_NAME
from ..platform import WINDOWS


class App(QMainWindow):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller if controller is not None else Controller()
        self.setWindowTitle(APP_NAME + " · Performance, with purpose")
        self.setWindowIcon(icon("logo", ACCENT, 64))
        self.resize(1260, 870)
        self.setMinimumSize(920, 480)
        if QApplication.platformName() != "offscreen" and self.screen():
            area = self.screen().availableGeometry()
            self.resize(
                min(1260, max(920, area.width() - 32)),
                min(870, max(480, area.height() - 40)),
            )
        self.setStyleSheet(stylesheet())
        self._bindings = []
        self.close_requested = False
        self.collapsed = False
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(224)
        sidebar_box = QVBoxLayout(self.sidebar)
        sidebar_box.setContentsMargins(0, 0, 0, 0)
        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        nav_body = QWidget()
        nav_body.setObjectName("navigationBody")
        self.nav_scroll.viewport().setObjectName("navigationViewport")
        self.nav_scroll.setWidget(nav_body)
        sidebar_box.addWidget(self.nav_scroll)
        side = QVBoxLayout(nav_body)
        side.setContentsMargins(14, 22, 14, 18)
        side.setSpacing(7)
        brandrow = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icon("logo", ACCENT, 30).pixmap(30, 30))
        brandrow.addWidget(logo)
        self.brand = label(APP_NAME, "brand")
        brandrow.addWidget(self.brand)
        brandrow.addStretch()
        side.addLayout(brandrow)
        self.edition = label("PERFORMANCE LAB  /  2.0", "caption")
        side.addWidget(self.edition)
        side.addSpacing(26)
        self.nav = {}
        keys = [
            "dashboard",
            "optimization",
            "gaming",
            "monitor",
            "benchmarks",
            "restore",
            "settings",
        ]
        for i, (name, key) in enumerate(zip(PAGES, keys)):
            if name == "Settings":
                side.addStretch()
            b = NavigationButton("  " + name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setIcon(icon(key))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(name)
            b.setAccessibleName(name)
            b.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            side.addWidget(b)
            self.nav[name] = b
            shortcut = QShortcut(QKeySequence("Ctrl+" + str(i + 1)), self)
            shortcut.activated.connect(lambda n=name: self.navigate(n))
        self.safety = label("DOCUMENTED. REVERSIBLE.", "caption")
        side.addSpacing(12)
        side.addWidget(self.safety)
        self.collapse = NavigationButton("Collapse sidebar")
        self.collapse.setObjectName("collapse")
        self.collapse.setIcon(icon("menu"))
        self.collapse.setAccessibleName("Collapse or expand sidebar")
        self.collapse.setToolTip("Collapse / expand navigation")
        self.collapse.clicked.connect(self.toggle_sidebar)
        footer = QHBoxLayout()
        footer.setContentsMargins(14, 5, 14, 10)
        footer.addWidget(self.collapse, alignment=Qt.AlignmentFlag.AlignLeft)
        footer.addStretch()
        sidebar_box.addLayout(footer)
        outer.addWidget(self.sidebar)
        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(right, 1)
        bar = QFrame()
        bar.setObjectName("topbar")
        barbox = FlowLayout()
        bar.setLayout(barbox)
        barbox.setContentsMargins(28, 15, 28, 15)
        self.breadcrumb = label("Workspace  /  Dashboard", "muted")
        barbox.addWidget(self.breadcrumb)
        self.environment = label(
            "Windows desktop"
            if WINDOWS
            else "Linux preview · Windows actions unavailable",
            "tag",
            False,
        )
        barbox.addWidget(self.environment)
        right.addWidget(bar)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        right.addWidget(self.progress)
        self.notice = QFrame()
        self.notice.setObjectName("notice")
        noticebox = QHBoxLayout(self.notice)
        self.notice_text = label("")
        noticebox.addWidget(self.notice_text, 1)
        dismiss = QToolButton()
        dismiss.setText("×")
        dismiss.setAccessibleName("Dismiss notification")
        dismiss.clicked.connect(self.notice.hide)
        noticebox.addWidget(dismiss)
        self.notice.hide()
        right.addWidget(self.notice)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        self.current = "Dashboard"
        self.pages = {}
        for name, cls in zip(
            PAGES,
            [
                Dashboard,
                Optimization,
                Gaming,
                Monitor,
                Benchmarks,
                RestoreCenter,
                Settings,
            ],
        ):
            self.pages[name] = cls(self)
            self.stack.addWidget(self.pages[name].widget)
        self.statusBar().showMessage(
            "Ready · No Windows settings changed automatically"
        )
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(
            lambda: self.controller.inspect_activity(quiet=True)
        )
        self.watch_timer = QTimer(self)
        self.watch_timer.setInterval(5000)
        self.watch_timer.timeout.connect(self.controller.poll_game)
        self.fade = QPropertyAnimation(self)
        self.fade.setDuration(130)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        self.sidebar_animation.setDuration(150)
        self.controller.changed.connect(self.on_changed)
        self.controller.busy_changed.connect(self.on_busy)
        self.controller.error.connect(self.show_error)
        self.controller.notice.connect(self.toast)
        self.controller.monitoring_failed.connect(
            lambda: self.pages["System Monitor"].live.setChecked(False)
        )
        self.set_collapsed(
            self.controller.preferences["sidebar_collapsed"], persist=False
        )
        self.navigate(self.controller.preferences["startup_page"], animate=False)
        if self.controller.owned():
            self.toast(
                "Saved changes found. Open Restore Center to inspect or undo them."
            )

    def bind_busy(self, widget, predicate=None):
        predicate = predicate or (lambda: True)
        self._bindings.append((weakref.ref(widget), predicate))
        widget.setEnabled(not self.controller.busy and bool(predicate()))

    def on_busy(self, busy, title):
        if busy:
            self.notice.hide()
        self.progress.setVisible(busy)
        self.statusBar().showMessage(title)
        live = []
        for ref, predicate in self._bindings:
            widget = ref()
            if widget is not None and isValid(widget):
                widget.setEnabled(not busy and bool(predicate()))
                live.append((ref, predicate))
        self._bindings = live
        self.pages["Gaming Mode"].mode_switch.setEnabled(not busy)

    def on_changed(self):
        self.pages[self.current].refresh()
        self.update_timers()
        if (
            self.close_requested
            and not self.controller.busy
            and not self.controller.session.active
        ):
            self.close_requested = False
            QTimer.singleShot(0, self.close)

    def navigate(self, name, animate=True):
        if name not in self.pages:
            return
        self.fade.stop()
        old = self.stack.currentWidget()
        if old:
            old.setGraphicsEffect(None)
        self.current = name
        page = self.pages[name]
        self.stack.setCurrentWidget(page.widget)
        self.breadcrumb.setText("Workspace  /  " + name)
        for key, b in self.nav.items():
            b.setChecked(key == name)
        page.refresh()
        if (
            animate
            and not self.controller.preferences["reduce_motion"]
            and self.isVisible()
        ):
            effect = QGraphicsOpacityEffect(page.widget)
            page.widget.setGraphicsEffect(effect)
            self.fade.setTargetObject(effect)
            self.fade.setPropertyName(b"opacity")
            self.fade.setStartValue(0.72)
            self.fade.setEndValue(1.0)
            self.fade.start()
        self.update_timers()

    def toggle_sidebar(self):
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, value, persist=True):
        self.collapsed = value
        target = 76 if value else 224
        self.collapse.setText("" if value else "Collapse sidebar")
        self.brand.setVisible(not value)
        self.edition.setVisible(not value)
        self.safety.setVisible(not value)
        for name, b in self.nav.items():
            b.setText("" if value else "  " + name)
        self.sidebar_animation.stop()
        # The layout owns width; finite animation is disabled by Reduce motion.
        self.sidebar.setMinimumWidth(0)
        if (
            persist
            and self.isVisible()
            and not self.controller.preferences["reduce_motion"]
        ):
            self.sidebar_animation.setStartValue(self.sidebar.width())
            self.sidebar_animation.setEndValue(target)
            self.sidebar_animation.start()
        else:
            self.sidebar.setMaximumWidth(target)
        self.sidebar.setMinimumWidth(target if not persist else 0)
        if persist:
            try:
                self.controller.preference("sidebar_collapsed", value)
            except Exception as error:
                self.show_error(str(error))

    def update_timers(self):
        if not hasattr(self, "monitor_timer"):
            return
        monitor = self.pages["System Monitor"]
        live = (
            WINDOWS
            and monitor.live.isChecked()
            and self.current == "System Monitor"
            and self.isVisible()
            and not self.isMinimized()
        )
        interval = self.controller.preferences["monitor_interval"] * 1000
        if live:
            if (
                not self.monitor_timer.isActive()
                or self.monitor_timer.interval() != interval
            ):
                self.monitor_timer.start(interval)
        else:
            self.monitor_timer.stop()
        watching = (
            WINDOWS
            and self.controller.watch_enabled
            and bool(self.controller.session.active)
        )
        if watching and not self.watch_timer.isActive():
            self.watch_timer.start()
        elif not watching:
            self.watch_timer.stop()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.update_timers()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_timers()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.update_timers()

    def toast(self, text):
        self.notice_text.setStyleSheet("")
        self.notice_text.setText(text)
        self.notice.show()
        self.statusBar().showMessage(text)

    def show_error(self, text):
        self.close_requested = False
        self.toast("Operation could not complete. " + text)
        self.notice_text.setStyleSheet("color: #f2c19f;")

    def open_settings(self, uri):
        if not WINDOWS:
            self.toast("This guided workflow requires Windows.")
            return
        import os

        try:
            os.startfile("ms-settings:" + uri)
        except OSError as error:
            self.show_error(str(error))

    def shutdown(self):
        if self.controller.busy or self.controller.session.active:
            return False
        self.monitor_timer.stop()
        self.watch_timer.stop()
        self.fade.stop()
        self.sidebar_animation.stop()
        return self.controller.shutdown()

    def closeEvent(self, event):
        if self.controller.busy:
            self.toast("Wait for the current operation to finish before closing.")
            event.ignore()
            return
        if self.controller.session.active:
            self.close_requested = True
            self.controller.end_session()
            event.ignore()
            return
        self.shutdown()
        event.accept()
