# Architecture, ApexxTweaks 2.0

The v0.1 separation is preserved and extended:

- `actions.py`: immutable metadata, categories, evidence, hardware/permission requirements and session eligibility. Static catalogue plus validated per-target optional actions. `desired` supports typed JSON states.
- `targets.py`: canonical JSON descriptors, stable IDs, strict optional-app command and publisher policy, read-only inventory classification. No arbitrary commands or executable enrollment.
- `platform.py`: Windows version gate, command execution, backend routing, hardware preflight, mocks. PowerShell scripts use UTF-16LE encoded commands and explicit UTF-8 output. No shell execution. Commands have timeouts; failures remain visible.
- `windows_controls.py`: typed registry handling, modern AC power APIs, Windows 10 capture policy, task XML validation/fingerprinting and narrowly scoped Win32 process QoS. Windows DLLs load only inside Windows operations. Optional-process handles have query rights and, only for apply/restore, set-information rights; no VM/memory/debug/injection access. Signature, image, creation time and user-token SID are checked.
- `discovery.py`: current-user Run candidates, allowlisted optional processes, opt-in task discovery; rejected items remain read-only with explanations. Public process metadata is sufficient; no game handles are opened.
- `engine.py`: original-value backup, write-ahead journal, read-back verification, recovery, reverse restoration and external-change checks. Action aliases on one target and competing power methods cannot overlap. Original state is checked again after backup. The journal stores each action description and session owner; older records remain readable. Restoration uses stored targets/snapshots even when the app has not rediscovered an optional action.
- `session.py`: session-owned transactions; already-desired settings are never owned. Start failure restores only this session's pending/applied records. Failure/conflict during restore preserves recovery state. Two absent observations after a detected game tolerate a brief restart. Watcher failure disarms automation explicitly.
- `diagnostics.py`, `telemetry.py`, `analysis.py`: read-only inventories, bounded repeated collection and qualified screening. No background autonomous optimization and no continuous sampling by default.
- `fortnite.py`: hardware-specific supported UI guidance; no file writes or protected-process interaction.
- `benchmark.py`: offline frame-time validation/statistics, independent-run bootstrap intervals, context validation. No capture providers or injected measurements.
- `gui.py`: stable Qt application entry point, Windows single-instance mutex and startup smoke path. Internal package/entry points stay compatible.
- `ui/controller.py`: serialized QThreadPool adapter over the engine/session, main-thread result/error signals, typed presentation state, benchmark import/export and separate UI preferences. It does not reimplement system writes.
- `ui/window.py`: collapsible/scrollable navigation, finite transitions, progress/feedback, timer lifecycle, responsive resize and safe close/session restoration.
- `ui/pages/`: seven focused pages and connected controls; details are on demand, compatibility gates automatic Apply, guided Windows Settings remain outside the journal.
- `ui/widgets.py`, `icons.py`, `theme.py`, `assets/theme.qss`: reusable cards/switches/wrapping command rows, original stroke icons, antialiased plots and the design system. No browser/QML/QtCharts runtime. See [UI architecture](UI_2.md).

## Failure model

Atomic JSON uses flush/fsync/replace. Journal states are pending → applied or recovery_required → restored. A timeout after OS mutation can leave an applied setting with a pending/recovery record; the app does not assume failure means unchanged. Backups must succeed before writes. Original-value conflicts are preserved. If an EcoQoS target exited or PID was reused, restore records a lifetime-based completion and never opens a replacement process for writing.

Task definitions are not recreated or overwritten; only the enabled flag is restored after the rest of the definition matches the snapshot fingerprint. Application uninstallation/signature changes, deleted tasks/plans, external setting changes and newly imposed policy can block automatic restore; snapshots support manual recovery.

AC preflight is repeated before applying, but restoration does not require AC: it restores original settings on battery too. Management checks constrain recording policy; user-token/signature/principal checks constrain optional targets. OS configuration can race another administrator between validation and mutation; the application cannot provide system-wide transactional exclusion. Do not manage the same settings simultaneously from multiple tools/accounts/sessions.

Snapshots, XML backups, logs and exports are local, user-writable diagnostic artifacts, not tamper-resistant audit stores. Preserve them until all changes are restored; corruption must be investigated before new writes. No journal auto-migration deletes old data.

## Product rename compatibility

`branding.py` centralizes ApexxTweaks product identity and the minimum legacy compatibility identifiers. Fresh data uses the new name; populated legacy data is reused in place to preserve absolute snapshot references. Two populated stores are refused instead of silently merged. Both approved optional-task namespaces remain accepted; target IDs/fingerprints are never rewritten. The Windows mutex stays shared with previous versions. Human-readable saved action metadata is rebranded at presentation time; raw history and backup paths remain accurate. See [upgrade instructions](UPGRADING.md).

The benchmark analyzer adds bounded bucket-peak trace metadata without changing FPS/lows/p99 calculations. Older results remain readable. `ui-preferences.json` is separate from legacy settings files. GUI-local selection/state is distinct from a verified backend state; journal presence alone is not proof that a setting remains applied.
