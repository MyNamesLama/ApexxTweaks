# FrameWise 0.2

Windows 10/11 gaming diagnostics and reversible optimization, developed on Bazzite Linux. Native dark Tk desktop UI; no browser runtime, telemetry, resident service or kernel driver. No measured FPS improvement or universal anti-cheat approval is claimed.

## What's new

- **Real optional-app actions:** remove selected current-user logon Run entries, disable opt-in launch tasks, and apply Windows EcoQoS to selected signed Spotify/Discord instances. Everything else remains read-only. No termination, suspension or game-process policy changes.
- **Windows 11 AC power mode:** uses documented PowerGet/SetUserConfiguredACPowerMode, with AC, API and Balanced-plan checks. Classic High performance-plan testing remains available separately. Conflicting power methods cannot overlap.
- **Windows 10 recording policy:** supported GameDVR policy on eligible unmanaged Pro/Enterprise/Education desktop systems, with admin confirmation and exact value/absence restoration. Windows 11 capture control stays in the supported Settings UI.
- **Gaming Mode:** applies only explicitly selected session-safe Power, Background and Task actions. Owns only changes it actually made; rolls back its own changes if startup fails. Optionally restores after Fortnite has been observed and is absent for two consecutive five-second polls. Closing restores; interrupted exits require journal recovery next launch.
- **Sustained diagnostics:** bounded repeated CPU/core, memory, process and GPU-engine samples. GPU candidates require Fortnite PID attribution and sufficient coverage; a single spike is insufficient. Reports background CPU normalized to logical-processor count and distinguishes unavailable telemetry from low utilization.
- **Hardware-specific Fortnite report:** NVIDIA Reflex guidance, AMD/Intel recommendations, multi-GPU selection, RAM/refresh caveats and supported rendering-mode comparisons.
- **Advanced comparisons:** experiment contexts, duplicate-CSV rejection, FPS/lows/p99 comparison graphs and run-level bootstrap intervals. Archives preserve earlier experiments.
- **Searchable action categories:** individual toggles, full requirements/risks, verified active states, per-action undo, profile selection and discovery.

## Actions and scope

| Action family | What changes | When it may help | Restore |
|---|---|---|---|
| High performance plan | Select existing Windows plan on AC | Hardware-dependent ramp behavior; can regress with heat | Original GUID, plus exported plan backup |
| Best performance AC mode | Supported Windows 11 user-configured AC mode | Compatible devices using Balanced base plan; effective mode can be overridden | Exact original mode GUID |
| Recording policy | Windows 10 AllowGameDVR=0 | When Windows game recording was using resources | Original DWORD or absence |
| Optional startup | Remove one exact current-user Run value | Avoid future optional-app launches after sign-in | Exact command/type; refuse changed entry or unsigned replacement |
| Optional task | Disable selected app-launch task under `\FrameWiseOptional\` | Prevent selected launch automation during play | Original enabled state; verify XML fingerprint |
| Optional app EcoQoS | Change execution-speed QoS bit only | Reduce interference/energy from an approved background app on suitable CPUs | Original flags, bound to PID and creation time |
| Fax startup | Disable stopped, dependency-free optional Fax service | Avoid optional startup; normally no measurable FPS benefit | Exact startup mode |

EcoQoS is **not a CPU usage cap** and may slow or stutter voice/music. Only the chosen instances are changed; child/new instances are not automatically enrolled. Signed image, current-user token, full path and creation time are checked; exited/reused PIDs are never written during restore. No browsers, launchers, updaters, games, anti-cheat or security processes qualify. Common Discord updater-based startup commands intentionally remain read-only.

Task changes require explicit opt-in into `\FrameWiseOptional\`, current-user SID, non-elevated principal, a single direct Spotify/Discord launch and approved arguments/signature. This is not permission to disable arbitrary third-party tasks. Update/security/system tasks remain untouched. Running tasks are never stopped. See [task opt-in instructions](docs/USAGE.md).

**Game Mode, Windows 11 recording and GPU preferences:** buttons open supported Windows Settings pages, with state/guidance where available. These remain user-driven and are outside the rollback journal. No undocumented UserGpuPreferences, HAGS or recording registry writes. The documented Game Mode registry location is read for status, not treated as a public write contract.

## Run or build on Windows

Official CPython 3.13 x64 with Tcl/Tk; Windows 10 build 19041+ or Windows 11 desktop, Windows PowerShell 5.1/CIM. Prefer a currently supported Windows release. Optional providers, policy restrictions or unsupported APIs produce errors, not fabricated readings.

```powershell
python -m unittest discover -s tests -v
python -m tweaker
```

Start as a normal user. Explicitly restart elevated only when choosing the Fax or recording-policy action or a restore point; never silently elevate. UI confirmation is required before applying. Domain/enrollment-managed devices are excluded from recording-policy writes; conservative enrollment checks may also refuse some personal devices.

Build/download instructions: [Standalone Windows x64 executable](docs/WINDOWS_BUILD.md).

GitHub Actions builds a complete PyInstaller portable directory, creates **FrameWise-windows-x64.zip**, smoke-tests that exact ZIP without Python on PATH, and uploads it as **FrameWise-windows-x64** only after successful testing. Download it from a successful **Actions → Windows x64 portable build** run, extract the artifact, then extract the inner ZIP and launch **FrameWise/FrameWise.exe**. Keep the entire folder, including `_internal`. **No Python installation is required for end users.**

For local packaging, install CPython 3.13 x64 with Tcl/Tk and PowerShell 7, then run:

```powershell
python -m pip install -r requirements-build.txt .
pwsh -File scripts/build-windows.ps1
pwsh -File scripts/smoke-windows.ps1
```

No installer or signing certificate is included. PyInstaller cannot cross-compile Windows from Linux. This workspace has not executed the Windows Actions workflow: packaged Windows startup and Windows 11 functionality remain unverified. The workflow uses a Windows Server hosted runner; even a passing smoke test still needs Windows 11 desktop validation.

## Bazzite development

The core remains dependency-free:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q tweaker launcher.py
```

GUI requires Tkinter. Use a Fedora distrobox if the host Python omits it:

```bash
distrobox create --name framewise-dev --image registry.fedoraproject.org/fedora:latest
distrobox enter framewise-dev
sudo dnf install python3 python3-tkinter
python3 -m tweaker
```

Run from the repository directory. Alternatively, a `uv` managed CPython with Tcl/Tk supports preview/testing:

```bash
uv run --python 3.13 --no-project python -m unittest discover -s tests -v
uv run --python 3.13 --no-project python -m tweaker
```

Linux previews the interface and analyzes imported captures. Windows mutations are refused. The GUI tests skip when Tk/display is unavailable; native registry/QoS tests skip on Linux.

## Safe workflow

1. Inspect hardware and sustained activity. Review optional startup/task inventories; names alone never prove something is unnecessary.
2. In Optimize, discover approved apps, search/filter, toggle and read each action. Balanced selects nothing. Competitive proposes the Windows 11 AC-mode experiment; optional apps require individual selection. Windows 10 users can select the classic plan manually. Optional restore points are offered in Settings; snapshots are mandatory regardless.
3. Apply one persistent change, or use Gaming → Start approved Gaming Mode for temporary eligible selections. Persistent-only selections are excluded from Gaming Mode and never silently applied.
4. Capture repeated matched external frame-time runs with identical monitoring, route, warm-up, graphics, cap and thermal conditions. No capture tool is installed/launched, and no protected game handles are opened.
5. Import ≥3 independent CSVs per condition under the same experiment context. Compare average, lows, p99, variation and graphs; regressions matter too.
6. Undo a selected action or restore all. Persistent multi-action Apply is per-action, not atomic; Gaming Mode startup has scoped rollback. Conflicts/errors remain in History for recovery. If the watcher fails, it explicitly disarms and leaves restoration to the user.

Backups/logs/history: `%LOCALAPPDATA%\FrameWise`; Linux preview: `~/.local/share/FrameWise`. The 0.1 history format remains readable; new records add action descriptions and session ownership. Preserve snapshot folders and `history.json` until every change is restored. A corrupt journal must be repaired from backups before further writes. App exports can contain usernames, paths, process information and task definitions; review before sharing.

Restore refuses external-setting conflicts. QoS restore of a vanished original process is recorded as restored-by-lifetime. Missing executables/signature failures or changed task definitions can block restore: inspect the stored snapshot and restore manually through the owning application's settings, Task Scheduler or Services. Original plan backup can be imported with `powercfg /import` if needed; inspect the new GUID before activating it. No blanket force mode is exposed.

## Measurement details and remaining limitations

CSV requires `frametime_ms`, `MsBetweenPresents` or `FrameTime`, in milliseconds, ≥1000 finite positive frames, one process/swapchain. Multiple Application/ProcessID/SwapChainAddress streams are rejected. Duplicate file content is rejected by the UI; renaming a capture is not an independent repeat. Context strings are user-supplied, so matching is still the user's responsibility. New experiment archives previous runs. Legacy 0.1 runs without context can be viewed/exported but must be recaptured with context for the advanced comparison.

FPS = 1000/mean frame time. Lows use the mean of the slowest ceil(1%/0.1%) frames; p99 nearest rank. Intervals resample independent **runs**, not individual autocorrelated frames. Exploratory percentile bootstrap intervals can be unreliable with small samples and do not prove causality. Short/mismatched-duration captures generate warnings. Presentation/frame-generation semantics must match; no capture semantics are inferred from a CSV name. No input-latency metric is fabricated.

Still absent: thermal/VRAM instrumentation, causal game-thread profiling, continuous trace correlation, end-to-end input latency, per-process network bandwidth, game packet-loss measurement, SMART detail and automated in-game graphics writes. Read-only counters may be absent. GPU engine maxima are screening signals, not aggregate whole-GPU utilization. No memory cleaners, timer/HPET hacks, TCP registry tweaks, security reductions, priority/affinity changes, process suspension, injection, game-file modification or kernel components.

Windows configuration changes, real-game performance and anti-cheat behavior remain **unverified on Windows in this workspace**. Compatibility is an engineering constraint, not a certification claim. See [rationale](docs/OPTIMIZATIONS.md), [usage](docs/USAGE.md), [architecture](docs/ARCHITECTURE.md) and [validation](docs/VALIDATION.md).
