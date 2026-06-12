# Release Checklist

Use this checklist before publishing a new Книжница release. Use fake writing
samples only. Do not test with private manuscripts.

## Basic launch

- [ ] Install or run the candidate build on Windows.
- [ ] Open the app successfully.
- [ ] Confirm the main window renders correctly.
- [ ] Confirm existing local data loads from `%APPDATA%\Книжница`.
- [ ] Confirm Russian opens by default, then switch `RU / EN` and confirm the
  selected interface language persists after restart.

## Books

- [ ] Create a new book.
- [ ] Rename the book.
- [ ] Edit book metadata such as year, era, place, and synopsis.
- [ ] Switch between books without losing changes.

## Chapters and autosave

- [ ] Create a chapter.
- [ ] Rename a chapter.
- [ ] Write and edit chapter text.
- [ ] Leave the chapter and return to it.
- [ ] Confirm autosaved text is still present after app restart.
- [ ] Reorder chapters.

## Version history

- [ ] Create a manual chapter version.
- [ ] Trigger an automatic version by changing chapters.
- [ ] View saved versions.
- [ ] Restore a previous version.
- [ ] Confirm the current text is preserved safely during restore.

## Characters

- [ ] Create a character.
- [ ] Edit profile fields.
- [ ] Add and remove a character photo using fake/test images only.
- [ ] Add character aliases.
- [ ] Confirm character mentions are found in chapter text.
- [ ] Add and edit character links/map relationships.

## Plan

- [ ] Open the book plan.
- [ ] Edit chapter status.
- [ ] Edit chapter summary.
- [ ] Edit chapter notes.
- [ ] Confirm plan changes appear in search.

## Search

- [ ] Search by book title.
- [ ] Search by chapter title and text.
- [ ] Search by character name and aliases.
- [ ] Search by plan text.
- [ ] Open a search result and confirm it navigates to the right item.

## Trash

- [ ] Move a chapter to trash.
- [ ] Restore the chapter.
- [ ] Move a character to trash.
- [ ] Restore the character.
- [ ] Move a book to trash.
- [ ] Restore the book.
- [ ] Permanently remove only fake/test data.

## Export

- [ ] Export a book to `.docx`.
- [ ] Open the `.docx` and confirm title, chapters, and text are present.
- [ ] Export a book to `.txt`.
- [ ] Open the `.txt` and confirm readable UTF-8 text.
- [ ] Confirm export does not modify the local library.

## Backups

- [ ] Create a manual backup.
- [ ] Confirm backup appears in `%APPDATA%\Книжница\Резервные копии`.
- [ ] Import a backup made from fake/test data.
- [ ] Confirm the app creates a safety backup before import.
- [ ] Confirm old backups are pruned without deleting the active library.

## Installer and update

- [ ] Build the installer with Inno Setup.
- [ ] Install the app for the current Windows user.
- [ ] Confirm Start Menu and desktop shortcuts are created.
- [ ] Launch the installed app.
- [ ] Install the new version over the previous version.
- [ ] Confirm the updater closes the running app if needed.
- [ ] Confirm existing user data in `%APPDATA%\Книжница` remains after update.
- [ ] Uninstall the app.
- [ ] Confirm user data in `%APPDATA%\Книжница` is not deleted by uninstall.

## Release publication

- [ ] Confirm README, SECURITY, CONTRIBUTING, roadmap, and this checklist are up
  to date.
- [ ] Confirm no private manuscripts, backups, tokens, keys, or local-only files
  are staged.
- [ ] Create a GitHub release with clear notes.
- [ ] Attach the Windows installer.
- [ ] Download the release asset once and confirm it is the expected installer.
