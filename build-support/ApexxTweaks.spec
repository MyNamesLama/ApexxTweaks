# Windows x64 portable directory: Python runtime, Tcl/Tk and all ApexxTweaks modules.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules

project = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(project))
a = Analysis(
    [str(project / 'launcher.py')],
    pathex=[str(project)],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('tweaker') + ['tkinter.ttk', 'ctypes.wintypes', 'winreg'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='ApexxTweaks',
    console=False,
    debug=False,
    strip=False,
    upx=False,
    uac_admin=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='ApexxTweaks', strip=False, upx=False)
