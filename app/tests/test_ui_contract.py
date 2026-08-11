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

    def test_working_text_views_use_available_width(self):
        self.assertIn(".wrap{--page-pad:", self.html)
        self.assertIn(";max-width:none", self.html)
        self.assertIn(".chapter-wrap{max-width:none}", self.html)
        self.assertIn(".character-wrap{max-width:none}", self.html)
        self.assertIn(".plan-document-editor{max-width:none", self.html)

    def test_lore_markdown_is_escaped_before_formatting(self):
        self.assertIn("function renderLoreMarkdown", self.html)
        self.assertIn('let safe=escapeHtml(String(value||""))', self.html)
        self.assertIn('safe=safe.replace(/\\*\\*([^*\\n]+)\\*\\*/g,"<strong>$1</strong>")', self.html)
        self.assertIn('html.push("<hr>")', self.html)

    def test_lore_reader_has_compact_header_outline_and_contextual_count(self):
        self.assertIn('class="wrap lore-wrap"', self.html)
        self.assertIn('class="lore-pagehead"', self.html)
        self.assertIn('class="lore-heading lore-view-heading"', self.html)
        self.assertIn('.lore-view-heading .badge{height:28px;padding:0 12px;line-height:1;align-items:center;justify-content:center;transform:translateY(3px)}', self.html)
        self.assertIn('<span class="badge">${escapeHtml(labelEnum("lore",item.type||"Заметка"))}</span>', self.html)
        self.assertNotIn('<div class="lore-meta"><span class="badge">', self.html)
        self.assertIn('function loreOutline', self.html)
        self.assertIn('class="lore-document"', self.html)
        self.assertIn('t("inNote")', self.html)
        self.assertNotIn('style="width:126px;aspect-ratio:1"', self.html)

    def test_lore_editor_offers_basic_formatting_controls(self):
        for command in ("heading", "bold", "italic", "list", "divider"):
            self.assertIn(f"applyLoreFormat('{command}')", self.html)
        self.assertIn('id="loreDetails"', self.html)
        self.assertNotIn('class="format-divider"', self.html)
        self.assertNotIn('class="format-hint"', self.html)
        self.assertNotIn('<div class="lore-meta"><span>${t("formatting")}</span></div>', self.html)
        self.assertNotIn('formatting:["Оформление","Formatting"]', self.html)

    def test_new_lore_opens_the_full_editor_without_a_title_prompt(self):
        self.assertIn("function addLore(){", self.html)
        self.assertIn('const item={id:uid(),type:"Заметка",title:""', self.html)
        self.assertNotIn('const title=await openInput({title:t("newLore")', self.html)
        self.assertIn('if(titleInput&&!item.title.trim()) queueMicrotask(()=>titleInput.focus())', self.html)

    def test_truncated_sidebar_labels_expose_the_full_name(self):
        self.assertIn('class="label" title="${escapeAttr(titleOrFallback(item.title))}"', self.html)

    def test_character_map_keeps_long_names_and_roles_inside_cards(self):
        self.assertIn('.map-copy{display:block;flex:1;min-width:0;overflow:hidden}', self.html)
        self.assertIn('.map-role{display:block;width:100%;', self.html)
        self.assertIn('class="map-name" title="${escapeAttr(nameOrFallback(c.name))}"', self.html)
        self.assertIn('class="map-role" title="${escapeAttr(roleOrFallback(c.role))}"', self.html)
        self.assertNotIn('<span style="min-width:0"><span class="map-name">', self.html)

    def test_sidebar_actions_are_consistent_for_chapters_characters_and_lore(self):
        self.assertIn("async function renameCharacter(id,ev)", self.html)
        self.assertIn("async function renameLore(id,ev)", self.html)
        self.assertIn("onclick=\"renameCharacter('${c.id}',event)\"", self.html)
        self.assertIn("onclick=\"deleteCharacter('${c.id}',event)\"", self.html)
        self.assertIn("onclick=\"renameLore('${item.id}',event)\"", self.html)
        self.assertIn("onclick=\"deleteLore('${item.id}',event)\"", self.html)
        self.assertIn('if(route.view==="lore"&&route.itemId===id)', self.html)

    def test_book_overview_has_clear_editing_controls_without_duplicate_actions(self):
        self.assertIn('<div class="wrap overview-wrap">', self.html)
        self.assertNotIn('<h1 class="overview-heading">', self.html)
        self.assertIn('<label for="ovTitle">${t("bookTitle")}</label>', self.html)
        self.assertIn('class="overview-title-input" id="ovTitle"', self.html)
        self.assertIn('<label for="ovAuthor">${t("author")}</label>', self.html)
        self.assertIn('class="overview-title-input" id="ovAuthor"', self.html)
        self.assertIn('bind("ovAuthor","author",false)', self.html)
        self.assertIn('function eraSelect(b)', self.html)
        self.assertIn('document.getElementById("ovEra").addEventListener("change",onEraSelect)', self.html)
        self.assertNotIn('class="side-book ', self.html)
        overview=self.html.split('function renderOverview(main,b){',1)[1].split('/* ============ ВЕРХНЯЯ ПАНЕЛЬ',1)[0]
        for duplicate_action in ('onclick="addChapter()"','onclick="openPlan()"','onclick="addLore()"','onclick="openExport()"','onclick="openPreview()"'):
            self.assertNotIn(duplicate_action, overview)

    def test_book_layout_uses_writer_presets_and_real_pages(self):
        self.assertIn('preview:["Макет книги","Book layout"]', self.html)
        self.assertIn('const BOOK_FORMATS={', self.html)
        self.assertIn('compact:{width:130,height:200', self.html)
        self.assertIn('standard:{width:145,height:215', self.html)
        self.assertIn('a5:{width:148,height:210', self.html)
        self.assertIn('function renderPreviewPages()', self.html)
        self.assertIn('function fitPreviewParagraph(body,text,continued=false)', self.html)
        self.assertIn('function previewOverflows(body)', self.html)
        self.assertIn('number.className="pv-page-number"', self.html)
        self.assertIn('author.textContent=book.author.trim()', self.html)
        self.assertIn('document.fonts&&document.fonts.ready', self.html)
        self.assertIn('count.textContent=previewPageCountLabel(pageNumber)', self.html)
        self.assertIn('.pv-title-page .pv-page-body{width:100%', self.html)
        self.assertIn('.pv-title-page{padding:24mm 21mm;text-align:center}', self.html)
        self.assertIn('.pv-title-page .pv-book-title{width:100%', self.html)
        self.assertNotIn('.pv-pages.spread .pv-title-sheet{grid-column:1 / -1', self.html)
        self.assertNotIn('.pv-title-page .pv-book-title{font:700 24pt/1.25 "Georgia",serif;max-width:90%;overflow-wrap:anywhere}', self.html)

        preview=self.html.split('/* ============ ПРЕДПРОСМОТР ============ */',1)[1].split('/* ============ РЕЗЕРВНЫЕ КОПИИ ============ */',1)[0]
        self.assertNotIn('WORDS_PER_PAGE', preview)
        self.assertNotIn("'≈'", preview)
        self.assertNotIn('export_pdf', preview.lower())

    def test_default_author_is_reused_but_can_be_overridden_per_book(self):
        self.assertIn('defaultAuthor:["Автор новых книг","Default author"]', self.html)
        self.assertIn('function setDefaultAuthor(value)', self.html)
        self.assertIn('id="defaultAuthorInput"', self.html)
        self.assertIn('function openNewBookForm()', self.html)
        self.assertIn('value="${escapeAttr(defaultAuthor)}"', self.html)
        self.assertIn('author,previewFormat:"standard"', self.html)
        self.assertIn('if(!String(state.settings.defaultAuthor||"").trim()&&author) state.settings.defaultAuthor=author', self.html)


if __name__ == "__main__":
    unittest.main()
