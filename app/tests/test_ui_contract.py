import unittest
from pathlib import Path


UI = Path(__file__).resolve().parents[1] / "ui.html"


class UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")

    def test_load_failure_is_visible_and_recoverable(self):
        self.assertIn("function decodedLoadResult", self.html)
        self.assertIn("showLoadFailure(result)", self.html)
        self.assertIn("recover_latest_backup", self.html)

    def test_pending_state_can_be_flushed_before_close(self):
        self.assertIn("window.knizhnitsaBeforeClose=function()", self.html)
        self.assertIn('window.addEventListener("beforeunload"', self.html)
        self.assertIn("flushPendingSave()", self.html)

    def test_save_status_is_global_and_persistent(self):
        self.assertIn('id="globalSaveStatus"', self.html)
        self.assertIn('className="global-save-status error"', self.html)
        self.assertIn('role="status" aria-live="polite"', self.html)
        self.assertNotIn("const t=Date.now()", self.html)

    def test_context_menu_supports_editable_and_selected_read_only_text(self):
        self.assertIn("function selectableTextTarget", self.html)
        for command in ("undo", "redo", "cut", "copy", "paste", "delete", "selectAll"):
            self.assertIn(f'data-command="{command}"', self.html)
        self.assertIn('toast(t("clipboardEmpty"))', self.html)

    def test_dialogs_have_keyboard_and_focus_management(self):
        self.assertIn('role="dialog" aria-modal="true"', self.html)
        self.assertIn("function requestCloseModal", self.html)
        self.assertIn('if(e.key==="Tab"&&dialog)', self.html)
        self.assertIn('if(document.querySelector(".modal"))', self.html)

    def test_clickable_non_buttons_get_keyboard_support(self):
        self.assertIn("function enhanceInteractiveControls", self.html)
        self.assertIn('el.setAttribute("role","button")', self.html)
        self.assertIn('e.key!=="Enter"&&e.key!==" "', self.html)

    def test_chapters_have_keyboard_reorder_buttons(self):
        self.assertIn('aria-label="${t("moveUp")}"', self.html)
        self.assertIn('aria-label="${t("moveDown")}"', self.html)

    def test_update_check_is_user_initiated(self):
        self.assertIn('id="checkUpdatesButton" onclick="checkForUpdates()"', self.html)
        self.assertIn("a.check_for_updates(lang())", self.html)
        self.assertNotIn("setInterval(checkForUpdates", self.html)


if __name__ == "__main__":
    unittest.main()
