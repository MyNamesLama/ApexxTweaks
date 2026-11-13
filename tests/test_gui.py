"""Qt integration tests preserve old frontend behavior and exercise the 2.0 workflow."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import Qt, QThread
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton
    from PySide6.QtTest import QTest
except ImportError:
    QApplication = None


@unittest.skipUnless(
    QApplication is not None, "Install the project dependencies for Qt GUI tests"
)
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        from tweaker.ui.controller import Controller
        from tweaker.platform import MockBackend
        from tweaker.gui import App

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = Controller(MockBackend(), Path(self.tmp.name) / "ApexxTweaks")
        self.app = App(self.c)
        self.app.show()
        self.qt.processEvents()

    def tearDown(self):
        self.wait_job()
        if self.c.session.active:
            self.c.session.end()
            self.c.records = list(self.c.engine.records)
        self.app.shutdown()
        self.app.close()
        self.qt.processEvents()

    def wait_job(self):
        deadline = time.monotonic() + 5
        while self.c.busy and time.monotonic() < deadline:
            self.qt.processEvents()
            QTest.qWait(5)
        self.qt.processEvents()
        self.assertFalse(self.c.busy, "Worker did not finish")

    def inspect(self):
        self.c.inspect_states()
        self.wait_job()

    def test_product_branding_and_fresh_data_path(self):
        self.assertIn("ApexxTweaks", self.app.windowTitle())
        self.assertEqual(self.c.data.name, "ApexxTweaks")
        self.assertEqual(self.app.brand.text(), "ApexxTweaks")

    def test_navigation_and_compact_layout(self):
        from tweaker.ui.controller import PAGES

        for name in PAGES:
            self.app.navigate(name, animate=False)
            self.qt.processEvents()
            self.assertEqual(
                self.app.stack.currentWidget(), self.app.pages[name].widget
            )
            self.assertTrue(self.app.nav[name].isChecked())
        self.app.resize(920, 540)
        for name in PAGES:
            self.app.navigate(name, animate=False)
            self.qt.processEvents()
            page = self.app.pages[name]
            self.assertLessEqual(
                page.body.minimumSizeHint().width(),
                page.widget.viewport().width(),
                name,
            )
        self.app.set_collapsed(True)
        self.qt.processEvents()
        self.assertFalse(self.app.brand.isVisible())

    def test_search_category_and_individual_actions(self):
        page = self.app.pages["Optimization"]
        self.app.navigate("Optimization", animate=False)
        page.search.setText("power")
        self.qt.processEvents()
        self.assertEqual(page.list.count(), 2)
        # deferred-deletion widgets are excluded by layout enumeration below
        page.category.setCurrentText("System")
        self.qt.processEvents()
        self.assertEqual(page.list.count(), 1)
        page.search.clear()
        self.qt.processEvents()
        self.assertIn("Fax", page.list.itemAt(0).widget().action.title)

    def test_apply_then_restore_is_verified_and_undoable(self):
        self.inspect()
        self.c.apply("power.high")
        self.wait_job()
        self.assertTrue(self.c.states["power.high"]["active"])
        self.assertEqual(len(self.c.owned()), 1)
        self.c.restore(self.c.owned()[0][0])
        self.wait_job()
        self.assertFalse(self.c.owned())
        self.assertEqual(
            self.c.engine.backend.read("power"), "381b4222-f694-41f0-9685-ff5bb260df2e"
        )

    def test_uninspected_actions_cannot_apply(self):
        errors = []
        self.c.error.connect(errors.append)
        self.assertFalse(self.c.apply("power.high"))
        self.assertTrue(errors)
        self.assertFalse(self.c.records)

    def test_no_automatic_windows_changes_or_idle_monitor(self):
        self.assertFalse(self.c.records)
        self.assertFalse(self.c.busy)
        self.assertFalse(self.app.monitor_timer.isActive())
        self.assertFalse(self.app.watch_timer.isActive())
        self.assertFalse(self.c.hardware)

    def test_live_monitor_pauses_away_from_page(self):
        with patch("tweaker.ui.window.WINDOWS", True):
            self.app.pages["System Monitor"].live.setChecked(True)
            self.app.navigate("System Monitor", animate=False)
            self.qt.processEvents()
            self.assertTrue(self.app.monitor_timer.isActive())
            self.app.navigate("Dashboard", animate=False)
            self.assertFalse(self.app.monitor_timer.isActive())
            self.app.navigate("System Monitor", animate=False)
            self.app.showMinimized()
            self.qt.processEvents()
            self.assertFalse(self.app.monitor_timer.isActive())

    def test_legacy_benchmark_and_journal_loaded_by_gui(self):
        from tweaker.branding import LEGACY_APP_NAME
        from tweaker.engine import Engine
        from tweaker.platform import MockBackend
        from tweaker.ui.controller import Controller

        base = Path(self.tmp.name) / "legacy-fixture"
        legacy = base / LEGACY_APP_NAME
        old = Engine(MockBackend(), legacy)
        old.apply("power.high")
        runs = {"Before": [{"average_fps": 123}], "After": []}
        (legacy / "benchmarks.json").write_text(json.dumps(runs))
        before = (legacy / "history.json").read_bytes()
        with patch.dict(os.environ, {"LOCALAPPDATA": str(base)}):
            restored = Controller(MockBackend())
        self.assertEqual(restored.data, legacy)
        self.assertEqual(restored.runs, runs)
        self.assertEqual(restored.records[0]["action"], "power.high")
        self.assertEqual((legacy / "history.json").read_bytes(), before)
        restored.shutdown()

    def test_saved_action_branding_without_target_change(self):
        from dataclasses import replace
        from tweaker.actions import optional_action
        from tweaker.branding import LEGACY_APP_NAME
        from tweaker.targets import encode

        target = encode("startup", name="Music", command="fixture")
        a = optional_action(
            "startup", target, LEGACY_APP_NAME + " action", {"exists": False}
        )
        self.c.engine.register(
            [replace(a, description=LEGACY_APP_NAME + " description")]
        )
        page = self.app.pages["Optimization"]
        page.search.setText("action")
        page.refresh()
        card = page.list.itemAt(0).widget()
        texts = [w.text() for w in card.findChildren(QLabel)]
        self.assertTrue(any("ApexxTweaks action" in t for t in texts))
        self.assertFalse(any(LEGACY_APP_NAME in t for t in texts))
        self.assertEqual(self.c.engine.actions[a.id].target, target)

    def test_worker_callback_runs_on_gui_thread_and_ui_stays_responsive(self):
        from threading import Event

        release = Event()
        received = []
        self.c.submit(
            "test blocking worker",
            lambda: release.wait(2),
            lambda value: received.append(QThread.currentThread()),
        )
        self.app.navigate("Settings", animate=False)
        self.qt.processEvents()
        self.assertEqual(self.app.current, "Settings")
        self.assertTrue(self.c.busy)
        self.assertFalse(self.app.shutdown())
        release.set()
        self.wait_job()
        self.assertEqual(received, [self.qt.thread()])

    def test_restoration_conflict_visible_and_preserved(self):
        self.inspect()
        self.c.apply("power.high")
        self.wait_job()
        self.c.engine.backend.values["power"] = "outside"
        self.c.inspect_recovery()
        self.wait_job()
        self.assertEqual(self.c.restore_states[0][0], "conflict")
        errors = []
        self.c.error.connect(errors.append)
        self.c.restore(0)
        self.wait_job()
        self.assertTrue(errors)
        self.assertEqual(self.c.engine.backend.read("power"), "outside")
        self.c.engine.backend.values["power"] = self.c.records[0]["desired"]

    def test_session_owns_only_its_changes_and_close_restores(self):
        self.inspect()
        self.c.apply("service.fax")
        self.wait_job()
        self.c.start_session(["power.high"])
        self.wait_job()
        self.assertTrue(self.c.session.active)
        self.app.close()
        self.wait_job()
        self.qt.processEvents()
        self.assertFalse(self.c.session.active)
        self.assertEqual(self.c.engine.backend.read("fax"), "Disabled")

    def test_real_preferences_persist_without_touching_legacy_preferences(self):
        path = self.c.data / "preferences.json"
        path.write_text('{"legacy":true}')
        self.c.preference("reduce_motion", True)
        self.c.preference("monitor_interval", 12)
        from tweaker.ui.controller import Controller

        fresh = Controller(self.c.engine.backend, self.c.data)
        self.assertTrue(fresh.preferences["reduce_motion"])
        self.assertEqual(fresh.preferences["monitor_interval"], 12)
        self.assertEqual(path.read_text(), '{"legacy":true}')
        fresh.shutdown()

    def test_charts_draw_empty_and_collected_data(self):
        monitor = self.app.pages["System Monitor"]
        monitor.sample_received(
            {"cpu": [{"PercentProcessorTime": 25}], "gpu": [], "memory": []}
        )
        self.assertEqual(monitor.history["cpu"], [25])
        self.assertEqual(monitor.history["gpu_engine"], [])
        chart = monitor.charts["cpu"]
        self.assertFalse(chart.grab().isNull())
        histogram = self.app.pages["Benchmarks"].histogram
        histogram.set_values([1, 2, 3, 4, 5, 6, 7])
        self.assertFalse(histogram.grab().isNull())

    def test_actual_card_apply_and_restore_buttons_are_connected(self):
        self.inspect()
        page = self.app.pages["Optimization"]
        self.app.navigate("Optimization", animate=False)
        page.category.setCurrentText("Power")
        page.refresh()
        card = next(
            page.list.itemAt(i).widget()
            for i in range(page.list.count())
            if page.list.itemAt(i).widget().action.id == "power.high"
        )
        apply = next(
            w for w in card.findChildren(QPushButton) if w.accessibleName() == "Apply"
        )
        with patch(
            "tweaker.ui.pages.optimization.confirm", return_value=True
        ) as confirmation:
            QTest.mouseClick(apply, Qt.MouseButton.LeftButton)
            self.wait_job()
            self.assertTrue(confirmation.called)
        self.assertEqual(len(self.c.owned()), 1)
        card = next(
            page.list.itemAt(i).widget()
            for i in range(page.list.count())
            if page.list.itemAt(i).widget().action.id == "power.high"
        )
        restore = next(
            w for w in card.findChildren(QPushButton) if w.accessibleName() == "Restore"
        )
        with patch("tweaker.ui.pages.optimization.confirm", return_value=True):
            QTest.mouseClick(restore, Qt.MouseButton.LeftButton)
            self.wait_job()
        self.assertFalse(self.c.owned())

    def test_unsupported_control_disabled_and_applied_filter(self):
        self.c.states = {
            "power.high": {
                "available": False,
                "active": False,
                "reason": "Unavailable device",
            }
        }
        page = self.app.pages["Optimization"]
        page.category.setCurrentText("Power")
        page.refresh()
        card = next(
            page.list.itemAt(i).widget()
            for i in range(page.list.count())
            if page.list.itemAt(i).widget().action.id == "power.high"
        )
        apply = next(
            w for w in card.findChildren(QPushButton) if w.accessibleName() == "Apply"
        )
        self.assertFalse(apply.isEnabled())
        self.c.states["power.high"] = {
            "available": True,
            "active": True,
            "reason": "Configured",
        }
        page.applied.setChecked(True)
        page.refresh()
        self.assertEqual(page.list.count(), 1)
        self.assertEqual(page.list.itemAt(0).widget().action.id, "power.high")

    def test_failed_watcher_disarms_without_restoring_or_losing_session(self):
        self.inspect()
        self.c.start_session(["power.high"])
        self.wait_job()
        self.c.watch_enabled = True
        with patch(
            "tweaker.ui.controller.diagnostics.fortnite_running",
            side_effect=RuntimeError("Provider failed"),
        ):
            self.c.poll_game()
            self.wait_job()
        self.assertFalse(self.c.watch_enabled)
        self.assertTrue(self.c.session.active)
        self.assertIn("manually", self.app.notice_text.text())

    def test_persistent_conflicting_power_method_not_offered_as_ready(self):
        self.inspect()
        self.c.apply("power.high")
        self.wait_job()
        self.assertFalse(self.c.states["power.ac-performance"]["available"])
        self.inspect()
        self.assertFalse(self.c.states["power.ac-performance"]["available"])

    def test_import_duplicate_archive_and_export_use_existing_files(self):
        context = "same route / GPU / DX12 / cap"
        path = Path(self.tmp.name) / "capture.csv"
        path.write_text("frametime_ms\n" + "10\n" * 1000)
        self.c.import_run(str(path), "Before", context)
        self.wait_job()
        self.assertEqual(self.c.runs["Before"][0]["average_fps"], 100)
        errors = []
        self.c.error.connect(errors.append)
        self.c.import_run(str(path), "After", context)
        self.wait_job()
        self.assertTrue(errors)
        self.assertFalse(self.c.runs["After"])
        export = Path(self.tmp.name) / "results.json"
        self.c.export(export)
        self.assertEqual(
            json.loads(export.read_text())["runs"]["Before"][0]["context"], context
        )
        self.assertTrue(self.c.new_experiment())
        self.assertFalse(self.c.runs["Before"])
        self.assertTrue(list(self.c.data.glob("benchmarks-archive-*.json")))

    def test_profile_selection_never_applies_settings(self):
        self.inspect()
        page = self.app.pages["Gaming Mode"]
        page.profile.setCurrentText("Competitive")
        page.select_profile()
        self.assertEqual(page.selected, {"power.ac-performance"})
        self.assertFalse(self.c.records)
        page.profile.setCurrentText("Balanced")
        page.select_profile()
        self.assertFalse(page.selected)

    def test_missing_metrics_do_not_reuse_stale_ram_as_live_data(self):
        from tweaker.ui.controller import measurements

        result = measurements(
            {"memory": {"totalMB": 8192, "freeMB": 2048}}, {"cpu": [], "memory": []}
        )
        self.assertIsNone(result["ram_percent"])
        self.assertIsNone(result["gpu_engine"])

    def test_bounded_frame_trace_preserves_stutter_peaks(self):
        from tweaker.benchmark import analyze

        frames = [10.0] * 3001
        frames[1234] = 200.0
        result = analyze(frames)
        self.assertLessEqual(len(result["frame_trace_ms"]), 300)
        self.assertEqual(max(result["frame_trace_ms"]), 200)
        self.assertEqual(result["frames"], 3001)

    def test_persistent_batch_survives_filters_and_can_be_restored(self):
        self.inspect()
        page = self.app.pages["Optimization"]
        page.batch.setChecked(True)
        page.select("power.high", True)
        page.select("service.fax", True)
        page.search.setText("nothing-visible")
        self.assertEqual(page.selected, {"power.high", "service.fax"})
        with patch("tweaker.ui.pages.optimization.confirm", return_value=True):
            page.apply_selection()
            self.wait_job()
        self.assertEqual(len(self.c.owned()), 2)
        self.c.restore_all()
        self.wait_job()
        self.assertFalse(self.c.owned())

    def test_batch_refuses_conflicting_power_methods_before_any_write(self):
        self.inspect()
        errors = []
        self.c.error.connect(errors.append)
        self.assertFalse(self.c.apply_many(["power.high", "power.ac-performance"]))
        self.assertFalse(self.c.records)
        self.assertTrue(errors)

    def test_restore_all_deactivates_successfully_restored_session(self):
        self.inspect()
        self.c.start_session(["power.high"])
        self.wait_job()
        self.c.restore_all()
        self.wait_job()
        self.assertFalse(self.c.session.active)
        self.assertFalse(self.c.owned())

    def test_live_monitor_error_stops_sampling_without_faking_a_value(self):
        self.app.pages["System Monitor"].live.setChecked(True)
        with patch(
            "tweaker.ui.controller.diagnostics.activity",
            side_effect=RuntimeError("Counters unavailable"),
        ):
            self.c.inspect_activity()
            self.wait_job()
        self.assertFalse(self.app.pages["System Monitor"].live.isChecked())
        self.assertFalse(self.c.sample)

    def test_comparison_graph_and_table_use_real_derived_metrics(self):
        from tweaker.benchmark import analyze

        before = analyze([10] * 1000)
        before["context"] = "same scene"
        after = analyze([8] * 1000)
        after["context"] = "same scene"
        self.c.runs = {"Before": [before] * 3, "After": [after] * 3}
        page = self.app.pages["Benchmarks"]
        self.app.navigate("Benchmarks", animate=False)
        page.compare_runs()
        self.wait_job()
        self.assertEqual(page.comparison["metrics"]["average_fps"]["delta"], 25)
        self.assertEqual(page.comparison_table.rowCount(), 4)
        self.assertFalse(page.comparison_chart.grab().isNull())

    def test_failed_preference_save_restores_visible_switch(self):
        page = self.app.pages["Settings"]
        with patch(
            "tweaker.ui.controller.atomic_json", side_effect=OSError("Read-only folder")
        ):
            page.motion.setChecked(True)
        self.assertFalse(page.motion.isChecked())
        self.assertFalse(self.c.preferences["reduce_motion"])

    def test_scrollable_sidebar_stays_dark_expanded_and_collapsed(self):
        self.c.preferences["reduce_motion"] = True
        for collapsed in (False, True):
            self.app.set_collapsed(collapsed, persist=False)
            self.qt.processEvents()
            color = self.app.sidebar.grab().toImage().pixelColor(5, 100)
            self.assertLess(max(color.red(), color.green(), color.blue()), 60)

    def test_verified_power_update_and_restore_do_not_leave_stale_dashboard_state(self):
        self.inspect()
        self.c.hardware = {"power": {"power": "381b4222-f694-41f0-9685-ff5bb260df2e"}}
        self.c.apply("power.high")
        self.wait_job()
        self.assertEqual(
            self.c.hardware["power"]["power"],
            self.c.engine.actions["power.high"].desired,
        )
        self.c.restore(0)
        self.wait_job()
        self.assertNotIn("power", self.c.hardware)

    def test_monitor_interval_keyboard_changes_are_persisted(self):
        self.app.navigate("Settings", animate=False)
        slider = self.app.pages["Settings"].interval
        slider.setFocus()
        QTest.keyClick(slider, Qt.Key.Key_Right)
        self.qt.processEvents()
        self.assertEqual(self.c.preferences["monitor_interval"], slider.value())
        self.assertEqual(
            json.loads((self.c.data / "ui-preferences.json").read_text())[
                "monitor_interval"
            ],
            slider.value(),
        )

    def test_inventory_result_stays_accessible_after_a_fortnite_report(self):
        self.c.game_report = {"recommendations": ["Existing Fortnite guidance"]}
        received = []
        with patch(
            "tweaker.ui.controller.diagnostics.startup",
            return_value={"startup": [], "tasks": [], "services": []},
        ):
            self.c.inventory(received.append)
            self.wait_job()
        self.assertEqual(received, [self.c.inventory_report])
        self.assertEqual(
            self.c.game_report["recommendations"], ["Existing Fortnite guidance"]
        )

    def test_new_import_selects_its_metrics_instead_of_an_older_run(self):
        self.app.navigate("Benchmarks", animate=False)
        page = self.app.pages["Benchmarks"]
        for condition, milliseconds in [("Before", 10), ("After", 8)]:
            path = Path(self.tmp.name) / (condition + ".csv")
            path.write_text("frametime_ms\n" + (str(milliseconds) + "\n") * 1000)
            self.c.import_run(str(path), condition, "same scene")
            self.wait_job()
        self.assertEqual(page.table.currentRow(), 1)
        self.assertEqual(page.metrics[0].value.text(), "125.00")
