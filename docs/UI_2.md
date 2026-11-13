# ApexxTweaks 2.0 interface

The frontend was replaced with PySide6 Essentials 6.8.3 / Qt Widgets. The Windows optimization engine, definitions, native controls, discovery, journal, restoration and GamingSession remain the same modules. This is a presentation rewrite, not a different set of undocumented tweaks.

## Navigation and design

Seven sidebar destinations: Dashboard, Optimization, Gaming Mode, System Monitor, Benchmarks, Restore Center and Settings. The sidebar collapses to icons with tooltips. Ctrl+1 through Ctrl+7 opens the corresponding page; Tab/Shift+Tab navigates controls, Space operates checkboxes/switches and Enter activates buttons. Controls use accessible names, native focus and selection behavior. Qt handles logical pixel scaling; actual Windows DPI/screen-reader validation is still pending.

`ui/assets/theme.qss` defines near-black/charcoal surfaces, restrained rounded cards and lime highlights. Original vector stroke icons render through QtSvg without third-party icon/font downloads. Charts are antialiased QPainter widgets. No plotting daemon, embedded browser, GPU-intensive shader, QtCharts module or always-running animation exists. Page/sidebar transitions are finite; Reduce motion disables them. Action rows wrap at narrow widths, pages scroll vertically, and detailed reports are on-demand dialogs rather than wall-of-JSON dashboards.

## Truthful state and action controls

Fresh dashboards show Not inspected/Unavailable until the user collects data. CPU usage is the mean of available logical-processor counters. GPU chart/card values are explicitly the **maximum reported 3D engine**: they are not aggregate physical-GPU utilization. Memory used is derived only from valid total/available readings. Temperatures are Unavailable because the backend has no validated temperature provider. Unknown measurements never become zero on a chart.

Compatibility must be inspected before applying a change. Unavailable actions show disabled Apply controls with reasons in their tooltip/Details; configured states show Already configured. Restore remains journal-owned and conflict-aware. GUI metadata cannot override backend checks; backend preflight/read-back still occurs at mutation time. Power methods that conflict with an owned experiment are not offered as ready. Category names map only to supported action families; Network Diagnostics contains a read-only ICMP probe, not network tweaks. Guided Windows Settings are visually and behaviorally separate from automatic actions and outside the journal.

Gaming Mode has its own explicit checkboxes and profile suggestions; selecting a profile never applies changes. The mode switch confirms risk before calling the existing session manager. End session restores only owned changes. The watcher disarms after an error without assuming the game exited. Normal close waits for current work, then restores an active session before closing. Restore All also ends a successfully restored active session. Failure or conflict leaves recoverable records intact.

Restore Center displays original values, timestamps, status and a full raw journal/backup view. The original paths are never rebranded or rewritten. Include restored history reveals previous completed operations. Check for conflicts is read-only. An unavailable/conflicted result disables a misleading Restore button until reinspection; the backend also checks before writing.

## Threads, monitoring and files

`ui/controller.py` is a QObject adapter with one QThreadPool worker. Qt result signals update widgets on the GUI thread. Windows/PowerShell diagnostics and mutations never run in button handlers. Concurrent submissions are refused instead of racing journals. Navigation is usable during work; closing is refused while a worker operates. Commands retain backend timeouts and are never force-killed during a mutation.

No recurring UI timer runs at idle. Live monitoring is opt-in, 3–15 seconds, and active only while System Monitor is visible and the window is not minimized. It pauses away from that page; samples do not queue behind a busy operation. Sustained diagnostics remain bounded and user-requested. Fortnite exit polling is independently opt-in and requires an active session. Charts repaint on data/resize, not continuously. Windows monitoring overhead still needs measurement on target machines.

Preferences live in `ui-preferences.json`: reduce motion, start minimized, sidebar collapse, startup page and interval. Unknown preference keys are preserved. No tray or update switch is presented because neither feature exists. Safety/error logs remain mandatory; users can view/export them. Existing `preferences.json`, benchmarks, snapshots and journal files are not replaced. Legacy folder and mutex handling is unchanged; see [Upgrading](UPGRADING.md).

Benchmark results preserve existing calculations and CSV validation. New captures add ≤300 maximum-of-bucket trace points; the chart labels its bucket size and does not claim a raw trace. Before/after charts and tables compare the independent-run metrics and exploratory bootstrap intervals. Empty captures, old captures without trace metadata and insufficient/mismatched contexts have explicit states. Archiving does not delete optimization backups.

## Actual Linux previews

Screenshots below are Qt offscreen renders of the real application with uninspected hardware. They are not Windows tests or measured gaming data.

- [Dashboard](screenshots/dashboard.png)
- [Optimization](screenshots/optimization.png) · [compact](screenshots/optimization-compact.png)
- [Gaming Mode](screenshots/gaming-mode.png)
- [System Monitor](screenshots/system-monitor.png)
- [Benchmarks](screenshots/benchmarks.png)
- [Restore Center](screenshots/restore-center.png)
- [Settings](screenshots/settings.png)
- [Collapsed sidebar](screenshots/sidebar-collapsed.png)

Screenshots were inspected during development. Compact 920×540 and default 1260×870 layouts are exercised in GUI tests; Windows display scaling, desktop window-manager behavior and assistive technology remain manual release checks.

Persistent multi-selection remains available under Optimization → Select multiple → Review selection. Selections remain explicit across search filters; confirmations list all selected actions. Persistent batches retain per-action failure semantics and recoverable earlier successes. The UI refuses conflicting power methods before starting a batch.

Reproduce the uninspected preview images using `.venv/bin/python scripts/capture-ui.py` after installing the project. It uses isolated temporary app data and does not run native diagnostics or apply settings. On the development host the normal Linux Wayland startup smoke test also passed; offscreen tests alone are not being presented as window-manager validation.

The compact Windows layout correction replaces fixed metric columns with automatic card stacking and all critical fixed control rows with height-for-width reflow. Text/buttons wrap rather than clip, including long hardware identifiers and paths. No larger minimum window is required. See [responsive layout details](RESPONSIVE_LAYOUT.md) for root cause and regression coverage.
