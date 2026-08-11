import os
import tempfile
import unittest
from unittest import mock

from docx import Document

import main


class ExportStructureTests(unittest.TestCase):
    def setUp(self):
        self.book = {
            "title": "Тестовая книга",
            "chapters": [
                {"title": "Первая глава", "content": "Первый абзац.\nПродолжение строки.\n\nВторой абзац."},
                {"title": "", "content": "Финал."},
            ],
        }

    def test_txt_contains_book_and_chapter_structure(self):
        text = main.build_book_txt(self.book, "ru")
        self.assertTrue(text.startswith("Тестовая книга\n\nПервая глава"))
        self.assertIn("Первый абзац.\nПродолжение строки.\n\nВторой абзац.", text)
        self.assertIn("\n\nГлава 2\n\nФинал.", text)
        self.assertTrue(text.endswith("\n"))

    def test_docx_preserves_title_headings_paragraphs_and_line_break(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "book.docx")
            main.write_book_docx(self.book, path, "ru")
            document = Document(path)

        texts = [paragraph.text for paragraph in document.paragraphs]
        self.assertEqual(texts[0], "Тестовая книга")
        self.assertIn("Первая глава", texts)
        self.assertIn("Первый абзац.\nПродолжение строки.", texts)
        self.assertIn("Второй абзац.", texts)
        self.assertIn("Глава 2", texts)
        self.assertIn("Финал.", texts)

    def test_export_txt_accepts_old_string_and_new_book_object(self):
        api = main.Api()
        with mock.patch.object(api, "_write_dialog", return_value={"ok": True}) as writer:
            old_response = api.export_txt("Готовый текст", "ru")
            old_content = writer.call_args.args[0]
            new_response = api.export_txt(self.book, "ru")
            new_content = writer.call_args.args[0]

        self.assertTrue(old_response["ok"])
        self.assertEqual(old_content, "Готовый текст")
        self.assertTrue(new_response["ok"])
        self.assertIn("Тестовая книга", new_content)
        self.assertIn("Первая глава", new_content)


if __name__ == "__main__":
    unittest.main()
