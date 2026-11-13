"""Serialized asynchronous adapter over the unchanged optimization backend."""

import copy
import json
import math
import time
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool
from ..engine import Engine, atomic_json
from ..platform import WindowsBackend, powershell
from ..branding import data_directory
from ..session import GamingSession
from .. import diagnostics, discovery, telemetry, benchmark
from ..analysis import rows
from ..fortnite import recommendations
from ..targets import classify_inventory
from ..windows_controls import ProcessExpired

PAGES = [
    "Dashboard",
    "Optimization",
    "Gaming Mode",
    "System Monitor",
    "Benchmarks",
    "Restore Center",
    "Settings",
]
DEFAULTS = {
    "reduce_motion": False,
    "start_minimized": False,
    "sidebar_collapsed": False,
    "startup_page": "Dashboard",
    "monitor_interval": 5,
}


class TaskSignals(QObject):
    finished = Signal(object)


class Task(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = TaskSignals()

    def run(self):
        try:
            result = (self.fn(), None)
        except Exception as error:
            result = (None, str(error))
        self.signals.finished.emit(result)


class Controller(QObject):
    changed = Signal()
    busy_changed = Signal(bool, str)
    error = Signal(str)
    notice = Signal(str)
    sample_ready = Signal(object)
    monitoring_failed = Signal()

    def __init__(self, backend=None, root=None):
        super().__init__()
        self.data = Path(root) if root is not None else data_directory()
        self.engine = Engine(
            backend if backend is not None else WindowsBackend(), self.data
        )
        self.session = GamingSession(self.engine)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.busy = False
        self._callback = None
        self._task = None
        self.closed = False
        self.states = {}
        self.restore_states = {}
        self.hardware = {}
        self.sample = {}
        self.last_telemetry = None
        self.game_report = None
        self.inventory_report = None
        self.discovery_report = None
        self.last_import = None
        self.network_result = None
        self.watch_enabled = False
        self.game_status = "Not inspected"
        self.records = copy.deepcopy(self.engine.records)
        self.runs = self._load("benchmarks.json", {"Before": [], "After": []})
        if not isinstance(self.runs, dict) or any(
            not isinstance(self.runs.get(k), list) for k in ("Before", "After")
        ):
            raise RuntimeError(
                "Invalid benchmark file. Preserve it before repairing it; no results were overwritten."
            )
        self.preferences = dict(DEFAULTS)
        saved = self._load("ui-preferences.json", {})
        if not isinstance(saved, dict):
            raise RuntimeError(
                "Invalid UI preferences; preserve the file before repairing it."
            )
        self.preferences.update(saved)
        for key in ("reduce_motion", "start_minimized", "sidebar_collapsed"):
            self.preferences[key] = (
                self.preferences[key]
                if type(self.preferences[key]) is bool
                else DEFAULTS[key]
            )
        if self.preferences.get("startup_page") not in PAGES:
            self.preferences["startup_page"] = "Dashboard"
        interval = self.preferences.get("monitor_interval")
        if type(interval) is not int or not 3 <= interval <= 15:
            self.preferences["monitor_interval"] = 5

    def _load(self, name, default):
        path = self.data / name
        return (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else copy.deepcopy(default)
        )

    def preference(self, key, value):
        updated = dict(self.preferences)
        updated[key] = value
        atomic_json(self.data / "ui-preferences.json", updated)
        self.preferences = updated
        self.changed.emit()

    def submit(self, title, fn, callback=None, quiet=False):
        if self.busy or self.closed:
            if not quiet:
                self.notice.emit(
                    "Another operation is running. Navigation remains available; try again when it finishes."
                )
            return False
        self.busy = True
        self._callback = callback
        self._job_title = title
        self.busy_changed.emit(True, title)
        task = Task(fn)
        self._task = task
        task.signals.finished.connect(self._finished)
        self.pool.start(task)
        return True

    @Slot(object)
    def _finished(self, result):
        value, error = result
        callback = self._callback
        self._callback = None
        self._task = None
        self.busy = False
        self.records = copy.deepcopy(self.engine.records)
        self.busy_changed.emit(False, "Ready")
        if error:
            if self._job_title == "Reading resource counters":
                self.monitoring_failed.emit()
            if self._job_title == "Checking game session":
                self.watch_enabled = False
                self.game_status = "Game detection unavailable"
                error += " Automatic game watching stopped; end Gaming Mode manually to restore."
            self.states = {}
            self.restore_states = {}
            self.hardware.pop("power", None)
            try:
                self.engine.log(error)
            except OSError:
                pass
            self.error.emit(error)
        elif callback:
            try:
                callback(value)
            except Exception as problem:
                self.error.emit(str(problem))
        self.changed.emit()

    def inspect_states_sync(self):
        states = {}
        for action in list(self.engine.actions.values()):
            try:
                current = self.engine.backend.read(action.target)
                active = current == action.desired
                if any(
                    r["status"] != "restored"
                    and r["action"] != action.id
                    and (
                        r["target"] == action.target
                        or {r["target"], action.target} == {"power", "ac-mode"}
                    )
                    for r in self.engine.records
                ):
                    states[action.id] = {
                        "available": False,
                        "active": active,
                        "reason": "Restore the existing experiment on this target first.",
                        "current": current,
                    }
                    continue
                if not active and hasattr(self.engine.backend, "prepare"):
                    self.engine.backend.prepare(action)
                states[action.id] = {
                    "available": True,
                    "active": active,
                    "reason": "Configured" if active else "Ready to apply",
                    "current": current,
                }
            except Exception as error:
                states[action.id] = {
                    "available": False,
                    "active": False,
                    "reason": str(error),
                }
        return states

    def inspect_states(self):
        return self.submit(
            "Checking action compatibility", self.inspect_states_sync, self._set_states
        )

    def _set_states(self, states):
        self.states = states

    def inspect_system(self):
        def inspect():
            hardware = diagnostics.inventory()
            power = {}
            for target in ("power", "ac-mode"):
                try:
                    power[target] = self.engine.backend.read(target)
                except Exception:
                    pass
            try:
                sample = diagnostics.activity()
            except Exception:
                sample = {}
            return {"hardware": hardware, "power": power, "sample": sample}

        def done(result):
            self.hardware = result["hardware"]
            self.hardware["power"] = result["power"]
            self.sample = result["sample"]
            self.sample_ready.emit(self.sample)
            self.notice.emit(
                "System information inspected. No Windows settings were changed."
            )

        return self.submit("Inspecting system information", inspect, done)

    def inspect_activity(self, quiet=False):
        def done(sample):
            self.sample = sample
            self.sample_ready.emit(sample)

        return self.submit(
            "Reading resource counters", diagnostics.activity, done, quiet
        )

    def sustained(self):
        def done(result):
            self.last_telemetry = result
            atomic_json(self.data / "last-telemetry.json", result)
            self.notice.emit(
                "Sustained sample saved. Findings are screening candidates, not proof of a bottleneck."
            )

        return self.submit(
            "Collecting bounded sustained samples", telemetry.collect, done
        )

    def discover(self):
        def work():
            actions, rejected = discovery.discover()
            self.engine.register(actions)
            return self.inspect_states_sync(), len(actions), rejected

        def done(result):
            self.states, count, rejected = result
            self.discovery_report = {
                "available": [a.title for a in self.engine.actions.values()],
                "read_only": rejected,
            }
            self.notice.emit(
                f"{count} approved optional-app actions discovered; {len(rejected)} entries remain read-only."
            )

        return self.submit("Discovering approved optional applications", work, done)

    def apply(self, action_id):
        state = self.states.get(action_id, {})
        if not state.get("available"):
            self.error.emit(
                "Inspect compatibility first. Unavailable or uninspected actions cannot be applied."
            )
            return False

        def done(result):
            self.states[action_id] = {
                "available": True,
                "active": True,
                "reason": "Applied and verified",
            }
            target = self.engine.actions[action_id].target
            if target in ("power", "ac-mode"):
                self.hardware.setdefault("power", {})[target] = self.engine.actions[
                    action_id
                ].desired
            if target in ("power", "ac-mode"):
                for key, action in self.engine.actions.items():
                    if action.target in ("power", "ac-mode") and key != action_id:
                        self.states[key] = {
                            "available": False,
                            "active": False,
                            "reason": "Restore the existing power experiment first.",
                        }
            self.restore_states = {}
            self.notice.emit(result)

        return self.submit(
            "Applying approved change", lambda: self.engine.apply(action_id), done
        )

    def apply_many(self, ids):
        if not ids:
            return False
        if any(not self.states.get(key, {}).get("available") for key in ids):
            self.error.emit(
                "Every selected action must pass compatibility inspection first."
            )
            return False
        targets = {self.engine.actions[key].target for key in ids}
        if {"power", "ac-mode"} <= targets:
            self.error.emit(
                "Choose one power method per experiment, not both. No settings were changed."
            )
            return False

        def work():
            results = []
            for key in ids:
                try:
                    results.append(self.engine.apply(key))
                except Exception as error:
                    raise RuntimeError(
                        f"{key}: {error}. Earlier successful changes, if any, remain in Restore Center for undo."
                    ) from error
            return results

        def done(results):
            self.states = {}
            self.restore_states = {}
            self.hardware.pop("power", None)
            self.notice.emit(
                f"{len(results)} selected actions processed. Inspect compatibility to refresh their current state."
            )

        return self.submit("Applying approved selection", work, done)

    def restore(self, index):
        def done(_):
            self.states = {}
            self.restore_states = {}
            self.hardware.pop("power", None)
            self.notice.emit("Original setting restored and verified.")

        return self.submit(
            "Restoring original setting",
            lambda: self.engine.restore(self.engine.records[index]),
            done,
        )

    def restore_all(self):
        def done(_):
            self.states = {}
            self.restore_states = {}
            self.hardware.pop("power", None)
            self.notice.emit("All journal-owned changes restored and verified.")

        def work():
            self.engine.restore_all()
            if self.session.active:
                self.session.end()

        return self.submit("Restoring journal-owned changes", work, done)

    def inspect_recovery(self):
        def work():
            result = {}
            for i, record in enumerate(self.engine.records):
                if record["status"] == "restored":
                    continue
                try:
                    current = self.engine.backend.read(record["target"])
                    if current not in (record["original"], record["desired"]):
                        result[i] = (
                            "conflict",
                            "Changed outside ApexxTweaks. Automatic restore will refuse to overwrite it.",
                        )
                    else:
                        result[i] = (
                            "ready",
                            "Original value can be restored; checked again before writing.",
                        )
                except ProcessExpired:
                    result[i] = (
                        "ready",
                        "Original optional process exited; restore records completion without a PID write.",
                    )
                except Exception as error:
                    result[i] = ("unavailable", str(error))
            return result

        def done(result):
            self.restore_states = result

        return self.submit("Checking restoration conflicts", work, done)

    def start_session(self, ids):
        if any(not self.states.get(k, {}).get("available") for k in ids):
            self.error.emit("Inspect and select only compatible session actions first.")
            return False

        def done(_):
            self.states = {}
            self.hardware.pop("power", None)
            self.notice.emit(
                "Gaming Mode is active. Only changes owned by this session will be restored."
            )

        return self.submit(
            "Starting approved Gaming Mode", lambda: self.session.start(ids), done
        )

    def end_session(self):
        def done(_):
            self.states = {}
            self.restore_states = {}
            self.hardware.pop("power", None)
            self.notice.emit("Gaming Mode ended. Session-owned changes restored.")

        return self.submit("Restoring Gaming Mode changes", self.session.end, done)

    def poll_game(self):
        def work():
            running = diagnostics.fortnite_running()
            ended = self.session.observe(running) if self.session.active else False
            return running, ended

        def done(result):
            running, ended = result
            self.game_status = "Fortnite running" if running else "Fortnite not running"
            if ended:
                self.states = {}
                self.hardware.pop("power", None)
                self.notice.emit(
                    "Fortnite exited. Gaming Mode restored its session-owned changes."
                )

        return self.submit("Checking game session", work, done, quiet=True)

    def inspect_game(self):
        def work():
            return recommendations(diagnostics.inventory(), diagnostics.fortnite())

        def done(result):
            self.game_report = result
            installed = any(i.get("exists") for i in result.get("installations", []))
            self.game_status = (
                "Fortnite installation detected"
                if installed
                else "No supported installation detected"
            )

        return self.submit("Inspecting Fortnite and hardware", work, done)

    def inventory(self, callback=None):
        def done(result):
            self.inventory_report = result
            if callback:
                callback(result)

        return self.submit(
            "Reading startup and task inventory",
            lambda: classify_inventory(diagnostics.startup()),
            done,
        )

    def gaming_settings(self, callback):
        return self.submit(
            "Inspecting guided gaming settings", diagnostics.gaming_settings, callback
        )

    def probe(self, host):
        def done(result):
            self.network_result = result

        return self.submit(
            "Measuring ICMP response latency and jitter",
            lambda: diagnostics.network(host),
            done,
        )

    def restore_point(self):
        return self.submit(
            "Requesting a Windows restore point",
            lambda: powershell(
                "Checkpoint-Computer -Description 'ApexxTweaks user-requested checkpoint' -RestorePointType MODIFY_SETTINGS"
            ),
            lambda _: self.notice.emit(
                "Windows checkpoint command completed. Check System Protection for availability."
            ),
        )

    def import_run(self, path, condition, context):
        context = context.strip()
        if not context:
            self.error.emit("Enter an experiment context before importing.")
            return False

        def done(result):
            if any(
                r.get("source_sha256") == result["source_sha256"]
                for runs in self.runs.values()
                for r in runs
            ):
                raise ValueError(
                    "This exact capture is already imported. Reimporting it is not an independent repeat run."
                )
            result.update(
                context=context,
                source=Path(path).name,
                changes=[
                    r["action"] for r in self.engine.records if r["status"] == "applied"
                ],
            )
            updated = copy.deepcopy(self.runs)
            updated[condition].append(result)
            atomic_json(self.data / "benchmarks.json", updated)
            self.runs = updated
            self.last_import = result["source_sha256"]
            self.notice.emit(
                f"Imported {condition.lower()} capture: {result['source']}"
            )

        return self.submit(
            "Analyzing frame-time capture", lambda: benchmark.load_csv(path), done
        )

    def compare(self, callback):
        return self.submit(
            "Comparing independent benchmark runs",
            lambda: benchmark.advanced_compare(self.runs["Before"], self.runs["After"]),
            callback,
        )

    def new_experiment(self):
        if self.busy:
            return False
        atomic_json(self.data / f"benchmarks-archive-{time.time_ns()}.json", self.runs)
        empty = {"Before": [], "After": []}
        atomic_json(self.data / "benchmarks.json", empty)
        self.runs = empty
        self.last_import = None
        self.changed.emit()
        return True

    def export(self, path):
        atomic_json(
            Path(path),
            {
                "runs": self.runs,
                "history": self.records,
                "telemetry": self.last_telemetry,
            },
        )

    def owned(self, action_id=None):
        return [
            (i, r)
            for i, r in enumerate(self.records)
            if r["status"] != "restored"
            and (action_id is None or r["action"] == action_id)
        ]

    def shutdown(self):
        if self.busy or self.session.active:
            return False
        self.closed = True
        self.pool.waitForDone()
        return True


def measurements(hardware, sample):
    """Truthful presentation values; no invented GPU aggregate or temperatures."""

    def numeric(value):
        try:
            n = float(value)
            return n if math.isfinite(n) else None
        except (TypeError, ValueError):
            return None

    cores = [numeric(c.get("PercentProcessorTime")) for c in rows(sample.get("cpu"))]
    cores = [v for v in cores if v is not None]
    cpu = sum(cores) / len(cores) if cores else None
    total = numeric((hardware.get("memory") or {}).get("totalMB"))
    available = next(
        (
            numeric(m.get("AvailableMBytes"))
            for m in rows(sample.get("memory"))
            if m.get("AvailableMBytes") is not None
        ),
        None,
    )
    if available is None and not sample:
        available = numeric((hardware.get("memory") or {}).get("freeMB"))
    used = (
        total - available
        if total is not None and available is not None and 0 <= available <= total
        else None
    )
    engines = [numeric(e.get("UtilizationPercentage")) for e in rows(sample.get("gpu"))]
    engines = [v for v in engines if v is not None]
    return {
        "cpu": cpu,
        "gpu_engine": max(engines) if engines else None,
        "total_mb": total,
        "used_mb": used,
        "available_mb": available,
        "ram_percent": 100 * used / total if used is not None and total else None,
    }
