# OpenAI Codex for OSS Application Notes

This document is a maintainer-facing draft for preparing an OpenAI Codex for
Open Source application. It should stay factual: Авторея is a new public
local-first desktop app for writers, not a project with proven large-scale
adoption.

## Why this project fits

Авторея is a Windows desktop app for writers who want to keep manuscripts,
chapters, characters, plans, backups, and exports on their own computer. The
project is public, MIT-licensed, and intentionally local-first: no accounts, no
cloud sync, and no default upload of manuscripts.

The repository is a good candidate for Codex-assisted open-source maintenance
because it has clear user value, a privacy-sensitive domain, and practical
maintenance work that benefits from careful code review:

- local data handling and backup safety;
- DOCX/TXT export correctness;
- Windows installer and update behavior;
- WebView/Python bridge hardening;
- documentation and release process improvements;
- automated tests for the most important local workflows.

## Maintainer Work

Expected maintainer work includes:

- release management: build verification, installer packaging, release notes,
  and release asset checks;
- issue triage: reproduce bugs with fake writing samples, label security or
  data-loss risks, and keep public issues free of private manuscripts;
- security review: inspect local storage, backups, exports, installer behavior,
  and the WebView/Python bridge;
- documentation: keep README, SECURITY, CONTRIBUTING, roadmap, and release
  checklist current;
- packaging: keep PyInstaller and Inno Setup workflows understandable and
  reproducible.

## Security Angle

The app works with private creative material. Security review matters because a
bug can expose, corrupt, overwrite, or unexpectedly remove user writing. Important
areas:

- local manuscript storage in `%APPDATA%\Авторея\library.json`;
- backup creation, pruning, import, and restore behavior;
- export of private text to Word and TXT files;
- Windows installer update/uninstall behavior;
- file dialogs for images, backups, and exports;
- WebView/Python bridge boundaries exposed through `pywebview`.

The goal is not to add cloud features. The goal is to keep the app transparent,
local-first, and safer for writers.

## Draft Application Fields

### Describe your role

I am the maintainer of Авторея, a public MIT-licensed local-first Windows
desktop app for writers. I manage the repository, releases, installer packaging,
documentation, issue triage, and the security-sensitive areas around local
manuscript storage, backups, export, and the WebView/Python bridge.

### Why does this repository qualify?

Авторея is an open-source desktop tool for writers. It is intentionally
local-first: it works without accounts, without cloud sync, and keeps manuscripts
on the user's own Windows computer. The repository is public, MIT-licensed, has a
release with a Windows installer, and includes README, SECURITY, CONTRIBUTING,
roadmap, release checklist, and public issues that describe the next maintenance
work.

The project is new and honest about its current state. It does not claim broad
adoption. It is a practical open-source app with clear user value and a concrete
maintenance roadmap.

### Why does your project need Codex Security?

The app handles private manuscripts, character notes, plans, local backups, and
exported files. A security or reliability bug could expose private writing,
corrupt local data, create unsafe backups, mishandle exports, or make the
Windows installer unsafe during update/uninstall. Codex Security would help
review local storage, backup/import behavior, export paths, installer behavior,
and the WebView/Python bridge.

### How will you use API credits?

API credits would be used for maintainer work, not for uploading user
manuscripts from the app. Planned uses include:

- generating and reviewing tests for local data handling and exports;
- security-focused review of the WebView/Python bridge and file operations;
- issue triage and reproduction planning with fake sample data;
- documentation improvements for users and contributors;
- release checklist and packaging review.

### Anything else

Авторея is built around a simple privacy promise: writers should be able to use
the app without an account and without sending manuscripts to a server. The
project is still early, which makes this a good moment to add security review,
tests, and maintainer discipline before the codebase grows.
