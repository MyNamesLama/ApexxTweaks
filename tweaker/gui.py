"""Stable application entry point for the ApexxTweaks 2.0 Qt frontend."""

import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from .branding import APP_NAME, JOURNAL_MUTEX
from .ui.window import App
from .ui.controller import PAGES


def main(smoke=False):
    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion("2.0.0")
    lock = None
    kernel = None
    if os.name == "nt":
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        lock = kernel.CreateMutexW(None, False, JOURNAL_MUTEX)
        if not lock or ctypes.get_last_error() == 183:
            if lock:
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel.CloseHandle(lock)
            if smoke:
                raise RuntimeError(
                    "Another application instance owns the recovery journal"
                )
            QMessageBox.warning(
                None,
                APP_NAME,
                APP_NAME + " is already running or the journal lock is unavailable.",
            )
            return 1
    try:
        window = App()
        if smoke:
            # Exercise the actual frontend, assets, navigation and plots, but never
            # run diagnostics, mutate Windows or modify imported benchmark files.
            window.show()
            application.processEvents()
            for page in PAGES:
                window.navigate(page, animate=False)
                application.processEvents()
            window.pages["System Monitor"].charts["cpu"].set_values([10, 20, 15])
            window.pages["Benchmarks"].histogram.set_values([1, 2, 3, 4, 5, 6, 7])
            application.processEvents()
            window.shutdown()
            window.close()
            application.processEvents()
            return 0
        if window.controller.preferences["start_minimized"]:
            window.showMinimized()
        else:
            window.show()
        return application.exec()
    except Exception as error:
        if smoke:
            raise
        QMessageBox.critical(
            None,
            APP_NAME + " could not start",
            str(error)
            + "\n\nPreserve application data and recovery journals before repairing files.",
        )
        return 1
    finally:
        if lock:
            import ctypes

            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(lock)
