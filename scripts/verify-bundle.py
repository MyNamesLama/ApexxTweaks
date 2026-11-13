"""Fail the build if x64 PE or required bundled Python/Tk components are missing."""
import struct
import sys
from pathlib import Path


def verify(folder):
    folder = Path(folder)
    executable = folder / 'ApexxTweaks.exe'
    with executable.open('rb') as f:
        if f.read(2) != b'MZ':
            raise ValueError('ApexxTweaks.exe is not a Windows PE executable')
        f.seek(0x3c)
        offset = struct.unpack('<I', f.read(4))[0]
        f.seek(offset)
        if f.read(4) != b'PE\0\0' or struct.unpack('<H', f.read(2))[0] != 0x8664:
            raise ValueError('ApexxTweaks.exe must target AMD64/x64')
    for pattern in ('python313.dll', '_tkinter.pyd', 'init.tcl', 'tk.tcl'):
        if not any(folder.rglob(pattern)):
            raise ValueError(f'Missing bundled runtime dependency: {pattern}')
    for relative in ('README.md', 'LICENSE', 'docs/WINDOWS_BUILD.md'):
        if not (folder / relative).is_file():
            raise ValueError(f'Missing distribution file: {relative}')
    print('Bundle structure validated: Windows x64 PE, Python, Tcl/Tk and documentation. Launch not yet tested.')


if __name__ == '__main__':
    verify(sys.argv[1])
