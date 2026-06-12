# -*- coding: utf-8 -*-
"""
Книжница — нативное приложение для Windows для написания книг.
Окно на движке WebView2 (Edge), интерфейс — ui.html.
Данные хранятся в реальном файле: %APPDATA%\\Книжница\\library.json
"""
import os
import io
import sys
import re
import json
import time
import shutil
import base64
import ctypes
import mimetypes
from datetime import datetime
import webview

APP_NAME = "Книжница"
MUTEX_NAME = "Local\\KnizhnitsaSingleInstance"
LEGACY_APP_NAMES = ("Пиши книгу",)
MAX_BACKUPS = 15
AUTO_BACKUP_INTERVAL = 10 * 60
ALWAYS_START_MAXIMIZED = True
window = None
instance_mutex = None
last_auto_backup = 0


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


DATA_FILE = os.path.join(data_dir(), "library.json")
BACKUP_DIR = os.path.join(data_dir(), "Резервные копии")
WINDOW_STATE_FILE = os.path.join(data_dir(), "window.json")


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def appdata_dir(app_name):
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, app_name)


def result(ok=True, error=""):
    return {"ok": bool(ok), "error": error}


def norm_lang(lang):
    return "en" if lang == "en" else "ru"


def msg(lang, ru, en):
    return en if norm_lang(lang) == "en" else ru


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def has_books(raw):
    try:
        data = json.loads(raw)
        return bool(data.get("books"))
    except Exception:
        return False


def current_file_has_books():
    if not os.path.exists(DATA_FILE):
        return False
    try:
        return has_books(read_text(DATA_FILE))
    except Exception:
        return False


def migrate_legacy_data():
    if current_file_has_books():
        return
    for old_name in LEGACY_APP_NAMES:
        old_file = os.path.join(appdata_dir(old_name), "library.json")
        if not os.path.exists(old_file):
            continue
        try:
            raw = read_text(old_file)
            if not has_books(raw):
                continue
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            if os.path.exists(DATA_FILE):
                create_backup_from_text(read_text(DATA_FILE), "перед переносом")
            shutil.copy2(old_file, DATA_FILE)
            create_backup_from_text(raw, "перенесено из старой версии")
            return
        except Exception:
            continue


def safe_slug(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:70] or APP_NAME


def backup_name(reason):
    stamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    return f"{stamp} - {safe_slug(reason)}.json"


def read_latest_backup_bytes():
    try:
        files = [
            os.path.join(BACKUP_DIR, n)
            for n in os.listdir(BACKUP_DIR)
            if n.lower().endswith(".json")
        ]
        if not files:
            return None
        latest = max(files, key=os.path.getmtime)
        with open(latest, "rb") as f:
            return f.read()
    except Exception:
        return None


def recycle_path(path):
    try:
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        op = SHFILEOPSTRUCTW()
        op.wFunc = 3
        op.pFrom = path + "\0\0"
        op.fFlags = 0x0040 | 0x0010 | 0x0400 | 0x0004
        if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0:
            return True
    except Exception:
        pass
    try:
        os.remove(path)
    except Exception:
        pass
    return False


def prune_backups():
    try:
        files = [
            os.path.join(BACKUP_DIR, n)
            for n in os.listdir(BACKUP_DIR)
            if n.lower().endswith(".json")
        ]
        files.sort(key=os.path.getmtime, reverse=True)
        for path in files[MAX_BACKUPS:]:
            recycle_path(path)
    except Exception:
        pass


def create_backup_from_text(data, reason, lang="ru"):
    if not data:
        return result(True)
    try:
        raw = data.encode("utf-8")
        if read_latest_backup_bytes() == raw:
            return result(True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        path = os.path.join(BACKUP_DIR, backup_name(reason))
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        prune_backups()
        return {"ok": True, "path": path, "error": ""}
    except Exception as e:
        return result(False, f"{msg(lang, 'Не удалось сделать резервную копию', 'Could not create a backup')}: {e}")


def backup_current_file(reason, force=False, lang="ru"):
    global last_auto_backup
    if not os.path.exists(DATA_FILE):
        return result(True)
    if not force and time.time() - last_auto_backup < AUTO_BACKUP_INTERVAL:
        return result(True)
    try:
        res = create_backup_from_text(read_text(DATA_FILE), reason, lang)
        if res.get("ok"):
            last_auto_backup = time.time()
        return res
    except Exception as e:
        return result(False, f"{msg(lang, 'Не удалось сделать резервную копию', 'Could not create a backup')}: {e}")


def load_initial_settings():
    settings = {"theme": "light", "accent": "#3f4ea3", "fontSize": 19, "lang": "ru"}
    try:
        if os.path.exists(DATA_FILE):
            data = json.loads(read_text(DATA_FILE))
            saved = data.get("settings") or {}
            if saved.get("theme") in ("light", "dark"):
                settings["theme"] = saved["theme"]
            if re.match(r"^#[0-9a-fA-F]{6}$", saved.get("accent") or ""):
                settings["accent"] = saved["accent"]
            if isinstance(saved.get("fontSize"), int):
                settings["fontSize"] = saved["fontSize"]
            if saved.get("lang") == "en":
                settings["lang"] = "en"
    except Exception:
        pass
    return settings


def accent_soft(hex_color, theme):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    alpha = 0.22 if theme == "dark" else 0.13
    return f"rgba({r},{g},{b},{alpha})"


def prepare_html(html, settings):
    theme = settings["theme"]
    accent = settings["accent"]
    lang = norm_lang(settings.get("lang"))
    soft = accent_soft(accent, theme)
    html = html.replace('data-theme="light"', f'data-theme="{theme}"', 1)
    html = re.sub(r'<html lang="[^"]+"', f'<html lang="{lang}"', html, count=1)
    initial = (
        "<script>"
        f"window.__INITIAL_SETTINGS__={json.dumps(settings, ensure_ascii=False)};"
        "</script>"
    )
    style = (
        "<style id=\"initialAccent\">"
        f":root,[data-theme=\"light\"],[data-theme=\"dark\"]{{--accent:{accent};--accent-soft:{soft};}}"
        "</style>"
    )
    return html.replace("</head>", initial + style + "</head>", 1)


def load_window_state():
    try:
        with open(WINDOW_STATE_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
        w = int(s.get("width", 0))
        h = int(s.get("height", 0))
        if w < 940 or h < 620:          # не меньше min_size
            return None
        state = {"width": w, "height": h}
        if isinstance(s.get("x"), int) and isinstance(s.get("y"), int):
            state["x"] = s["x"]
            state["y"] = s["y"]
        state["maximized"] = bool(s.get("maximized"))
        return state
    except Exception:
        return None


def save_window_state():
    if window is None:
        return
    try:
        state = {
            "width": int(window.width),
            "height": int(window.height),
            "x": int(window.x),
            "y": int(window.y),
        }
        tmp = WINDOW_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, WINDOW_STATE_FILE)
    except Exception:
        pass


def acquire_single_instance():
    global instance_mutex
    try:
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        instance_mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        # use_last_error → берём код ошибки сразу, ctypes не затирает его
        if ctypes.get_last_error() != ERROR_ALREADY_EXISTS:
            return True
        # второй экземпляр: показываем уже открытое окно и выходим
        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        hwnd = user32.FindWindowW(None, APP_NAME)
        if hwnd:
            user32.ShowWindow(ctypes.c_void_p(hwnd), 9)   # SW_RESTORE
            user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
        return False
    except Exception:
        return True


class Api:
    """Мост между интерфейсом (JS) и диском (Python)."""

    # ---- данные книг ----
    def load(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
        except Exception:
            return ""

    def save(self, data, lang="ru"):
        lang = norm_lang(lang)
        try:
            old = ""
            if os.path.exists(DATA_FILE):
                old = read_text(DATA_FILE)
            if old and old != data:
                backup_res = backup_current_file(
                    msg(lang, "автокопия перед сохранением", "auto backup before saving"),
                    lang=lang,
                )
                if not backup_res.get("ok"):
                    return backup_res
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, DATA_FILE)  # атомарно — не потеряем книгу при сбое
            return result(True)
        except Exception as e:
            return result(False, f"{msg(lang, 'Не удалось сохранить библиотеку', 'Could not save library')}: {e}")

    def data_location(self):
        return DATA_FILE

    def backup_state(self, data, reason="ручная копия", lang="ru"):
        return create_backup_from_text(data, reason, lang)

    # ---- цвет системного заголовка окна (Windows 11) ----
    def set_titlebar(self, caption_hex):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.FindWindowW.restype = ctypes.c_void_p
            user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
            hwnd = user32.FindWindowW(None, APP_NAME)
            if not hwnd:
                return False
            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
            dwm.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]

            def cref(h):
                h = h.lstrip("#")
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return r | (g << 8) | (b << 16)  # COLORREF = 0x00BBGGRR

            dark = ctypes.c_int(1)
            dwm(hwnd, 20, ctypes.byref(dark), 4)                       # IMMERSIVE_DARK_MODE → светлые кнопки
            cap = ctypes.c_int(cref(caption_hex))
            dwm(hwnd, 35, ctypes.byref(cap), 4)                        # CAPTION_COLOR
            txt = ctypes.c_int(cref("#ffffff"))
            dwm(hwnd, 36, ctypes.byref(txt), 4)                        # TEXT_COLOR
            return True
        except Exception:
            return False

    # ---- выбор изображения (фото персонажа / фон карты) ----
    def pick_image(self, lang="ru"):
        lang = norm_lang(lang)
        try:
            paths = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=(
                    msg(lang, "Изображения (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif)", "Images (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif)"),
                    msg(lang, "Все файлы (*.*)", "All files (*.*)"),
                ),
            )
            if not paths:
                return ""
            p = paths[0] if isinstance(paths, (list, tuple)) else paths
            # уменьшаем картинку, чтобы файл библиотеки не разрастался
            try:
                from PIL import Image
                img = Image.open(p)
                img.thumbnail((1000, 1000))
                buf = io.BytesIO()
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGBA")
                    img.save(buf, "PNG")
                    mime = "image/png"
                else:
                    img = img.convert("RGB")
                    img.save(buf, "JPEG", quality=84)
                    mime = "image/jpeg"
                data = base64.b64encode(buf.getvalue()).decode("ascii")
                return "data:%s;base64,%s" % (mime, data)
            except Exception:
                with open(p, "rb") as f:
                    data = base64.b64encode(f.read()).decode("ascii")
                mime = mimetypes.guess_type(p)[0] or "image/png"
                return "data:%s;base64,%s" % (mime, data)
        except Exception:
            return ""

    # ---- экспорт готовой книги ----
    def export_docx(self, book, lang="ru"):
        lang = norm_lang(lang)
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Pt, Inches

            title = (book or {}).get("title") or msg(lang, "книга", "book")
            path = window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=f"{safe_slug(title)}.docx",
                file_types=(msg(lang, "Документ Word (*.docx)", "Word document (*.docx)"),),
            )
            if not path:
                return result(False, "")
            if isinstance(path, (list, tuple)):
                path = path[0]

            doc = Document()
            section = doc.sections[0]
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.9)
            section.right_margin = Inches(0.9)

            normal = doc.styles["Normal"]
            normal.font.name = "Georgia"
            normal.font.size = Pt(12)

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(title)
            run.bold = True
            run.font.size = Pt(22)

            chapters = (book or {}).get("chapters") or []
            for index, chapter in enumerate(chapters):
                doc.add_page_break()
                h = doc.add_paragraph()
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                h_run = h.add_run(chapter.get("title") or f"{msg(lang, 'Глава', 'Chapter')} {index + 1}")
                h_run.bold = True
                h_run.font.size = Pt(16)

                text = chapter.get("content") or ""
                paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
                if not paragraphs:
                    continue
                for para in paragraphs:
                    pp = doc.add_paragraph()
                    pp.paragraph_format.first_line_indent = Inches(0.35)
                    pp.paragraph_format.line_spacing = 1.25
                    pp.paragraph_format.space_after = Pt(2)
                    pp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    pp.add_run(para)

            doc.save(path)
            return result(True)
        except Exception as e:
            return result(False, f"{msg(lang, 'Не удалось сохранить DOCX', 'Could not save DOCX')}: {e}")

    def export_txt(self, content, lang="ru"):
        lang = norm_lang(lang)
        return self._write_dialog(content, msg(lang, "книга.txt", "book.txt"),
                                  (msg(lang, "Текстовый файл (*.txt)", "Text file (*.txt)"),), encoding="utf-8", lang=lang)

    def _write_dialog(self, content, fname, ftypes, encoding="utf-8", lang="ru"):
        lang = norm_lang(lang)
        try:
            path = window.create_file_dialog(
                webview.SAVE_DIALOG, save_filename=fname, file_types=ftypes)
            if not path:
                return False
            if isinstance(path, (list, tuple)):
                path = path[0]
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return result(True)
        except Exception as e:
            return result(False, f"{msg(lang, 'Не удалось сохранить файл', 'Could not save file')}: {e}")

    # ---- резервные копии ----
    def export_backup(self, data, lang="ru"):
        lang = norm_lang(lang)
        return self._write_dialog(
            data,
            msg(lang, "Книжница-копия.json", "Knizhnitsa-backup.json"),
            (msg(lang, "Файл копии (*.json)", "Backup file (*.json)"),),
            lang=lang,
        )

    def import_backup(self, lang="ru"):
        lang = norm_lang(lang)
        try:
            paths = window.create_file_dialog(
                webview.OPEN_DIALOG, file_types=(msg(lang, "Файл копии (*.json)", "Backup file (*.json)"),))
            if not paths:
                return ""
            p = paths[0] if isinstance(paths, (list, tuple)) else paths
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""


def main():
    global window
    if not acquire_single_instance():
        return
    migrate_legacy_data()
    settings = load_initial_settings()
    with open(resource("ui.html"), "r", encoding="utf-8") as f:
        html = prepare_html(f.read(), settings)

    state = load_window_state()
    win_kwargs = dict(
        html=html,
        js_api=Api(),
        width=(state or {}).get("width", 1240),
        height=(state or {}).get("height", 860),
        min_size=(940, 620),
        background_color="#161618" if settings["theme"] == "dark" else "#f6f6f4",
    )
    if state and "x" in state and "y" in state:
        win_kwargs["x"] = state["x"]
        win_kwargs["y"] = state["y"]

    window = webview.create_window(APP_NAME, **win_kwargs)

    if ALWAYS_START_MAXIMIZED or (state and state.get("maximized")):
        window.events.shown += lambda: window.maximize()
    # Запоминаем размер/позицию на случай, если позже отключим автозапуск развёрнутым.
    window.events.resized += lambda *a: save_window_state()
    window.events.moved += lambda *a: save_window_state()
    window.events.closing += save_window_state

    webview.start()


if __name__ == "__main__":
    main()
