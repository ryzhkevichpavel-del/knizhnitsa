# Privacy policy

Effective date: 12 August 2026

Книжница is a local-first Windows application for writers. It has no user
accounts, advertising, analytics, cloud synchronization, or telemetry operated
by the Книжница project.

## Data stored on the computer

Books, chapters, plans, character information, settings, exports, and backups
are stored locally on the user's computer. The project does not receive or
store these files.

## Network access

By default, after each application launch, Книжница makes one delayed HTTPS
request to the public GitHub Releases API to check whether a newer version is
available. The user can disable these automatic checks in the application
settings and still run a manual check when needed. The request contains the
application name and installed version in its User-Agent header. Like any HTTPS
request, GitHub also receives ordinary network metadata, including the user's IP
address.

The update check does not transmit manuscripts, book or chapter titles,
character information, plans, file names, local paths, settings, or backup
contents. It does not download or install an update automatically. When an
update exists, the application shows a button; GitHub Releases opens only after
the user clicks it.

If the computer is offline or GitHub is unavailable, Книжница continues to work
normally. The latest update-check result may be cached locally in
`%APPDATA%\Книжница\update-check.json`.

GitHub processes the update request under the
[GitHub General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

## Sharing data by user action

Книжница exports files only to a location selected by the user. If a user later
uploads an exported file, a manuscript, or a diagnostic example to another
service, that action and the receiving service's privacy terms are outside the
Книжница application.

## Questions

Privacy questions may be opened as a
[GitHub issue](https://github.com/ryzhkevichpavel-del/knizhnitsa/issues) without
attaching manuscripts, library files, backups, or other private information.
