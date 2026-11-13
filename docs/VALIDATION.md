# Validation and release gates

Linux: dependency-free core tests cover journal ordering, backup failure, successful/failed verification, failures before and after mutation, interrupted-write recovery, repeat actions, external conflict preservation, baseline ownership, statistics, CSV validation and command-input rejection. They exercise mocks, not Windows system modifications.

Windows CI: core tests, non-mutating Tk construction smoke test, PyInstaller package and artifact checksum. Hosted Windows does not substitute for Windows 10/11 gaming hardware and EAC tests. The workflow has not been remotely executed from this unconnected workspace.

Before distributing as a stable release:

- Run read-only inventory on Windows 10 build 19041+ and current Windows 11 with NVIDIA, AMD and Intel devices, multi-GPU and localized installations. Confirm partial-provider behavior and performance-counter permissions.
- In disposable Windows VMs, explicitly test apply/read-back/undo of both actions, non-admin denials, Fax absent/running/dependent/delayed-auto, policy-restricted schemes, battery refusal and unavailable High performance plan.
- Interrupt after write-ahead save and after OS mutation; reopen, inspect history and restore. Validate full disk, journal corruption, outside configuration changes and deleted original power scheme handling.
- Verify System Protection disabled/enabled/admin/rate limits; command completion is not a guarantee that Windows created a new checkpoint.
- Exercise temporary sessions: game never starts, multiple executable names, observed game exits, watcher errors, close during diagnostics, abrupt app exit and recovery. No anti-cheat or game internals should be accessed.
- Run three or more identical warm captures per condition; log driver, hardware, cap, display, temperatures, power and game options. Verify capture semantics, single swapchain, frame generation status and repeatability. Check average and lows. Record regressions as well as improvements.
- Test packaged executable on a clean Windows account without Python. Check GUI scaling, long text, error dialogs, all buttons, Windows Settings URIs, artifact hash and app-data permissions.
- Validate publisher policy and real Fortnite/EAC compatibility without injection or protected-process access. No universal compatibility certification is inferred from architecture.

Unimplemented features are listed explicitly in README; there is no claim that this first release fulfills advanced continuous telemetry or hardware-lab validation.

## Results from this workspace

- 2026-11-13: 22 unit tests passed with managed CPython 3.13.18 on Bazzite Linux. Earlier 19-test core suite also passed with system Python 3.15.2.
- Tk GUI launched with managed Python 3.13; all six pages constructed, event loop processed, and frame-time histogram rendered 21 canvas objects. This validates construction and basic drawing, not visual quality on Windows or every interaction.
- Source compiled successfully with `compileall`.
- Host Python lacked Tk; a managed Python runtime was installed in user space using uv. No host RPM changes were made.
- Windows backend mutations, GitHub Actions execution, packaged EXE, EAC behavior and performance improvements: not tested in this workspace. No Windows executable was produced locally.

## v0.2 validation

The current suite discovers **68 tests**. With managed CPython 3.13/Tk on Bazzite, **65 pass and 3 native Windows tests skip**. With the host Python lacking Tk, GUI tests also skip explicitly. Source compiles and `launcher.py --smoke-test` succeeds on Linux with the managed runtime.

Added coverage includes all built-in and optional action round trips with mocks; original typed values/absence; recovery without rediscovery; external target conflicts; conflicting power methods; stale state after backup; process lifetime/PID reuse; session ownership, partial-failure rollback and watcher exit policy; task principal/action/namespace/signature constraints; command ambiguity; matched experiment contexts; independent-run statistics; sustained GPU attribution/coverage; searchable GUI filters, individual toggles, charts and mock-backed active-state display.

Three native Windows tests are configured for CI, **not run locally**: disposable HKCU Unicode/DWORD/absence round trips; Get/SetProcessInformation QoS round trip on the test runner's own process with test-only policy mocks; and creation-time mismatch refusal. They do not touch real app/game processes, services, tasks, power or recording policy. An explicitly test-only publisher-policy extension allows the Python test runner; production allowlists are unchanged.

The Windows workflow now smoke-tests the actual packaged executable and bundled Tcl/Tk using `--smoke-test` with a timeout, before uploading ZIP/SHA256. Neither this workflow nor a Windows build has executed from this workspace.

Additional hardware/Windows release gates:

- Confirm PowerGet/SetUserConfiguredACPowerMode exports on supported Windows 11 releases, AC/Balanced requirements, legacy-plan conflicts, policy denial and exact-mode restoration including battery transitions. Verify effective vs requested modes separately.
- Exercise Windows 10 recording policy on clean supported editions, unsupported Home, domain/enrollment-managed devices and existing policy values/absence. Confirm clips stop after required restart/sign-out and restore exactly. Do not infer effective recording shutdown from registry read-back.
- Validate actual Spotify/Discord certificate subjects, current-user process identity, PID exits/reuse, inaccessible processes, updates/uninstallation and child processes. Confirm only bit 0 changes and all initial flags restore. Measure potential music/voice regressions as well as gaming behavior.
- Exercise opt-in tasks on real Task Scheduler: optional namespace, same-user interactive principal, direct approved action, disabled/pre-enabled states, edited XML, removed tasks and concurrent runs. Verify canonical fingerprints survive only enabled-state changes; never recreate definitions automatically.
- Exercise current-user Run values, Unicode commands, quoted spaces, unsupported updater launchers and outside changes. Confirm undo restores startup only; it does not relaunch or terminate apps.
- Test session start failures after each action and after mutation, rollback conflicts, watcher errors/disarming, brief Fortnite restarts, game never starting, normal close and forced exits. Confirm other persistent actions remain owned/restored independently.
- Sample on NVIDIA/AMD/Intel/multi-GPU hardware, provider absence and truncated process-counter names. GPU coverage must be unknown when attribution is missing, never assumed idle. Assess monitoring overhead with identical A/B conditions.
- Use ≥3 genuine independent captures per condition, same context/route/warm-up/cap/driver. Validate graph units/scales, duplicate rejection, archive retention and low-FPS regressions. Bootstrap intervals remain exploratory with small n.

No real-game, anti-cheat, thermal, input-latency or FPS improvement validation has occurred on Windows here.

Final regression additions verify that unresolved optional definitions reload for individual undo, query-only identity validation precedes write-capable handle acquisition, write handles are revalidated while the query handle stays alive, missing memory data remains unknown, and explicit CIM game PIDs support truncated process-counter names.

## ApexxTweaks rename validation

The renamed application discovers **85 tests: 82 passed and 3 native Windows tests skipped**, using managed CPython 3.13 with Tk on Bazzite. The source GUI smoke test (`python launcher.py --smoke-test`) also passed. Both build/smoke PowerShell scripts parsed successfully; workflow YAML, PyInstaller spec syntax, exact metadata/entry-point capitalization, renamed artifact/ZIP paths and build/smoke path references were checked. `git diff --check` passed.

Rename-specific tests cover fresh product-named data, in-place legacy data and settings retention, original snapshot bytes and absolute paths, successful legacy journal undo, legacy task action identities, validation of both exact optional-task namespaces, the shared cross-version mutex, ambiguous-store refusal, old/new empty-directory cases, metadata refresh without journal rewriting, GUI titles/headings, legacy benchmark loading and rebranded saved action descriptions.

New build names: `ApexxTweaks.exe`, `dist/ApexxTweaks/`, `ApexxTweaks-windows-x64.zip`, `ApexxTweaks-windows-x64` application artifact and `ApexxTweaks-windows-build-diagnostics` diagnostics artifact. The source package remains `tweaker`. Compatibility identifiers and historical audit paths are intentionally preserved; see [upgrade instructions](UPGRADING.md).

The renamed Windows executable and GitHub Actions workflow have **not been executed on Windows during this rename**. Linux tests and syntax checks do not establish Windows startup or functionality. The workflow retains the extracted-ZIP smoke test with isolated app data and Python removed from PATH; successful Windows results must be inspected before claiming the renamed executable works.

## ApexxTweaks 2.0 frontend rework

The Tk frontend was replaced with PySide6 Essentials / Qt Widgets while preserving the Windows engine, action definitions, typed snapshots, legacy folder/task/mutex compatibility and session rollback. Benchmark calculations are unchanged; new captures add bounded bucket-peak trace metadata.

Actual checks completed on Bazzite Linux with CPython 3.13:

- **113 tests discovered: 110 passed, 3 native Windows tests skipped.** The complete suite passed at normal Qt scaling and with `QT_SCALE_FACTOR=2` offscreen. Existing non-GUI tests remain intact; the GUI tests were migrated to the actual new widgets and extended.
- GUI integration coverage includes navigation, compact 920×540 layouts, collapsed/dark sidebar, meaningful empty states, search/category/applied filters, actual Apply/Restore button connections and confirmation, compatibility gating, persistent selections/batches, session ownership and close restoration, conflicts, watcher failure disarming, monitor pause/error behavior, Qt main-thread callbacks, responsive navigation during work, typed legacy journals/benchmarks, UI preference persistence/failure handling, keyboard slider persistence, exports/archives, duplicate imports, newest-run selection, real derived comparisons and preserved trace spikes.
- `python launcher.py --smoke-test` passed with the actual Linux **Wayland** platform as well as offscreen rendering. This visits all seven pages and exercises plots without Windows diagnostics or mutations.
- PyInstaller 6.16.0 built a **Linux-only frozen executable using the checked-in Qt spec**. Its seven-page smoke test passed with `PATH=/nonexistent`, PYTHONHOME/PYTHONPATH cleared and isolated app data. Packaged QSS was present. This verifies Linux frozen Qt imports/assets; it is not a Windows build or compatibility test.
- PyInstaller spec, metadata/package data, workflow YAML/x64/artifact paths and both PowerShell scripts were validated locally; `compileall`, new-frontend undefined/unused-import checks and `git diff --check` passed.
- Real uninspected UI screenshots were captured at default and compact sizes and inspected. Inspection caught and corrected a light sidebar viewport regression, narrow command-row wrapping, disabled-action styling and header/footer layout. A regression test verifies the sidebar stays dark. Reproduce with `python scripts/capture-ui.py` in the installed project environment. No Windows hardware values or benchmark improvements were invented for these images.
- One short, two-second Linux offscreen idle sanity check measured approximately **98.6 MiB RSS and 0.15% of one CPU core**, with both polling timers stopped. This is a single local observation, not a Windows footprint guarantee or gaming performance claim.

**Not executed here:** the redesigned Windows Actions build, packaged Windows startup, native Windows mutation tests, Windows 10/11 hardware diagnostics/game behavior, EAC compatibility, Windows DPI/window-manager/screen-reader validation, or before/after FPS/input-latency measurements. The workflow retains x64 PyInstaller packaging, required Qt DLL/platform-plugin/theme checks, ZIP/checksum output and extracted-archive smoke testing without Python on PATH. A successful hosted Windows Server smoke run would still need Windows desktop validation.

Manual Windows release gates now additionally include Qt qwindows/plugin startup on clean Windows 10/11 accounts, 100/125/150/200% scaling and multi-monitor moves, keyboard/screen-reader focus, start-minimized/taskbar behavior, worker failure/close handling, visible live-monitor pausing, and full original engine/session/restore tests on disposable Windows systems. Never substitute Linux GUI tests for those checks.

## Compact layout failure correction

The original compact-navigation test was retained, with no increase to the 920×480 application minimum. Rigid grids/rows were replaced with content/font-aware reflow, genuine height-for-width text and wrapping command/navigation controls. See [root cause and implementation](RESPONSIVE_LAYOUT.md).

Local Bazzite/CPython 3.13 verification: **118 tests discovered, 115 passed and 3 Windows-native tests skipped**. The five additional responsive regression tests also passed in separate processes at Qt scale factors **1, 1.25, 1.5 and 2** (reported DPRs 1.0, 1.25, 1.5 and 2.0). These tests cover all seven pages, larger real font metrics, populated long hardware/path values, actual text height, non-overlapping geometry, sidebar/caption access and full clipboard content. The source Wayland smoke test, workflow YAML checks, PowerShell parsing, static import checks and `compileall` were also exercised locally. Screenshots were regenerated and inspected, including compact and wide layouts and corrected caption contrast.

Windows CI now has an explicit four-scale layout regression step before the unchanged standalone packaging and extracted-ZIP startup checks. **The corrected Windows workflow/executable has not been run on Windows in this workspace**; native Windows/DPI results must come from that next CI run and Windows desktop testing. No claim is made that the reported Windows failure was independently reproduced at exactly 1086 pixels on Linux.

A Linux-only PyInstaller build using the unchanged spec also completed, and its startup smoke test passed with Python removed from PATH and isolated app data. This checks inclusion of the new wrapping-text module and Qt assets on Linux; it does not validate the Windows executable.
