# Upgrading to ApexxTweaks

ApexxTweaks preserves the existing `tweaker` Python package, action identifiers, journal schema, snapshots, saved benchmark files and restoration logic. The new executable is `ApexxTweaks.exe`; new archives/artifacts use `ApexxTweaks-windows-x64`.

## Existing data stays in place

New installations use `%LOCALAPPDATA%\ApexxTweaks` on Windows or `~/.local/share/ApexxTweaks` for Linux preview. Existing installations with populated data under the former `%LOCALAPPDATA%\FrameWise` (Linux: `~/.local/share/FrameWise`) automatically reuse that directory **in place**. Those legacy names are compatibility paths, not the current product name.

No directory is moved, no backup is deleted and no absolute snapshot path is rewritten. Journal targets, task paths, fingerprints and action IDs remain byte-for-byte unchanged. Existing settings/preferences, logs and benchmark results remain in the selected store. Old benchmark comparison requirements are unchanged: legacy captures without experiment context can be exported, but advanced comparisons need correctly labeled independent runs.

A shared legacy Windows mutex identifier remains unchanged internally so an older executable and ApexxTweaks cannot ordinarily write the same journal concurrently in one logon session. Close the older version before launching ApexxTweaks.

New opt-in task instructions use `\ApexxTweaksOptional\`. Discovery and undo also accept the previous `\FrameWiseOptional\` namespace with exactly the same principal, executable, signature and definition checks. Existing tasks are not renamed or recreated. Historical audit records and paths retain their original values so recovery information remains accurate; human-readable action descriptions shown by the UI use the new branding.

To upgrade: close the old executable, extract the new portable ZIP, launch `ApexxTweaks.exe`, and check Settings → History / recovery. Pending/applied changes from earlier versions should still be listed. Restore them normally when desired. Do not delete the old data directory after downloading the renamed executable.

## If both data stores contain files

ApexxTweaks refuses to silently choose or merge two populated stores. Neither store is modified. Preserve both directories and their snapshot folders. Each journal may own independent changes, so do not combine JSON or move snapshot directories.

An experienced user can inspect/restore each store separately using a temporary LOCALAPPDATA parent with a directory junction to **one original store**, then repeat for the other. For example, in PowerShell, with the application closed:

```powershell
$originalAppData = $env:LOCALAPPDATA
$selectedStore = Join-Path $originalAppData 'FrameWise' # Legacy compatibility folder; use ApexxTweaks for the other store.
$recoveryParent = Join-Path $env:TEMP ('ApexxTweaks-recovery-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $recoveryParent | Out-Null
New-Item -ItemType Junction -Path (Join-Path $recoveryParent 'ApexxTweaks') -Target $selectedStore | Out-Null
try {
    $env:LOCALAPPDATA = $recoveryParent
    Start-Process -FilePath 'C:\path\to\ApexxTweaks\ApexxTweaks.exe' -Wait
    # In the app: inspect History and restore that store's owned changes.
} finally {
    $env:LOCALAPPDATA = $originalAppData
}
```

Replace the executable path and selected store with your actual paths. The junction writes to the original journal in place; the original absolute snapshot references remain valid. Do not apply new optimizations during this recovery. Outside-setting conflicts are still refused. Keep all original data until restoration of both stores has been verified, then archive one inactive store outside LOCALAPPDATA before normal launch. Never recursively delete backup folders to resolve the conflict.

The Python distribution metadata and command entry point now use the exact product spelling `ApexxTweaks`. Internal imports and `python -m tweaker` remain unchanged. Git history and an existing repository remote URL are not rewritten by this local branding change.

For installations previously made with pip, close the application and uninstall the former Python distribution before installing this project's renamed distribution, so two installed distributions do not both own the same `tweaker` files. This removes installed code/entry points, not the separate user-data folder. Portable ZIP users only need the new extracted application directory; preserve the data stores described above.
