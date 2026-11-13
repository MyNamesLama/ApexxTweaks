"""Distribution validation fixtures; these are not Windows executable launch tests."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'scripts' / 'verify-bundle.py'
spec = importlib.util.spec_from_file_location('verify_bundle', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BundleValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        header = bytearray(256)
        header[:2] = b'MZ'
        struct.pack_into('<I', header, 0x3c, 128)
        header[128:132] = b'PE\0\0'
        struct.pack_into('<H', header, 132, 0x8664)
        (self.folder / 'ApexxTweaks.exe').write_bytes(header)
        for name in ('python313.dll', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Svg.dll', 'qwindows.dll'):
            target = self.folder / '_internal' / name
            target.parent.mkdir(exist_ok=True)
            target.touch()
        theme=self.folder/'_internal/tweaker/ui/assets/theme.qss'
        theme.parent.mkdir(parents=True,exist_ok=True); theme.touch()
        for name in ('README.md', 'LICENSE', 'docs/WINDOWS_BUILD.md'):
            target = self.folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()

    def test_complete_x64_structure(self):
        from contextlib import redirect_stdout
        import io
        with redirect_stdout(io.StringIO()):
            module.verify(self.folder)

    def test_x86_binary_rejected(self):
        exe = self.folder / 'ApexxTweaks.exe'
        data = bytearray(exe.read_bytes())
        struct.pack_into('<H', data, 132, 0x14c)
        exe.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'AMD64'):
            module.verify(self.folder)

    def test_missing_qt_platform_plugin_rejected(self):
        (self.folder / '_internal/qwindows.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'qwindows.dll'):
            module.verify(self.folder)

    def test_non_windows_binary_rejected(self):
        (self.folder / 'ApexxTweaks.exe').write_bytes(b'\x7fELF')
        with self.assertRaisesRegex(ValueError, 'Windows PE'):
            module.verify(self.folder)


    def test_theme_in_wrong_directory_does_not_mask_missing_packaged_asset(self):
        theme=self.folder/'_internal/tweaker/ui/assets/theme.qss'
        theme.unlink(); (self.folder/'theme.qss').touch()
        with self.assertRaisesRegex(ValueError,'UI asset'): module.verify(self.folder)
