# Action selection and Gaming Mode

## Optional applications

Choose **Optimization → Discover optional apps**. Discovery is read-only. Only direct Spotify/Discord targets with a valid expected publisher signature can produce actions. Unknown, unsigned, updater-dispatched, system, security, launcher and game entries remain read-only. The discovery report explains rejections; no “unnecessary” label is inferred from a name.

- **Startup:** exact REG_SZ values in the current user's standard Run key only. Removing an entry prevents a future sign-in launch; it does not reduce CPU of an instance already running. Only direct absolute executable commands and approved minimized-launch arguments qualify. Applications can recreate entries during updates; external changes block automatic undo.
- **Background:** EcoQoS applies only to the selected PID/creation-time/full-image/current-user instance. It changes the documented execution-speed QoS bit and preserves all other flags. Hardware and Windows determine the effect. This is an energy/scheduling hint, not CPU limiting. Voice/music can stutter, so select these only when acceptable and compare measured frame times. No new instances or children are automatically changed.
- **Tasks:** only user-opted-in tasks under `\ApexxTweaksOptional\`. Existing third-party tasks outside this namespace are analyzed/read-only, not automatically disabled. Tasks must be non-elevated, current-user direct optional-app launches; scripts, COM handlers, shell hosts and updater arguments are rejected. Disabling prevents future triggers, never stops a running task.

To create a deliberately optional Spotify logon task, use Task Scheduler: create folder `ApexxTweaksOptional`, create a task running only when your own user is logged on, leave **Run with highest privileges** unchecked, add a logon trigger and a single **Start a program** action pointing directly to your installed signed `Spotify.exe`, optionally with `--minimized`. Do not copy update/security tasks into this folder. Disable duplicate startup through the app's own settings if you choose this launch method. ApexxTweaks does not register or move existing tasks for you.

Use Optimization search/category filters, applied-only filtering and sorting. **Inspect compatibility** performs OS reads before enabling Apply. Each card has Details, current status and an individual Apply or Restore action. Gaming Mode uses separate per-card session checkboxes; the mode switch shows a risk summary before starting. Restore Center can inspect conflicts, restore individually or restore all owned changes. A journal record by itself is not a verified active state.

## Supported Windows gaming settings

Game Mode, Windows 11 Captures, per-app GPU choice, HAGS and display settings use supported Settings pages. Registry status is not proof that the game is benefiting. In Optimization, **Inspect settings status** reads the documented Game Mode preference location; absence is unknown/default. This version deliberately does not automate unsupported write paths. Manually changed settings are outside the action journal.

The Windows 10 recording-policy action uses the documented machine policy only on supported desktop editions. It disables Windows game recording/broadcasting for all users, not just Fortnite. It requires administrator rights and excludes domain/enrollment-managed systems. Configuration read-back does not demonstrate that an already-running recorder stopped: restart the game/sign out and inspect Captures. Windows 11 users use the Captures page instead.

Prefer testing AC power mode on Windows 11 with Balanced base plan. The classic High performance scheme is a separate experiment. ApexxTweaks refuses overlapping ownership of these methods, does not edit processor boost/core policies and never changes battery mode. Thermal/system signals can override the effective mode even when the API reports the requested user mode.

## Temporary Gaming Mode

Select approved Power, Background or Task actions, then **Gaming Mode → choose actions → mode switch ON**. Review the risks. Startup entries, recording policy and Fax are persistent-only and excluded. Already-desired states are not acquired by the session. Other persistent changes are never restored by a session.

An application error during start triggers reverse-order rollback of session-owned records, including pending writes. If rollback conflicts or fails, the session remains recoverable and the error is shown. Optional automatic restoration observes only public Fortnite executable names and waits for two absent polls after a detected run. It never accesses game handles/memory. A failed watcher explicitly disarms; end Gaming Mode manually. If Fortnite never starts, restoration waits for you to end the session or close the app.

Normal close restores the session first. Forced exit, system crash or power loss leaves pending/applied records in the write-ahead journal. Next launch flags recovery: open History and Restore. Restoring an exited optional process makes no write to its replacement PID. A changed signature, changed task definition, missing power plan or outside configuration change requires manual investigation with the original snapshot.

## Experiments

Use one context for a matched scene/hardware/driver/rendering-mode/resolution/cap configuration. Import separate captures; repeated import or renaming one file is not a new measurement. Changes are recorded from journal state, not inferred from manual settings. External settings and temperatures still need your own notes. **New experiment** archives current results, clears only Before/After data and preserves optimization backups/history. JSON exports can include local paths, usernames and telemetry; review before sharing.

Sustained sampling is opt-in and bounded; its CIM overhead may affect low-end systems. Use identical sampling in both conditions, or keep sampling separate from final FPS captures. Reports do not timestamp-align GPU or disk counters with imported frame times. Background CPU includes non-game system activity; only approved discovered apps are actionable. No recommendation authorizes terminating an unknown busy process.
