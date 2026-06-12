# Roadmap

This is a practical maintenance plan, not a promise of dates. The goal is to
keep Книжница safe for local writing work and easier to review as an open-source
project.

## Near-term maintenance

- Add automated tests for local library data handling.
- Add regression tests for `.docx` and `.txt` export.
- Review backup creation, pruning, import, and restore safety.
- Document the manual release verification process.

## Security and reliability

- Review the `pywebview` WebView/Python bridge boundaries.
- Keep local storage behavior clear and predictable.
- Check installer update/uninstall behavior against user data loss.
- Explore Windows installer code signing to reduce SmartScreen friction.

## Documentation

- Improve user-facing documentation for installation, backups, exports, and data
  location.
- Keep maintainer documentation current when build or release steps change.
- Add clearer troubleshooting notes for common Windows installation warnings.

## Tests to add first

- Loading, saving, and migrating `library.json`.
- Backup naming, duplicate detection, pruning, and restore/import safety.
- DOCX export structure for title, chapters, and paragraphs.
- TXT export encoding and chapter ordering.
