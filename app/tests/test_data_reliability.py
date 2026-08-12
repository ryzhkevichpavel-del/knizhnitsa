import json
import os
import tempfile
import unittest
from unittest import mock

import main


def library(title="Тест"):
    return json.dumps(
        {
            "books": [
                {
                    "title": title,
                    "chapters": [{"title": "Глава", "content": "Текст", "history": [{"text": "Черновик"}]}],
                    "characters": [{"name": "Герой"}],
                }
            ],
            "settings": {"lang": "ru"},
        },
        ensure_ascii=False,
    )


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


class DataReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = self.temporary.name
        self.patches = [
            mock.patch.object(main, "DATA_DIR", self.data_dir),
            mock.patch.object(main, "DATA_FILE", os.path.join(self.data_dir, "library.json")),
            mock.patch.object(main, "BACKUP_DIR", os.path.join(self.data_dir, "Резервные копии")),
            mock.patch.object(main, "WINDOW_STATE_FILE", os.path.join(self.data_dir, "window.json")),
            mock.patch.object(main, "UPDATE_CACHE_FILE", os.path.join(self.data_dir, "update-check.json")),
        ]
        for patch in self.patches:
            patch.start()
        main.last_auto_backup = 0
        self.api = main.Api()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)

    def test_missing_library_is_an_explicit_empty_success(self):
        response = self.api.load()
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"], "")
        self.assertFalse(response["recovery_available"])

    def test_save_load_flush_and_stats_are_structured(self):
        raw = library()
        saved = self.api.save(raw)
        loaded = self.api.load()
        flushed = self.api.flush_save(raw)

        self.assertTrue(saved["ok"])
        self.assertTrue(saved["changed"])
        self.assertEqual(loaded["data"], raw)
        self.assertEqual(loaded["stats"]["books"], 1)
        self.assertEqual(loaded["stats"]["chapters"], 1)
        self.assertEqual(loaded["stats"]["historyEntries"], 1)
        self.assertEqual(loaded["stats"]["bytes"], len(raw.encode("utf-8")))
        self.assertTrue(flushed["ok"])
        self.assertFalse(flushed["changed"])

    def test_unchanged_save_does_not_write_again(self):
        raw = library()
        self.assertTrue(self.api.save(raw)["ok"])
        with mock.patch.object(main, "atomic_write_text", wraps=main.atomic_write_text) as writer:
            response = self.api.save(raw)
        self.assertTrue(response["ok"])
        self.assertFalse(response["changed"])
        writer.assert_not_called()

    def test_invalid_json_is_rejected_without_touching_existing_file(self):
        original = library("Исходная")
        self.assertTrue(self.api.save(original)["ok"])
        response = self.api.save("{broken")
        self.assertFalse(response["ok"])
        self.assertEqual(main.read_text(main.DATA_FILE), original)

    def test_corrupt_main_reports_latest_valid_backup(self):
        self.write(main.DATA_FILE, "{broken")
        self.write(os.path.join(main.BACKUP_DIR, "01.json"), library("Исправная"))
        self.write(os.path.join(main.BACKUP_DIR, "02.json"), "also broken")
        os.utime(os.path.join(main.BACKUP_DIR, "02.json"), (200, 200))
        os.utime(os.path.join(main.BACKUP_DIR, "01.json"), (100, 100))

        response = self.api.load()
        recovered = self.api.recover_latest_backup()

        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], "library_invalid")
        self.assertTrue(response["recovery_available"])
        self.assertTrue(recovered["ok"])
        self.assertIn("Исправная", recovered["data"])
        self.assertTrue(self.api.load()["ok"])
        self.assertIn("Исправная", main.read_text(main.DATA_FILE))

    def test_newer_valid_tmp_is_offered_without_overwriting_main(self):
        current = library("Текущая")
        pending = library("Новая")
        self.write(main.DATA_FILE, current)
        self.write(main.DATA_FILE + ".tmp", pending)
        os.utime(main.DATA_FILE, (100, 100))
        os.utime(main.DATA_FILE + ".tmp", (200, 200))

        response = self.api.load()

        self.assertTrue(response["ok"])
        self.assertEqual(response["data"], current)
        self.assertTrue(response["recovery_available"])
        self.assertEqual(response["recovery_source"], "temporary")
        self.assertIn("Новая", self.api.recover_latest_backup()["data"])
        self.assertIn("Новая", main.read_text(main.DATA_FILE))

    def test_backups_are_deduplicated_and_pruned_to_fifteen(self):
        os.makedirs(main.BACKUP_DIR, exist_ok=True)
        first = main.create_backup_from_text(library("Одна"), "первая")
        duplicate = main.create_backup_from_text(library("Одна"), "повтор")
        self.assertTrue(first["ok"])
        self.assertTrue(duplicate["ok"])
        self.assertEqual(len(main.backup_files()), 1)

        def remove(path):
            os.remove(path)
            return True

        with mock.patch.object(main, "recycle_path", side_effect=remove):
            for index in range(20):
                response = main.create_backup_from_text(library(str(index)), str(index))
                self.assertTrue(response["ok"])
        self.assertEqual(len(main.backup_files()), main.MAX_BACKUPS)

    def test_legacy_migration_copies_valid_library_and_keeps_backup(self):
        legacy_dir = os.path.join(self.data_dir, "Старая версия")
        old_file = os.path.join(legacy_dir, "library.json")
        self.write(old_file, library("Старая книга"))
        with mock.patch.object(main, "LEGACY_APP_NAMES", ("old",)), mock.patch.object(
            main, "appdata_dir", return_value=legacy_dir
        ):
            response = main.migrate_legacy_data()
        self.assertTrue(response["ok"])
        self.assertTrue(response["migrated"])
        self.assertIn("Старая книга", main.read_text(main.DATA_FILE))
        self.assertGreaterEqual(len(main.backup_files()), 1)

    def test_brand_migration_preserves_legacy_backup_files(self):
        legacy_dir = os.path.join(self.data_dir, "Книжница")
        old_file = os.path.join(legacy_dir, "library.json")
        old_backup = os.path.join(legacy_dir, "Резервные копии", "2026-01-01 - старая.json")
        self.write(old_file, library("Текущая старая книга"))
        self.write(old_backup, library("Более ранняя книга"))

        with mock.patch.object(main, "LEGACY_APP_NAMES", ("Книжница",)), mock.patch.object(
            main, "appdata_dir", return_value=legacy_dir
        ):
            response = main.migrate_legacy_data()

        self.assertTrue(response["ok"])
        self.assertTrue(response["migrated"])
        self.assertTrue(os.path.exists(old_backup))
        self.assertTrue(os.path.exists(os.path.join(main.BACKUP_DIR, os.path.basename(old_backup))))
        self.assertIn("Текущая старая книга", main.read_text(main.DATA_FILE))

    def test_default_brand_migration_includes_knizhnitsa(self):
        self.assertIn("Книжница", main.LEGACY_APP_NAMES)

    def test_legacy_migration_never_overwrites_a_corrupt_current_file(self):
        self.write(main.DATA_FILE, "{damaged")
        legacy_dir = os.path.join(self.data_dir, "Старая версия")
        self.write(os.path.join(legacy_dir, "library.json"), library("Старая книга"))
        with mock.patch.object(main, "LEGACY_APP_NAMES", ("old",)), mock.patch.object(
            main, "appdata_dir", return_value=legacy_dir
        ):
            response = main.migrate_legacy_data()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], "current_file_invalid")
        self.assertEqual(main.read_text(main.DATA_FILE), "{damaged")

    def test_empty_current_library_does_not_restore_old_deleted_books(self):
        self.write(main.DATA_FILE, json.dumps({"books": [], "settings": {"lang": "ru"}}))
        legacy_dir = os.path.join(self.data_dir, "Старая версия")
        self.write(os.path.join(legacy_dir, "library.json"), library("Удалённая старая книга"))
        with mock.patch.object(main, "LEGACY_APP_NAMES", ("old",)), mock.patch.object(
            main, "appdata_dir", return_value=legacy_dir
        ):
            response = main.migrate_legacy_data()
        self.assertTrue(response["ok"])
        self.assertFalse(response["migrated"])
        self.assertNotIn("Удалённая старая книга", main.read_text(main.DATA_FILE))

    def test_import_backup_returns_data_cancel_and_read_errors_explicitly(self):
        class FakeWebview:
            OPEN_DIALOG = 1

        class FakeWindow:
            def __init__(self, selected):
                self.selected = selected

            def create_file_dialog(self, *_args, **_kwargs):
                return self.selected

        valid = os.path.join(self.data_dir, "valid.json")
        invalid = os.path.join(self.data_dir, "invalid.json")
        self.write(valid, library())
        self.write(invalid, "not json")
        with mock.patch.object(main, "webview", FakeWebview), mock.patch.object(main, "window", FakeWindow([valid])):
            ok = self.api.import_backup()
        with mock.patch.object(main, "webview", FakeWebview), mock.patch.object(main, "window", FakeWindow([])):
            cancelled = self.api.import_backup()
        with mock.patch.object(main, "webview", FakeWebview), mock.patch.object(main, "window", FakeWindow([invalid])):
            broken = self.api.import_backup()

        self.assertTrue(ok["ok"])
        self.assertIn("books", ok["data"])
        self.assertTrue(cancelled["cancelled"])
        self.assertFalse(broken["ok"])
        self.assertIn("повреждён", broken["error"])

    def test_app_info_and_update_check_have_stable_contract(self):
        info = self.api.app_info()
        with mock.patch.object(
            main.urllib.request,
            "urlopen",
            return_value=FakeResponse({"tag_name": "v9.0.0", "html_url": "https://example.test/release"}),
        ):
            update = self.api.check_for_updates()

        self.assertEqual(info["version"], main.APP_VERSION)
        self.assertTrue(update["ok"])
        self.assertEqual(update["current_version"], main.APP_VERSION)
        self.assertEqual(update["latest_version"], "9.0.0")
        self.assertTrue(update["update_available"])
        self.assertEqual(update["url"], "https://example.test/release")

    def test_update_check_failure_is_user_visible(self):
        with mock.patch.object(main.urllib.request, "urlopen", side_effect=OSError("offline")):
            response = self.api.check_for_updates("ru")
        self.assertFalse(response["ok"])
        self.assertEqual(response["current_version"], main.APP_VERSION)
        self.assertIn("Не удалось", response["error"])

    def test_background_update_check_requests_once_on_every_launch(self):
        self.write(
            main.UPDATE_CACHE_FILE,
            json.dumps({"checked_at": main.time.time(), "latest_version": "9.0.0", "url": "https://github.com/example/release"}),
        )
        with mock.patch.object(
            main.urllib.request,
            "urlopen",
            return_value=FakeResponse({"tag_name": "v9.0.0", "html_url": "https://github.com/example/release"}),
        ) as opener:
            response = self.api.check_for_updates("ru", False)
        self.assertTrue(response["ok"])
        self.assertTrue(response["update_available"])
        self.assertEqual(response["source"], "network")
        opener.assert_called_once()

    def test_background_update_check_refreshes_stale_cache(self):
        self.write(
            main.UPDATE_CACHE_FILE,
            json.dumps({"checked_at": 1, "latest_version": "1.0.0", "url": "https://github.com/example/old"}),
        )
        with mock.patch.object(
            main.urllib.request,
            "urlopen",
            return_value=FakeResponse({"tag_name": "v9.0.0", "html_url": "https://github.com/example/new"}),
        ) as opener:
            response = self.api.check_for_updates("ru", False)
        self.assertTrue(response["ok"])
        self.assertEqual(response["source"], "network")
        self.assertEqual(response["latest_version"], "9.0.0")
        opener.assert_called_once()

    def test_background_update_check_reuses_etag_when_release_is_unchanged(self):
        self.write(
            main.UPDATE_CACHE_FILE,
            json.dumps(
                {
                    "checked_at": 1,
                    "latest_version": "9.0.0",
                    "url": "https://github.com/example/release",
                    "etag": '"release-9"',
                }
            ),
        )

        def unchanged(request, timeout):
            self.assertEqual(request.get_header("If-none-match"), '"release-9"')
            self.assertEqual(timeout, main.UPDATE_CHECK_TIMEOUT)
            raise main.urllib.error.HTTPError(request.full_url, 304, "Not Modified", None, None)

        with mock.patch.object(main.urllib.request, "urlopen", side_effect=unchanged) as opener:
            response = self.api.check_for_updates("ru", False)
        self.assertTrue(response["ok"])
        self.assertEqual(response["source"], "not_modified")
        self.assertTrue(response["update_available"])
        opener.assert_called_once()

    def test_external_links_are_limited_to_https_github(self):
        with mock.patch.object(main.webbrowser, "open", return_value=True) as opener:
            allowed = self.api.open_external("https://github.com/ryzhkevichpavel-del/avtoreya/releases/latest")
            blocked = self.api.open_external("https://example.test/not-allowed")
        self.assertTrue(allowed["ok"])
        self.assertFalse(blocked["ok"])
        opener.assert_called_once()


if __name__ == "__main__":
    unittest.main()
