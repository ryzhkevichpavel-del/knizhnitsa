; Установщик «Авторея» (Inno Setup).
; Собирает онедир-сборку из dist\Авторея в полноценную устанавливаемую программу:
; запись в «Установка и удаление программ», ярлыки в Пуске и на рабочем столе,
; установка для текущего пользователя (без пароля администратора).

#define AppName "Авторея"
#define AppVersion "1.4.0"
#define AppPublisher "Авторея"
#define AppExe "Авторея.exe"
#define AppUserModelId "Avtoreya.Desktop"

[Setup]
AppId={{8B3F2A91-4D5E-4C7A-9B1F-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion=1.4.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Установщик приложения «Авторея»
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=© 2026 Авторея
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UsePreviousGroup=no
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
; установка для пользователя — без UAC и пароля администратора
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; если приложение запущено — предложить закрыть его перед установкой
CloseApplications=yes
AppMutex=Local\AvtoreyaSingleInstance,Local\KnizhnitsaSingleInstance
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=Avtoreya-Setup
SetupIconFile=icon.ico
#ifdef SignedBuild
SignTool=avtoreya
SignedUninstaller=yes
#endif

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[InstallDelete]
; Убираем только исполняемый файл и ярлыки прежнего названия. Пользовательские
; данные в %APPDATA% здесь никогда не затрагиваются.
Type: files; Name: "{app}\Книжница.exe"
Type: files; Name: "{autodesktop}\Книжница.lnk"
Type: files; Name: "{userprograms}\Книжница\Книжница.lnk"
Type: files; Name: "{userprograms}\Книжница\Удалить Книжница.lnk"
Type: files; Name: "{userprograms}\Книжница\Авторея.lnk"
Type: files; Name: "{userprograms}\Книжница\Удалить Авторея.lnk"
Type: files; Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Книжница.lnk"
Type: dirifempty; Name: "{userprograms}\Книжница"

[Files]
Source: "dist\Авторея\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "set_shortcut_app_id.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelId}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "{#AppUserModelId}"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\set_shortcut_app_id.ps1"" -ShortcutPath ""{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\{#AppName}.lnk"" -AppUserModelId ""{#AppUserModelId}"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
