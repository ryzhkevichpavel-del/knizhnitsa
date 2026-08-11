; Установщик «Книжница» (Inno Setup).
; Собирает онедир-сборку из dist\Книжница в полноценную устанавливаемую программу:
; запись в «Установка и удаление программ», ярлыки в Пуске и на рабочем столе,
; установка для текущего пользователя (без пароля администратора).

#define AppName "Книжница"
#define AppVersion "1.1.0"
#define AppPublisher "Книжница"
#define AppExe "Книжница.exe"
#define AppUserModelId "Knizhnitsa.Desktop"

[Setup]
AppId={{8B3F2A91-4D5E-4C7A-9B1F-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion=1.1.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Установщик приложения «Книжница»
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=© 2026 Книжница
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
; установка для пользователя — без UAC и пароля администратора
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; если приложение запущено — предложить закрыть его перед установкой
CloseApplications=yes
AppMutex=Local\KnizhnitsaSingleInstance
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=Книжница-Setup
SetupIconFile=icon.ico
#ifdef SignedBuild
SignTool=knizhnitsa
SignedUninstaller=yes
#endif

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\Книжница\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "set_shortcut_app_id.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelId}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "{#AppUserModelId}"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\set_shortcut_app_id.ps1"" -ShortcutPath ""{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\{#AppName}.lnk"" -AppUserModelId ""{#AppUserModelId}"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
