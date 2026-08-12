# Roadmap

This is a practical maintenance plan, not a promise of dates. The goal is to
keep Авторея safe for local writing work and easier to review as an open-source
project.

## Near-term maintenance

- Extend automated tests for local library data handling and recovery failures.
- Extend regression tests for unusual `.docx` and `.txt` documents.
- Keep backup creation, pruning, import, and restore safety under regression tests.
- Keep the automated and manual release verification process current.

## Security and reliability

- Review the `pywebview` WebView/Python bridge boundaries.
- Keep local storage behavior clear and predictable.
- Check installer update/uninstall behavior against user data loss.
- Evaluate a publicly trusted Windows code-signing certificate if release
  adoption justifies its recurring cost. Unsigned releases must remain clearly
  labelled in the meantime.

## Documentation

- Improve user-facing documentation for installation, backups, exports, and data
  location.
- Keep maintainer documentation current when build or release steps change.
- Expand troubleshooting notes when new repeatable Windows problems are found.

## Tests to add first

- Loading, saving, and migrating `library.json`.
- Backup naming, duplicate detection, pruning, and restore/import safety.
- DOCX export structure for title, chapters, and paragraphs.
- TXT export encoding and chapter ordering.

## Completed foundations

- Exact versions are pinned for the tested Windows/Python dependency chain.
- Loading, saving, migration, backup pruning/recovery, and DOCX/TXT structure
  have isolated automated regression tests.
- GitHub Actions compiles all Python sources, checks UI JavaScript, runs unit
  tests, and performs a PyInstaller build smoke test.
- One PowerShell 5.1/7-compatible release command supports explicit signed and
  unsigned modes and always creates `Avtoreya-Setup.exe`.
- Manual release and Windows troubleshooting instructions are documented.
