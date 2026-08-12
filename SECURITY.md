# Security Policy

Авторея works with private writing material: drafts, book plans, character
notes, exports, and local backups. Please treat every example file as sensitive.

## What not to post publicly

Do not attach or paste any of the following into public GitHub issues, pull
requests, screenshots, or logs:

- real manuscripts, drafts, chapter text, book plans, or character notes;
- `%APPDATA%\Авторея\library.json`;
- files from `%APPDATA%\Авторея\Резервные копии`;
- exported `.docx` or `.txt` files containing private text;
- personal names, emails, phone numbers, addresses, tokens, keys, or passwords.

If you need to show a problem, use a tiny fake example that contains no real
private writing.

## Reporting a security problem

If the repository has GitHub private vulnerability reporting enabled, please use
that first.

If it is not available, open a public issue with only a high-level description,
for example: "Possible unsafe file export path". Do not include private files or
step-by-step exploit details in the public issue. The maintainer can then choose
a safer follow-up channel.

## Important security areas

Security-sensitive areas in this project include:

- local library storage in `%APPDATA%\Авторея`;
- local backup creation, pruning, import, and restore behavior;
- Word and TXT export paths and generated files;
- the Windows installer and update/uninstall behavior;
- the WebView/Python bridge exposed through `pywebview`;
- file dialogs for image import, backup import, and export.

## Supported versions

Security fixes are expected to target the latest public release unless the
maintainer states otherwise.

## Data handling principle

The app should stay local-first: no accounts, no cloud sync, and no uploading
manuscripts to a server by default.
