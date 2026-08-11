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
import threading
from datetime import datetime

from windows_startup import (
    APP_USER_MODEL_ID,
    MUTEX_NAME,
    SingleInstance,
    StartupLog,
    StartupSplash,
    activate_process_window,
    set_process_app_user_model_id,
)

APP_NAME = "Книжница"
APP_VERSION = "1.1.0"
LEGACY_APP_NAMES = ("Пиши книгу",)
MAX_BACKUPS = 15
AUTO_BACKUP_INTERVAL = 10 * 60
ALWAYS_START_MAXIMIZED = True
webview = None
window = None
startup_log = None
startup_splash = None
single_instance = None
last_auto_backup = 0


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


DATA_DIR = data_dir()
DATA_FILE = os.path.join(DATA_DIR, "library.json")
BACKUP_DIR = os.path.join(DATA_DIR, "Резервные копии")
WINDOW_STATE_FILE = os.path.join(DATA_DIR, "window.json")


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


def _open_clipboard(attempts=8, delay=0.02):
    """Открыть системный буфер обмена, переждав короткую блокировку другим приложением."""
    user32 = ctypes.windll.user32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    for _ in range(attempts):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def read_clipboard_text():
    """Прочитать обычный Unicode-текст из буфера обмена Windows."""
    cf_unicode_text = 13
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
    user32.IsClipboardFormatAvailable.restype = ctypes.c_int
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int

    if not _open_clipboard():
        raise OSError("clipboard is busy")
    handle = None
    pointer = None
    try:
        if not user32.IsClipboardFormatAvailable(cf_unicode_text):
            return ""
        handle = user32.GetClipboardData(cf_unicode_text)
        if not handle:
            raise OSError("clipboard text is unavailable")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise OSError("clipboard text is locked")
        return ctypes.wstring_at(pointer)
    finally:
        if pointer and handle:
            kernel32.GlobalUnlock(handle)
        user32.CloseClipboard()


def write_clipboard_text(text):
    """Записать обычный Unicode-текст в буфер обмена Windows."""
    cf_unicode_text = 13
    gmem_moveable = 0x0002
    data = str(text or "").encode("utf-16-le") + b"\x00\x00"
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p

    handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not handle:
        raise OSError("clipboard allocation failed")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise OSError("clipboard allocation is locked")
    ctypes.memmove(pointer, data, len(data))
    kernel32.GlobalUnlock(handle)

    if not _open_clipboard():
        kernel32.GlobalFree(handle)
        raise OSError("clipboard is busy")
    transferred = False
    try:
        if not user32.EmptyClipboard():
            raise OSError("clipboard could not be cleared")
        if not user32.SetClipboardData(cf_unicode_text, handle):
            raise OSError("clipboard text could not be written")
        transferred = True
    finally:
        user32.CloseClipboard()
        if not transferred:
            kernel32.GlobalFree(handle)


def read_imported_text(path):
    """Извлечь обычный текст из поддерживаемого авторского документа."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        from docx import Document
        from docx.document import Document as DocumentObject
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        document = Document(path)
        blocks = []
        parent = document.element.body if isinstance(document, DocumentObject) else document._element
        for child in parent.iterchildren():
            if isinstance(child, CT_P):
                paragraph = Paragraph(child, document)
                text = paragraph.text.strip()
                if not text:
                    continue
                style_name = (paragraph.style.name if paragraph.style is not None else "").lower()
                numbering = (
                    (paragraph._p.pPr is not None and paragraph._p.pPr.numPr is not None)
                    or "list" in style_name
                    or "спис" in style_name
                )
                blocks.append(("• " if numbering else "") + text)
            elif isinstance(child, CT_Tbl):
                table = Table(child, document)
                rows = []
                for row in table.rows:
                    cells = [re.sub(r"\s+", " ", cell.text).strip() for cell in row.cells]
                    if any(cells):
                        rows.append(" | ".join(cells))
                if rows:
                    blocks.append("\n".join(rows))
        return "\n\n".join(blocks).strip()

    if ext not in (".txt", ".md"):
        raise ValueError("unsupported document type")
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return raw.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


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

    # ---- системный буфер обмена для меню правой кнопки ----
    def clipboard_read_text(self, lang="ru"):
        lang = norm_lang(lang)
        try:
            return {"ok": True, "error": "", "text": read_clipboard_text()}
        except Exception:
            return result(False, msg(lang, "Не удалось прочитать буфер обмена.", "Could not read the clipboard."))

    def clipboard_write_text(self, text, lang="ru"):
        lang = norm_lang(lang)
        try:
            write_clipboard_text(text)
            return result(True)
        except Exception:
            return result(False, msg(lang, "Не удалось записать текст в буфер обмена.", "Could not write to the clipboard."))

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

    # ---- импорт текста в открытую главу / план / арку ----
    def import_text_document(self, lang="ru"):
        lang = norm_lang(lang)
        try:
            paths = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=(
                    msg(lang, "Документы Word и текст (*.docx;*.txt;*.md)", "Word and text documents (*.docx;*.txt;*.md)"),
                    msg(lang, "Документ Word (*.docx)", "Word document (*.docx)"),
                    msg(lang, "Текстовый документ (*.txt;*.md)", "Text document (*.txt;*.md)"),
                ),
            )
            if not paths:
                return {"ok": False, "cancelled": True, "error": ""}
            path = paths[0] if isinstance(paths, (list, tuple)) else paths
            text = read_imported_text(path)
            return {
                "ok": True,
                "error": "",
                "name": os.path.basename(path),
                "text": text,
            }
        except ValueError:
            return result(False, msg(lang, "Поддерживаются только DOCX, TXT и MD.", "Only DOCX, TXT, and MD are supported."))
        except Exception as exc:
            return result(False, f"{msg(lang, 'Не удалось прочитать документ', 'Could not read the document')}: {exc}")

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
    global webview, window, startup_log, startup_splash, single_instance

    startup_log = StartupLog(DATA_DIR)
    app_id_ok = set_process_app_user_model_id(APP_USER_MODEL_ID)
    single_instance = SingleInstance(DATA_DIR, startup_log, mutex_name=MUTEX_NAME)
    role = single_instance.acquire()

    if role == "secondary":
        return
    if role == "error":
        ctypes.windll.user32.MessageBoxW(
            None,
            "Не удалось проверить уже запущенную Книжницу. Попробуйте ещё раз.",
            APP_NAME,
            0x10,
        )
        return

    startup_log.rotate_if_needed()
    startup_log.write(
        "python_entry",
        version=APP_VERSION,
        frozen=bool(getattr(sys, "frozen", False)),
        app_user_model_id=app_id_ok,
    )
    startup_log.write("instance_primary")

    window_ready = threading.Event()
    activation_pending = threading.Event()

    def request_window_activation():
        activation_pending.set()
        if window_ready.is_set():
            activate_process_window(os.getpid(), APP_NAME, logger=startup_log)

    single_instance.start_listener(request_window_activation)

    startup_splash = StartupSplash(resource("icon.ico"))
    splash_ok = startup_splash.start()
    startup_log.write("splash_shown", success=splash_ok)

    try:
        startup_log.write("webview_import_begin")
        import webview as webview_module

        webview = webview_module
        startup_log.write("webview_import_done")

        startup_log.write("data_migration_begin")
        migrate_legacy_data()
        startup_log.write("data_migration_done")

        settings = load_initial_settings()
        startup_log.write("html_prepare_begin")
        with open(resource("ui.html"), "r", encoding="utf-8") as f:
            html = prepare_html(f.read(), settings)
        startup_log.write("html_prepare_done")

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

        startup_log.write("create_window_begin")
        window = webview.create_window(APP_NAME, **win_kwargs)
        startup_log.write("create_window_done")

        def on_window_shown():
            startup_log.write("window_shown")
            window_ready.set()
            if startup_splash:
                startup_splash.stop()
            if ALWAYS_START_MAXIMIZED or (state and state.get("maximized")):
                window.maximize()
            if activation_pending.is_set():
                activate_process_window(os.getpid(), APP_NAME, logger=startup_log)

        def on_window_loaded():
            startup_log.write("window_loaded")

        def on_window_closing(*_):
            startup_log.write("window_closing")
            save_window_state()

        window.events.shown += on_window_shown
        window.events.loaded += on_window_loaded
        # Запоминаем размер/позицию на случай, если позже отключим автозапуск развёрнутым.
        window.events.resized += lambda *a: save_window_state()
        window.events.moved += lambda *a: save_window_state()
        window.events.closing += on_window_closing

        startup_log.write("webview_start_begin")
        webview.start()
        startup_log.write("webview_start_done")
    except Exception as exc:
        startup_log.write("fatal_error", error=type(exc).__name__, message=str(exc))
        if startup_splash:
            startup_splash.stop()
        ctypes.windll.user32.MessageBoxW(
            None,
            "Книжница не смогла запуститься. Подробности записаны в startup.log.",
            APP_NAME,
            0x10,
        )
        raise
    finally:
        if startup_splash:
            startup_splash.stop()
        if single_instance:
            single_instance.close()
        if startup_log:
            startup_log.write("shutdown")


if __name__ == "__main__":
    main()
