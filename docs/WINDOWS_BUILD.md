# Standalone Windows x64 build and download

The portable package contains `ApexxTweaks.exe`, bundled CPython 3.13 x64, Qt Widgets/Gui/Svg, all application modules and required runtime libraries, plus documentation and the license. **End users do not install Python, pip or PyInstaller.** This is an onedir standalone distribution: keep `_internal` and the other supplied files next to the executable. It is not a single-file EXE or an installer.

## Download and launch

1. Open your ApexxTweaks repository on GitHub and select **Actions → ApexxTweaks Windows x64 portable build**.
2. Select a successful run for the source revision you want. For a manual build, select **Run workflow** on that page (the workflow must exist on the default branch).
3. In the run's **Artifacts**, download **ApexxTweaks-windows-x64**. Sign in with repository read access. Artifacts expire after 30 days in this workflow; rerun the workflow if needed. See [GitHub's artifact download instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).
4. Extract the downloaded artifact archive. It contains `ApexxTweaks-windows-x64.zip`, `SHA256SUMS.txt` and `windows-smoke.json`.
5. Extract **ApexxTweaks-windows-x64.zip** into a normal writable folder. Open the resulting **ApexxTweaks** folder and double-click **ApexxTweaks.exe**. Do not launch inside a ZIP or move the executable away from `_internal`.
6. Start as a standard user. Choose explicit administrator launch only when a particular optimization requires it, as described in the main README. Packaging does not change privilege requirements or application features.

Windows 10 (build 19041+) and Windows 11 x64 are the intended end-user platforms. Individual actions retain their stricter OS/API requirements. The package relies on Windows system components such as PowerShell/CIM for Windows diagnostics; it bundles Python dependencies, not replacement Windows components. Builds are unsigned; inspect the source and provenance rather than disabling security protections.

Optional checksum verification, from the folder containing the inner ZIP:

```powershell
Get-FileHash .\ApexxTweaks-windows-x64.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

For GitHub CLI users on any development OS:

```bash
gh workflow run windows.yml --repo OWNER/REPOSITORY
gh run list --workflow windows.yml --repo OWNER/REPOSITORY
gh run watch RUN_ID --repo OWNER/REPOSITORY --exit-status
gh run download RUN_ID --repo OWNER/REPOSITORY --name ApexxTweaks-windows-x64
```

These commands require your actual repository and authenticated GitHub CLI. They are instructions, not evidence that a workflow was dispatched from this workspace.

## What the workflow does

- Uses an explicit Windows x64 hosted runner (`windows-2025`) and CPython 3.13 **x64**.
- Installs the application and pinned PyInstaller build requirement. Runtime dependencies listed in `pyproject.toml` are installed before analysis; the runtime dependency is pinned PySide6-Essentials 6.8.3 (including shiboken6 and the Qt binaries).
- Runs all automated tests, including GUI and Windows-native tests.
- Builds `build-support/ApexxTweaks.spec`. All ApexxTweaks modules are collected, and PyInstaller's Python/Qt Widgets/Gui/Svg dependency hooks bundle the runtime. No console or silent elevation is added.
- Checks that the EXE is AMD64 PE and that Python 3.13, Qt runtime DLLs, `qwindows.dll`, the QSS theme and documentation are present.
- Copies README/license/docs into the portable directory, creates the ZIP and records its SHA256.
- Extracts the **exact ZIP** to a temporary path containing spaces, changes working directory away from the checkout, clears PYTHONHOME/PYTHONPATH and removes Python from the child's PATH. Runs `ApexxTweaks.exe --smoke-test` with fresh LOCALAPPDATA.
- Requires successful exit within 60 seconds and evidence that the application constructor ran. The 2.0 smoke path constructs the Qt GUI, visits all seven pages, exercises plotting/assets and closes. It does not apply optimizations.
- Uploads the downloadable application artifact **only after successful tests and smoke testing**. Uploads diagnostics separately even after failure where files are available.

The smoke test prevents reliance on a Python executable on PATH and exercises bundled imports/Qt Widgets/Gui/Svg. The hosted runner still has Python installed elsewhere; this is not a clean Windows 11 machine test. `windows-2025` is a Windows Server hosted image, not a Windows 11 desktop. A passing report establishes packaged GUI startup on the reported runner OS, not Windows 11 gaming functionality, every diagnostic, EAC compatibility or performance improvements. Validate on an actual Windows 11 x64 machine before claiming those.

The `windows-smoke.json` report records status, tested OS, ZIP hash, exit code and error. A build-only success is insufficient. Inspect the exact revision and smoke report before distributing a ZIP.

## Build locally on Windows

Install CPython 3.13 x64 and PowerShell 7 (the build scripts use `pwsh`). End users do not need these build tools.

```powershell
python -m pip install -r requirements-build.txt .
python -m unittest discover -s tests -v
pwsh -File scripts/build-windows.ps1
pwsh -File scripts/smoke-windows.ps1
```

Outputs: `dist/ApexxTweaks/`, `dist/ApexxTweaks-windows-x64.zip`, `dist/SHA256SUMS.txt` and, after smoke testing, `dist/windows-smoke.json`. The checked-in spec is the single packaging configuration used locally and in Actions. See [PyInstaller's spec documentation](https://pyinstaller.org/en/stable/spec-files.html).

## Errors and test status

If a run fails, inspect the red step and **ApexxTweaks-windows-build-diagnostics** artifact: dependency versions, PyInstaller warnings/import graph and smoke report when available. No tested application artifact is uploaded after failure. PyInstaller warnings may mention optional/platform-specific modules; the smoke test and actual Windows checks determine whether required modules are missing.

The redesigned Windows workflow has not been executed from this Linux workspace. Source Qt tests, script parsing and a Linux-frozen smoke test do not establish a successful Windows build. Check the [validation record](VALIDATION.md) for exact results and remaining Windows release gates. A configured Git remote is not evidence of a dispatched Actions run.

## 2.0 Qt packaging changes

The checked-in spec collects `tweaker.ui` and its packaged QSS assets, QtCore/Gui/Widgets/Svg, shiboken6 and the native Qt platform plugins through PyInstaller hooks. It explicitly excludes Tk, QML/Quick and WebEngine. The verifier requires Python 3.13, Qt DLLs, `qwindows.dll` and `theme.qss` inside the directory; missing files fail the build. Original stroke icons are code assets, not external downloads. The application dynamically loads Qt's shared libraries; license texts and notices are copied with `docs/`.

The source suite exercises the real Qt widgets with offscreen rendering. The extracted-ZIP smoke test uses the normal Windows Qt platform plugin and the existing fresh LOCALAPPDATA / cleared Python PATH checks. The hosted image is still Windows Server, so a successful run would not replace Windows 10/11 desktop, DPI, driver or anti-cheat validation. The redesigned Windows build has not been run in this Linux workspace.
