import sys
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import main  # noqa: E402


class ClipboardApiTests(unittest.TestCase):
    def test_api_reads_unicode_text(self):
        with mock.patch.object(main, "read_clipboard_text", return_value="Текст из буфера"):
            response = main.Api().clipboard_read_text("ru")

        self.assertTrue(response["ok"])
        self.assertEqual(response["text"], "Текст из буфера")

    def test_api_writes_unicode_text(self):
        with mock.patch.object(main, "write_clipboard_text") as write:
            response = main.Api().clipboard_write_text("Вставить меня", "ru")

        self.assertTrue(response["ok"])
        write.assert_called_once_with("Вставить меня")

    def test_api_returns_clear_error_when_clipboard_is_busy(self):
        with mock.patch.object(main, "read_clipboard_text", side_effect=OSError("busy")):
            response = main.Api().clipboard_read_text("ru")

        self.assertFalse(response["ok"])
        self.assertIn("буфер обмена", response["error"])


if __name__ == "__main__":
    unittest.main()
