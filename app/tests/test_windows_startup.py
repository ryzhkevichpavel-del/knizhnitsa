import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from windows_startup import (  # noqa: E402
    ACTIVATE_EVENT_NAME,
    APP_USER_MODEL_ID,
    INSTALLER_MUTEX_NAME,
    LEGACY_ACTIVATE_EVENT_NAME,
    MUTEX_NAME,
    SingleInstance,
    StartupLog,
    StartupSplash,
    set_process_app_user_model_id,
)


@unittest.skipUnless(sys.platform == "win32", "Проверки предназначены для Windows")
class WindowsStartupTests(unittest.TestCase):
    def test_default_instance_objects_cover_all_windows_sessions_for_one_user(self):
        self.assertTrue(MUTEX_NAME.startswith("Global\\KnizhnitsaSingleInstance_"))
        self.assertTrue(ACTIVATE_EVENT_NAME.startswith("Global\\KnizhnitsaActivate_"))
        self.assertEqual(MUTEX_NAME.rsplit("_", 1)[-1], ACTIVATE_EVENT_NAME.rsplit("_", 1)[-1])
        self.assertEqual(INSTALLER_MUTEX_NAME, "Local\\KnizhnitsaSingleInstance")
        self.assertEqual(LEGACY_ACTIVATE_EVENT_NAME, "Local\\KnizhnitsaActivate")

    def test_webview_is_not_imported_at_main_module_entry(self):
        import main

        self.assertIsNone(main.webview)
        self.assertNotIn("webview", sys.modules)

    def test_close_flush_runs_outside_native_closing_callback(self):
        main_text = (APP_DIR / "main.py").read_text(encoding="utf-8")
        self.assertIn("def flush_then_close():", main_text)
        self.assertIn(
            'threading.Thread(target=flush_then_close, name="close-flush", daemon=True).start()',
            main_text,
        )
        closing_body = main_text.split("def on_window_closing(*_):", 1)[1].split(
            "window.events.shown", 1
        )[0]
        self.assertIn("return False", closing_body)
        self.assertNotIn("evaluate_js", closing_body)

    def test_app_user_model_id_is_explicit(self):
        self.assertTrue(set_process_app_user_model_id())
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        value = ctypes.c_wchar_p()
        shell32.GetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.POINTER(ctypes.c_wchar_p)]
        shell32.GetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        self.assertGreaterEqual(shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)), 0)
        try:
            self.assertEqual(value.value, APP_USER_MODEL_ID)
        finally:
            ole32 = ctypes.WinDLL("ole32", use_last_error=True)
            ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
            ole32.CoTaskMemFree.restype = None
            ole32.CoTaskMemFree(value)

    def test_activation_signal_waits_until_listener_starts(self):
        unique = uuid.uuid4().hex
        mutex_name = f"Local\\KnizhnitsaTestMutex_{unique}"
        event_name = f"Local\\KnizhnitsaTestEvent_{unique}"
        with tempfile.TemporaryDirectory() as folder:
            logger = StartupLog(folder)
            primary = SingleInstance(folder, logger, mutex_name=mutex_name, event_name=event_name)
            self.assertEqual(primary.acquire(), "primary")
            child_code = (
                "import sys; "
                f"sys.path.insert(0, {str(APP_DIR)!r}); "
                "from windows_startup import StartupLog, SingleInstance; "
                f"folder={folder!r}; "
                "log=StartupLog(folder); "
                f"instance=SingleInstance(folder, log, mutex_name={mutex_name!r}, event_name={event_name!r}); "
                "print(instance.acquire())"
            )
            child = subprocess.run(
                [sys.executable, "-c", child_code],
                check=True,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=10,
            )
            self.assertEqual(child.stdout.strip(), "secondary")

            received = threading.Event()
            primary.start_listener(received.set)
            self.assertTrue(received.wait(2), "Сигнал второго запуска потерян")
            primary.close()

    def test_startup_log_rotates(self):
        with tempfile.TemporaryDirectory() as folder:
            logger = StartupLog(folder, max_bytes=100)
            Path(logger.path).write_text("x" * 101, encoding="utf-8")
            logger.rotate_if_needed()
            self.assertFalse(Path(logger.path).exists())
            self.assertEqual(Path(logger.previous_path).stat().st_size, 101)
            logger.write("test_stage", value="ok")
            text = Path(logger.path).read_text(encoding="utf-8")
            self.assertIn("stage=test_stage", text)

    def test_native_splash_opens_and_closes(self):
        splash = StartupSplash(str(APP_DIR / "icon.ico"), slow_after=5)
        self.assertTrue(splash.start())
        self.assertIsNotNone(splash.hwnd)
        splash.stop()
        deadline = time.monotonic() + 2
        while splash.hwnd is not None and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertIsNone(splash.hwnd)


if __name__ == "__main__":
    unittest.main()
