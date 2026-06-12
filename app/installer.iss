; Установщик «Книжница» (Inno Setup).
; Собирает онедир-сборку из dist\Книжница в полноценную устанавливаемую программу:
; запись в «Установка и удаление программ», ярлыки в Пуске и на рабочем столе,
; установка для текущего пользователя (без пароля администратора).

#define AppName "Книжница"
#define AppVersion "1.0.1"
#define AppPublisher "Книжница"
#define AppExe "Книжница.exe"

[Setup]
AppId={{8B3F2A91-4D5E-4C7A-9B1F-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
; установка для пользователя — без UAC и пароля администратора
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; если приложение запущено — предложить закрыть его перед установкой
CloseApplications=yes
AppMutex=KnizhnitsaSingleInstance
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=Книжница-Setup
SetupIconFile=icon.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\Книжница\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
