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
