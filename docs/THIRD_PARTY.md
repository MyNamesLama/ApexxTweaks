# Runtime and asset notices

ApexxTweaks application code is MIT licensed (root LICENSE). Original stroke icons and QSS styling are application assets; no downloaded logo, icon font or proprietary application design is bundled.

The 2.0 GUI uses **PySide6 Essentials / shiboken6 6.8.3** and dynamically loaded Qt 6.8 shared libraries. PySide/Qt are distributed under their applicable open-source/commercial license terms, separate from the application's MIT license. The LGPL v3 and incorporated GPL v3 texts are included in `docs/licenses/`, obtained verbatim from the official PySide source tag:

- https://github.com/pyside/pyside-setup/tree/v6.8.3/LICENSES
- https://doc.qt.io/qtforpython-6/licenses.html
- https://doc.qt.io/qt-6.8/licenses-used-in-qt.html
- https://github.com/pyside/pyside-setup/tree/v6.8.3
- https://github.com/qt/qtbase/tree/v6.8.3

Qt binaries may include additional third-party components; upstream Qt attribution/license documentation and corresponding source accompany the above upstream materials. These notices do not relicense Qt under MIT or certify a distributor's compliance. Keep the supplied shared libraries, application documentation and license texts when distributing the portable directory.

CPython, PyInstaller and their runtime components retain their respective upstream licenses. The Windows operating system, PowerShell and CIM providers are host dependencies, not bundled replacements.
