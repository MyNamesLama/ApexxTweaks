# Technical rationale, v0.2

Only narrow controls with a defensible mechanism are offered. No benefit is presumed until repeated matched runs demonstrate it. Registry/API read-back verifies configuration, not effective rendering behavior. Regressions are possible.

| Family | Implementation and requirements | Plausible effect and risks | Saved state / verification |
|---|---|---|---|
| `power.high` | Existing built-in plan via `powercfg /setactive`; AC rechecked before apply | May change ramp behavior; heat/battery/thermal regression risk | Active GUID and exported plan; read active scheme |
| `power.ac-performance` | PowerGet/SetUserConfiguredACPowerMode, exported API, Windows 11, AC, Balanced base scheme | User power-mode preference may affect scheduling/energy policy; system signals can override it | Original supported GUID; API read-back |
| `capture.policy-off` | Documented AllowGameDVR DWORD at HKLM Software\Policies\Microsoft\Windows\GameDVR; Windows 10 desktop Pro+ only; excludes domain/enrollment management | Removes game-recording capability and its overhead if active; disables clips for all users, restart/sign-out may be needed | Original DWORD/absence; typed value read-back |
| `startup.*` | Delete exact approved current-user Run REG_SZ | Avoid future optional-app startup overhead. No effect on already running app; updates can recreate entry | Exact command/type/absence; signature and command checks; restore refuses changed entry |
| `task.*` | Disable a validated optional app-launch task in `\FrameWiseOptional\` only | Avoid automatic app launches during gaming; launch automation unavailable temporarily | Enabled flag, canonical definition fingerprint, XML backup; refuse definition changes |
| `eco.*` | Get/SetProcessInformation ProcessPowerThrottling execution-speed bit, Windows 11; signed Spotify/Discord, matching PID/creation time/path and current-user SID | Background energy/scheduling hint; not a cap or guaranteed lower CPU usage. May slow/stutter music or voice | Original ControlMask/StateMask; preserve other bits; read-back; vanished process is restored-by-lifetime without a PID write |
| `service.fax` | Set-Service Fax startup only; stopped, dependency-free and not delayed-auto | Normally no measurable FPS benefit; fax unavailable | Exact startup mode; service read-back |

Profiles select candidates; they do not establish suitability or authorize writes. Balanced selects none. Competitive proposes the modern AC-mode experiment. Optional app actions remain individually opt-in. There are no fixed “performance scores.”

## Why some settings remain guided

Microsoft's settings portability documentation identifies a Game Mode status registry location but does not establish a public setter contract. FrameWise reads it and opens the supported Settings UI. Windows 11 background capture APIs have provisioning restrictions; the Windows 10 GameDVR policy explicitly documents a desktop Windows 10 applicability limitation. It is not blindly applied to Windows 11. GPU preference and windowed optimizations are also managed through Windows Settings rather than undocumented registry writes.

Per-process EcoQoS is a supported engineering experiment, not a latency guarantee. It may direct efficiency scheduling and reduce energy spent on competing optional work; it can also prolong that work or degrade playback. Exact flags are read before any write. If GetProcessInformation or SetProcessInformation rejects the feature, the operation fails with a recoverable journal record rather than assuming success. No timer-resolution or process-priority flags are changed. Signed identity and user ownership are revalidated before writes; no protected game process is opened.

Task disablement is useful only for explicitly selected launch automation. Arbitrary third-party task names are not evidence of dispensability, so unknown/updater/security tasks remain read-only. Namespace opt-in plus principal/action/signature checks limits the authority of this feature.

Sustained screening requires ≥3 samples, ≥80% game-GPU coverage and ≥70% saturation for a GPU candidate; CPU thresholds are evaluated per logical processor. GPU load is attributed through public engine counter PID labels, not total engine load from other apps. These thresholds prioritize investigation and do not establish a game-thread bottleneck. No GPU utilization summation across unrelated engines, thermals, VRAM inference or causal disk attribution is performed.

## Primary sources

- [Microsoft: powercfg](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options): scheme switching/export.
- [PowerGetUserConfiguredACPowerMode](https://learn.microsoft.com/en-us/windows/win32/api/powrprof/nf-powrprof-powergetuserconfiguredacpowermode) and [PowerSetUserConfiguredACPowerMode](https://learn.microsoft.com/en-us/windows/win32/api/powrprof/nf-powrprof-powersetuserconfiguredacpowermode): documented power-mode APIs, requirements and effective-mode caveat.
- [ApplicationManagement / AllowGameDVR](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationmanagement#allowgamedvr): supported values, policy mapping and Windows 10 desktop limitation.
- [Windows 11 settings reference](https://learn.microsoft.com/en-us/windows/apps/develop/settings/settings-windows-11): Game Mode status location. Read access documentation is not treated as a public setter.
- [AppCaptureSettings](https://learn.microsoft.com/en-us/uwp/api/windows.media.capture.appcapturesettings): restricted API provisioning; not used for unprovisioned automatic writes.
- [Run and RunOnce keys](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys): standard logon launch mechanism. Only Run is changed; RunOnce and StartupApproved are untouched.
- [Disable-ScheduledTask](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/disable-scheduledtask) and [Export-ScheduledTask](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/export-scheduledtask): task state/export controls.
- [GetProcessInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessinformation), [PROCESS_POWER_THROTTLING_STATE](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_power_throttling_state) and [Windows Quality of Service](https://learn.microsoft.com/en-us/windows/win32/procthread/quality-of-service): supported per-process power policies. No registry-wide throttling override is used.
- [Graphics preferences/windowed games](https://support.microsoft.com/en-us/windows/hardware/display-graphics/optimizations-for-windowed-games-in-windows-11): supported user workflow and presentation applicability.
- [Microsoft performance counter classes](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/performance-counter-classes): formatted CIM counters; availability varies.
- [Epic: improve low FPS](https://www.epicgames.com/help/c-34254770/c-38015632/pc-fps-a25544495) and [Performance mode](https://www.epicgames.com/help/c-32735058/a20197720?lang=en-US): supported game-side options, changed through the game UI.
- [NVIDIA Fortnite Reflex](https://www.nvidia.com/en-us/geforce/news/fortnite-rtx-on-ray-tracing-nvidia-dlss-reflex/): official integration. Historical vendor measurements are not FrameWise measurements.
- [Set-Service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-service?view=powershell-5.1): Fax startup configuration, not evidence of gaming gains.

Reviewed during development. Do not infer compatibility certification or current-game FPS improvements from the existence of these APIs. HPET, timer hacks, forced cache clearing, security reductions, broad service disabling, TCP tweaks, affinity/priority changes and injected latency tools remain excluded.
