# Contributing

Спасибо за интерес к Авторее. Это небольшое local-first Windows-приложение для
писателей, поэтому главный принцип простой: не рисковать пользовательскими
рукописями и локальными данными.

## Set up

Требуется Windows and Python 3.

```powershell
cd app
python -m pip install -r requirements.txt
```

## Run locally

```powershell
cd app
python main.py
```

## Build

Build the desktop app:

```powershell
cd app
python -m PyInstaller --noconfirm --clean .\Авторея.spec
```

Build the Windows installer with Inno Setup 6:

```powershell
cd app
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

## Check changes

There are no automated tests yet. For now, use the manual release checklist:

- open the app;
- create and edit a book;
- create chapters and check autosave;
- check version history;
- add and edit characters;
- edit the chapter plan;
- search across content;
- move items to trash and restore them;
- export `.docx` and `.txt`;
- create and import a backup;
- install/update with the installer;
- confirm user data in `%APPDATA%\Авторея` is not deleted by update or
  uninstall.

Full checklist: [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

## Issues

Good issues are specific and safe:

- describe what happened and what you expected;
- include app version, Windows version, and how the app was installed;
- use fake sample text instead of real manuscripts;
- do not attach private library files, backups, exports, tokens, or personal
  data.

## Pull requests

Pull requests should be small and easy to review:

- explain the user-visible change;
- mention any data migration or file format impact;
- update README/docs when behavior changes;
- say which manual checks were completed;
- avoid unrelated formatting or cleanup in the same PR.

## Maintainer style

The project is maintained conservatively. Changes that touch local storage,
backups, export, installer behavior, or the WebView/Python bridge should be
reviewed with extra care.
