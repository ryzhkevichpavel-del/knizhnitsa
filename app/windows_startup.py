# -*- coding: utf-8 -*-
"""Лёгкий Windows-запуск до импорта pywebview.

Модуль использует только стандартную библиотеку: показывает небольшую заставку,
не допускает гонку нескольких экземпляров, передаёт запрос активации первому
процессу и пишет компактный журнал этапов запуска.
"""
import ctypes
import hashlib
import os
import threading
import time
from ctypes import wintypes
from datetime import datetime


APP_USER_MODEL_ID = "Knizhnitsa.Desktop"


def _user_kernel_scope():
    """Stable per-user suffix for kernel objects shared by Windows sessions."""
    identity = os.environ.get("USERPROFILE") or os.path.expanduser("~") or os.environ.get("USERNAME") or "default"
    normalized = os.path.normcase(os.path.abspath(identity)).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(normalized).hexdigest()[:16]


_KERNEL_SCOPE = _user_kernel_scope()
MUTEX_NAME = f"Global\\KnizhnitsaSingleInstance_{_KERNEL_SCOPE}"
ACTIVATE_EVENT_NAME = f"Global\\KnizhnitsaActivate_{_KERNEL_SCOPE}"
INSTALLER_MUTEX_NAME = "Local\\KnizhnitsaSingleInstance"
LEGACY_ACTIVATE_EVENT_NAME = "Local\\KnizhnitsaActivate"

ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
EVENT_MODIFY_STATE = 0x0002
SW_SHOW = 5
SW_RESTORE = 9
FLASHW_TRAY = 0x00000002
FLASHW_TIMERNOFG = 0x0000000C


class StartupLog:
    """Построчный журнал запуска с ограничением примерно в 512 КБ."""

    def __init__(self, folder, max_bytes=256 * 1024):
        self.path = os.path.join(folder, "startup.log")
        self.previous_path = os.path.join(folder, "startup.previous.log")
        self.max_bytes = max_bytes
        self.started = time.perf_counter()
        self.run_id = f"{os.getpid():x}-{time.time_ns():x}"
        self._lock = threading.Lock()

    def rotate_if_needed(self):
        try:
            if not os.path.exists(self.path) or os.path.getsize(self.path) <= self.max_bytes:
                return
            if os.path.exists(self.previous_path):
                os.remove(self.previous_path)
            os.replace(self.path, self.previous_path)
        except OSError:
            pass

    @staticmethod
    def _safe(value):
        text = str(value).replace("\r", " ").replace("\n", " ")
        return text[:180]

    def write(self, stage, **fields):
        stamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        elapsed_ms = int((time.perf_counter() - self.started) * 1000)
        parts = [
            stamp,
            f"pid={os.getpid()}",
            f"run={self.run_id}",
            f"elapsed_ms={elapsed_ms}",
            f"stage={self._safe(stage)}",
        ]
        parts.extend(f"{key}={self._safe(value)}" for key, value in fields.items())
        line = " ".join(parts) + "\n"
        try:
            with self._lock:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as stream:
                    stream.write(line)
                    stream.flush()
        except OSError:
            pass


def set_process_app_user_model_id(app_id=APP_USER_MODEL_ID):
    """Задаёт Windows постоянный идентификатор приложения для панели задач."""
    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        func = shell32.SetCurrentProcessExplicitAppUserModelID
        func.argtypes = [wintypes.LPCWSTR]
        func.restype = ctypes.c_long
        return func(app_id) >= 0
    except (AttributeError, OSError):
        return False


class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("dwFlags", wintypes.DWORD),
        ("uCount", wintypes.UINT),
        ("dwTimeout", wintypes.DWORD),
    ]


def _find_window_for_process(pid, exact_title):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found = []
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [enum_proc_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    @enum_proc_type
    def visit(hwnd, _):
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if buffer.value == exact_title:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def activate_process_window(pid, exact_title, wait_seconds=0, logger=None):
    """Разворачивает окно процесса; при запрете фокуса подсвечивает кнопку."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindowAsync.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.FlashWindowEx.argtypes = [ctypes.POINTER(FLASHWINFO)]
    user32.FlashWindowEx.restype = wintypes.BOOL

    deadline = time.monotonic() + max(0, wait_seconds)
    while True:
        hwnd = _find_window_for_process(pid, exact_title)
        if hwnd:
            command = SW_RESTORE if user32.IsIconic(hwnd) else SW_SHOW
            user32.ShowWindowAsync(hwnd, command)
            user32.BringWindowToTop(hwnd)
            focused = bool(user32.SetForegroundWindow(hwnd))
            if not focused:
                info = FLASHWINFO(
                    ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_TRAY | FLASHW_TIMERNOFG, 3, 0
                )
                user32.FlashWindowEx(ctypes.byref(info))
            if logger:
                logger.write("activation_completed", focused=focused)
            return True
        if time.monotonic() >= deadline:
            if logger:
                logger.write("activation_window_not_ready")
            return False
        time.sleep(0.1)


class SingleInstance:
    """Mutex + auto-reset событие, которое не теряется до создания окна."""

    def __init__(self, data_folder, logger, mutex_name=MUTEX_NAME, event_name=ACTIVATE_EVENT_NAME):
        self.data_folder = data_folder
        self.logger = logger
        self.mutex_name = mutex_name
        self.event_name = event_name
        self.pid_path = os.path.join(data_folder, "instance.pid")
        self.mutex_handle = None
        self.event_handle = None
        self.installer_mutex_handle = None
        self.legacy_event_handle = None
        self.use_compatibility_aliases = mutex_name == MUTEX_NAME and event_name == ACTIVATE_EVENT_NAME
        self.is_primary = False
        self._stopping = threading.Event()
        self._listener = None

    @staticmethod
    def _kernel32():
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.SetEvent.argtypes = [wintypes.HANDLE]
        kernel32.SetEvent.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        return kernel32

    def acquire(self):
        kernel32 = self._kernel32()
        # Событие создаётся раньше mutex: сигнал второго процесса не потеряется,
        # даже если первый ещё не успел запустить поток ожидания.
        self.event_handle = kernel32.CreateEventW(None, False, False, self.event_name)
        if not self.event_handle:
            self.logger.write("instance_error", error="CreateEventW")
            return "error"
        ctypes.set_last_error(0)
        self.mutex_handle = kernel32.CreateMutexW(None, False, self.mutex_name)
        mutex_error = ctypes.get_last_error()
        if not self.mutex_handle:
            self.logger.write("instance_error", error="CreateMutexW")
            kernel32.CloseHandle(self.event_handle)
            self.event_handle = None
            return "error"
        if mutex_error == ERROR_ALREADY_EXISTS:
            self._signal_primary(kernel32)
            kernel32.CloseHandle(self.mutex_handle)
            kernel32.CloseHandle(self.event_handle)
            self.mutex_handle = None
            self.event_handle = None
            return "secondary"
        if self.use_compatibility_aliases:
            self.legacy_event_handle = kernel32.CreateEventW(None, False, False, LEGACY_ACTIVATE_EVENT_NAME)
            ctypes.set_last_error(0)
            self.installer_mutex_handle = kernel32.CreateMutexW(None, False, INSTALLER_MUTEX_NAME)
            legacy_error = ctypes.get_last_error()
            if self.installer_mutex_handle and legacy_error == ERROR_ALREADY_EXISTS:
                pid = self._read_pid()
                signalled = bool(self.legacy_event_handle and kernel32.SetEvent(self.legacy_event_handle))
                self.logger.write("instance_secondary_legacy", primary_pid=pid or "unknown", signalled=signalled)
                for handle_name in ("installer_mutex_handle", "legacy_event_handle", "mutex_handle", "event_handle"):
                    handle = getattr(self, handle_name)
                    if handle:
                        kernel32.CloseHandle(handle)
                        setattr(self, handle_name, None)
                return "secondary"
            if not self.installer_mutex_handle or not self.legacy_event_handle:
                self.logger.write("instance_compatibility_alias_failed")
        self.is_primary = True
        self._write_pid()
        return "primary"

    def _write_pid(self):
        try:
            os.makedirs(self.data_folder, exist_ok=True)
            temp_path = self.pid_path + ".tmp"
            with open(temp_path, "w", encoding="ascii") as stream:
                stream.write(str(os.getpid()))
            os.replace(temp_path, self.pid_path)
        except OSError as exc:
            self.logger.write("instance_pid_write_failed", error=type(exc).__name__)

    def _read_pid(self):
        for _ in range(20):
            try:
                with open(self.pid_path, "r", encoding="ascii") as stream:
                    pid = int(stream.read().strip())
                if pid > 0:
                    return pid
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        return None

    def _signal_primary(self, kernel32):
        pid = self._read_pid()
        if pid:
            try:
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
                user32.AllowSetForegroundWindow.restype = wintypes.BOOL
                user32.AllowSetForegroundWindow(pid)
                activate_process_window(pid, "Книжница", logger=self.logger)
            except OSError:
                pass
        signalled = bool(kernel32.SetEvent(self.event_handle))
        self.logger.write("instance_secondary", primary_pid=pid or "unknown", signalled=signalled)

    def start_listener(self, callback):
        if not self.is_primary or not self.event_handle:
            return
        kernel32 = self._kernel32()

        def listen():
            while not self._stopping.is_set():
                result = kernel32.WaitForSingleObject(self.event_handle, 250)
                if result == WAIT_OBJECT_0:
                    self.logger.write("activation_requested")
                    try:
                        callback()
                    except Exception as exc:
                        self.logger.write("activation_failed", error=type(exc).__name__)
                elif result != WAIT_TIMEOUT:
                    break

        self._listener = threading.Thread(target=listen, name="KnizhnitsaActivation", daemon=True)
        self._listener.start()

    def close(self):
        self._stopping.set()
        if self._listener:
            self._listener.join(timeout=0.6)
        kernel32 = self._kernel32()
        for handle_name in ("legacy_event_handle", "installer_mutex_handle", "event_handle", "mutex_handle"):
            handle = getattr(self, handle_name)
            if handle:
                kernel32.CloseHandle(handle)
                setattr(self, handle_name, None)
        if self.is_primary:
            try:
                with open(self.pid_path, "r", encoding="ascii") as stream:
                    owns_file = int(stream.read().strip()) == os.getpid()
                if owns_file:
                    os.remove(self.pid_path)
            except (OSError, ValueError):
                pass


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class StartupSplash:
    """Небольшое Win32-окно, не создающее отдельную кнопку на панели задач."""

    def __init__(self, icon_path=None, slow_after=30):
        self.icon_path = icon_path
        self.slow_after = slow_after
        self.hwnd = None
        self.thread_id = None
        self._thread = None
        self._ready = threading.Event()
        self._stop_requested = threading.Event()
        self._slow = False
        self._wndproc = None
        self._timer = None

    def start(self):
        self._thread = threading.Thread(target=self._run, name="KnizhnitsaSplash", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=1.5)
        if self.hwnd:
            self._timer = threading.Timer(self.slow_after, self._mark_slow)
            self._timer.daemon = True
            self._timer.start()
        return bool(self.hwnd)

    def _mark_slow(self):
        self._slow = True
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
            user32.InvalidateRect.restype = wintypes.BOOL
            if self.hwnd:
                user32.InvalidateRect(self.hwnd, None, True)
        except OSError:
            pass

    def stop(self):
        self._stop_requested.set()
        if self._timer:
            self._timer.cancel()
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostMessageW.restype = wintypes.BOOL
            user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostThreadMessageW.restype = wintypes.BOOL
            if self.hwnd:
                user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
            elif self.thread_id:
                user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT
        except OSError:
            pass

    def _run(self):
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        self.thread_id = kernel32.GetCurrentThreadId()

        wndproc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        user32.LoadCursorW.restype = wintypes.HANDLE
        user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
        user32.RegisterClassExW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyWindow.restype = wintypes.BOOL
        user32.PostQuitMessage.argtypes = [ctypes.c_int]
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.UpdateWindow.argtypes = [wintypes.HWND]
        user32.UpdateWindow.restype = wintypes.BOOL
        user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
        user32.SetWindowRgn.restype = ctypes.c_int
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = wintypes.BOOL
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.TranslateMessage.restype = wintypes.BOOL
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype = ctypes.c_ssize_t
        user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        user32.UnregisterClassW.restype = wintypes.BOOL
        user32.DestroyIcon.argtypes = [wintypes.HICON]
        user32.DestroyIcon.restype = wintypes.BOOL
        user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
        user32.BeginPaint.restype = wintypes.HDC
        user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
        user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
        user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT]
        user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON, ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
        gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
        gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
        gdi32.CreateFontW.restype = wintypes.HFONT
        gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
        gdi32.SetBkMode.restype = ctypes.c_int
        gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
        gdi32.SetTextColor.restype = wintypes.COLORREF
        gdi32.CreateRoundRectRgn.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
        ]
        gdi32.CreateRoundRectRgn.restype = wintypes.HRGN
        gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi32.SelectObject.restype = wintypes.HGDIOBJ
        gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        gdi32.DeleteObject.restype = wintypes.BOOL

        background = gdi32.CreateSolidBrush(0x00201F1F)
        title_font = gdi32.CreateFontW(-25, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        text_font = gdi32.CreateFontW(-16, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        icon = None
        if self.icon_path and os.path.exists(self.icon_path):
            user32.LoadImageW.argtypes = [
                wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                ctypes.c_int, ctypes.c_int, wintypes.UINT,
            ]
            user32.LoadImageW.restype = wintypes.HANDLE
            icon = user32.LoadImageW(None, self.icon_path, 1, 48, 48, 0x0010)

        @wndproc_type
        def wndproc(hwnd, message, wparam, lparam):
            if message == 0x000F:  # WM_PAINT
                paint = PAINTSTRUCT()
                hdc = user32.BeginPaint(hwnd, ctypes.byref(paint))
                rect = wintypes.RECT(0, 0, 420, 126)
                user32.FillRect(hdc, ctypes.byref(rect), background)
                gdi32.SetBkMode(hdc, 1)
                gdi32.SetTextColor(hdc, 0x00F4F4F4)
                if icon:
                    user32.DrawIconEx(hdc, 27, 38, icon, 48, 48, 0, None, 3)
                left = 92 if icon else 30
                title_rect = wintypes.RECT(left, 29, 395, 65)
                gdi32.SelectObject(hdc, title_font)
                user32.DrawTextW(hdc, "Книжница", -1, ctypes.byref(title_rect), 0x00000020)
                gdi32.SetTextColor(hdc, 0x00B8B8B8)
                text_rect = wintypes.RECT(left, 68, 395, 98)
                gdi32.SelectObject(hdc, text_font)
                message_text = (
                    "Запуск занимает больше времени…"
                    if self._slow else "Приложение запускается…"
                )
                user32.DrawTextW(hdc, message_text, -1, ctypes.byref(text_rect), 0x00000020)
                user32.EndPaint(hwnd, ctypes.byref(paint))
                return 0
            if message == 0x0010:  # WM_CLOSE
                user32.DestroyWindow(hwnd)
                return 0
            if message == 0x0002:  # WM_DESTROY
                self.hwnd = None
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wndproc = wndproc
        class_name = f"KnizhnitsaStartupWindow_{os.getpid()}"
        hinstance = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW(
            ctypes.sizeof(WNDCLASSEXW),
            0,
            ctypes.cast(wndproc, ctypes.c_void_p),
            0,
            0,
            hinstance,
            icon,
            user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR)),
            background,
            None,
            class_name,
            icon,
        )
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if atom:
            width, height = 420, 126
            x = max(0, (user32.GetSystemMetrics(0) - width) // 2)
            y = max(0, (user32.GetSystemMetrics(1) - height) // 2)
            ex_style = 0x00000080 | 0x00000008 | 0x08000000  # TOOLWINDOW | TOPMOST | NOACTIVATE
            self.hwnd = user32.CreateWindowExW(
                ex_style, class_name, "Книжница запускается", 0x80000000,
                x, y, width, height, None, None, hinstance, None
            )
            if self.hwnd:
                region = gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, 18, 18)
                user32.SetWindowRgn(self.hwnd, region, True)
                user32.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
                user32.UpdateWindow(self.hwnd)
        self._ready.set()
        if self._stop_requested.is_set() and self.hwnd:
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0)
        if self.hwnd:
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        if atom:
            user32.UnregisterClassW(class_name, hinstance)
        for obj in (title_font, text_font, background):
            if obj:
                gdi32.DeleteObject(obj)
        if icon:
            user32.DestroyIcon(icon)
