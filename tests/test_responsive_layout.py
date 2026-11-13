"""Geometry regressions run unchanged on Linux and native Windows Qt font metrics."""

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import Qt, QEvent
    from PySide6.QtWidgets import QApplication, QWidget, QPushButton
    from PySide6.QtTest import QTest
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, "Install the declared Qt dependency")
class ResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        print(
            f"Qt layout platform={cls.qt.platformName()} scale={os.environ.get('QT_SCALE_FACTOR', 'default')} "
            f"DPR={cls.qt.primaryScreen().devicePixelRatio()} DPI={cls.qt.primaryScreen().logicalDotsPerInch()}"
        )

    def setUp(self):
        from tweaker.ui.controller import Controller
        from tweaker.ui.window import App
        from tweaker.platform import MockBackend

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.c = Controller(MockBackend(), Path(self.temp.name) / "ApexxTweaks")
        self.app = App(self.c)
        self.app.resize(920, 540)
        self.app.show()
        self.settle()
        self.stylesheet = self.app.styleSheet()

    def settle(self):
        for _ in range(3):
            self.qt.processEvents()
            self.qt.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def tearDown(self):
        self.app.shutdown()
        self.app.close()
        self.settle()

    def assert_fits(self, page, name):
        self.assertLessEqual(
            page.body.minimumSizeHint().width(), page.widget.viewport().width(), name
        )
        self.assertLessEqual(
            page.body.width(), page.widget.viewport().width(), name + " actual body"
        )
        self.assertEqual(
            page.widget.horizontalScrollBar().maximum(),
            0,
            name + " horizontal overflow",
        )
        # This checks actual allocated text height, not only the declared minimum.
        from tweaker.ui.text import WrappingLabel

        for text in page.body.findChildren(WrappingLabel):
            if text.isVisible() and text.text():
                self.assertGreaterEqual(
                    text.height(),
                    text.heightForWidth(text.width()),
                    name + ": " + text.text()[:80],
                )

    def enlarge_fonts(self, factor):
        # Windows Segoe UI/fallback metrics differ from Linux. Stress real layout
        # and paint geometry as well as the separate DPI subprocess matrix.
        self.app.setStyleSheet(
            re.sub(
                r"font-size: (\d+)px",
                lambda match: f"font-size: {round(int(match[1]) * factor)}px",
                self.stylesheet,
            )
        )
        self.settle()

    def test_every_page_fits_with_wider_font_metrics_and_populated_cards(self):
        from tweaker.ui.controller import PAGES

        self.c.hardware = {
            "platform": "Microsoft Windows 11 Pro for Workstations "
            + ("VeryLongEditionToken" * 12),
            "build": "26100",
            "cpu": [{"Name": "Intel Core Ultra Processor " + ("ModelIdentifier" * 20)}],
            "gpu": [{"Name": "NVIDIA GeForce " + ("AdapterIdentifier" * 20)}],
            "memory": {"totalMB": 32768, "freeMB": 12345},
            "power": {"power": "381b4222-f694-41f0-9685-ff5bb260df2e"},
        }
        self.c.engine.apply("service.fax")
        self.c.records = list(self.c.engine.records)
        for factor in (1.0, 1.25, 1.5, 2.0):
            self.enlarge_fonts(factor)
            for name in PAGES:
                with self.subTest(factor=factor, page=name):
                    self.app.navigate(name, animate=False)
                    self.settle()
                    self.assert_fits(self.app.pages[name], name)

    def test_dashboard_reflows_back_to_wide_layout_without_hiding_cards(self):
        self.app.navigate("Dashboard", animate=False)
        dashboard = self.app.pages["Dashboard"]
        # The transitions are tested against actual font metrics, not Linux-only
        # pixel breakpoints. The original compact test still uses exactly 920px.
        preferred = max(
            240, *(card.responsive_width_hint() for card in dashboard.metrics.values())
        )
        chrome = self.app.width() - dashboard.grid.geometry().width()
        wide = max(1440, chrome + 3 * preferred + 2 * dashboard.grid.spacing() + 20)
        medium = max(920, chrome + 2 * preferred + dashboard.grid.spacing() + 20)
        self.app.resize(wide, 850)
        self.settle()
        self.assertEqual(dashboard.grid.columns, 3)
        self.app.resize(medium, 540)
        self.settle()
        self.assertEqual(dashboard.grid.columns, 2)
        self.app.resize(920, 540)
        self.enlarge_fonts(3)
        self.settle()
        self.assertEqual(dashboard.grid.columns, 1)
        self.assert_fits(dashboard, "Dashboard")
        self.assertEqual(dashboard.grid.count(), 6)
        previous = None
        for card in dashboard.metrics.values():
            self.assertTrue(card.isVisible())
            if previous is not None:
                self.assertGreaterEqual(card.y(), previous.geometry().bottom() + 1)
            previous = card
        self.enlarge_fonts(1)
        self.app.resize(wide, 850)
        self.settle()
        self.assertEqual(dashboard.grid.columns, 3)

    def test_flow_rows_measure_wrapped_height_and_do_not_overlap(self):
        from tweaker.ui.widgets import FlowLayout, label, button

        host = QWidget()
        host.resize(320, 600)
        layout = FlowLayout()
        host.setLayout(layout)
        text = label("Full diagnostic text " + ("UNBROKEN_PATH_COMPONENT" * 40))
        buttons = [
            button("Inspect system", lambda: None),
            button("Restore original values", lambda: None),
        ]
        layout.addWidget(text)
        for control in buttons:
            layout.addWidget(control)
        host.show()
        self.settle()
        self.assertEqual(host.width(), 320)
        self.assertGreaterEqual(text.height(), text.heightForWidth(text.width()))
        for i in range(layout.count()):
            a = layout.itemAt(i).geometry()
            self.assertTrue(host.contentsRect().contains(a))
            for j in range(i):
                self.assertFalse(a.intersects(layout.itemAt(j).geometry()))
        host.close()

    def test_wrapped_label_preserves_plain_text_selection_and_copy(self):
        from tweaker.ui.widgets import label

        original = "C:\\🚀VeryLongBackupPathWithoutSpaces\\" + ("snapshot-" * 70)
        text = label(original)
        text.resize(200, text.heightForWidth(200))
        text.show()
        self.settle()
        self.assertGreater(text.heightForWidth(200), text.fontMetrics().height())
        text.setFocus()
        QTest.keyClick(text, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(text, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.qt.clipboard().text(), original)
        self.assertEqual(text.text(), original)
        text.close()

    def test_navigation_captions_and_action_footers_remain_accessible(self):
        self.enlarge_fonts(2)
        self.app.navigate("Optimization", animate=False)
        page = self.app.pages["Optimization"]
        page.batch.setChecked(True)
        self.settle()
        self.assert_fits(page, "Optimization with selection")
        self.assertLessEqual(
            self.app.nav_scroll.widget().minimumSizeHint().width(),
            self.app.nav_scroll.viewport().width(),
        )
        for nav in self.app.nav.values():
            self.assertGreaterEqual(nav.height(), nav.heightForWidth(nav.width()))
        for i in range(page.list.count()):
            card = page.list.itemAt(i).widget()
            for control in card.findChildren(QPushButton):
                if control.isVisible():
                    self.assertGreaterEqual(
                        control.width(), control.minimumSizeHint().width()
                    )
                    self.assertTrue(
                        control.parentWidget()
                        .contentsRect()
                        .contains(control.geometry())
                    )
