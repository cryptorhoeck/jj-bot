; JJ-Bot Installer Script (Inno Setup)
; Creates a professional Windows installer

#define AppName "JJ-Bot Trading System"
#define AppVersion "1.0.0"
#define AppPublisher "JJ-Bot"
#define AppURL "https://github.com/cryptorhoeck/jj-bot"

[Setup]
AppId={{8F3D7E2A-9B4C-4A1D-8E5F-6C7D8E9F0A1B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\JJ-Bot
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=JJ-Bot-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start JJ-Bot automatically when Windows starts"; GroupDescription: "Auto-start:"; Flags: checked

[Files]
; Main application files
Source: "jj_bot_tray.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "glue\*"; DestDir: "{app}\glue"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "services\*"; DestDir: "{app}\services"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dashboard\*"; DestDir: "{app}\dashboard"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "tests\*"; DestDir: "{app}\tests"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\venv\Scripts\pythonw.exe"; Parameters: """{app}\jj_bot_tray.py"""; WorkingDir: "{app}"
Name: "{group}\Open Dashboard"; Filename: "http://localhost:5173"
Name: "{group}\API Documentation"; Filename: "http://127.0.0.1:8000/docs"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\venv\Scripts\pythonw.exe"; Parameters: """{app}\jj_bot_tray.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\venv\Scripts\pythonw.exe"; Parameters: """{app}\jj_bot_tray.py"""; WorkingDir: "{app}"; Tasks: startup

[Run]
; Install Python dependencies during setup
Filename: "python"; Parameters: "-m venv ""{app}\venv"""; StatusMsg: "Creating Python virtual environment..."; Flags: runhidden
Filename: "{app}\venv\Scripts\python.exe"; Parameters: "-m pip install --upgrade pip"; StatusMsg: "Upgrading pip..."; Flags: runhidden
Filename: "{app}\venv\Scripts\python.exe"; Parameters: "-m pip install -r ""{app}\requirements.txt"""; StatusMsg: "Installing Python dependencies..."; Flags: runhidden
Filename: "{app}\venv\Scripts\python.exe"; Parameters: "-m pip install pystray pillow"; StatusMsg: "Installing GUI dependencies..."; Flags: runhidden

; Install Node.js dependencies
Filename: "cmd"; Parameters: "/c cd /d ""{app}\dashboard\jj-dashboard"" && npm install"; StatusMsg: "Installing dashboard dependencies..."; Flags: runhidden

; Create data directories
Filename: "cmd"; Parameters: "/c mkdir ""{app}\data"""; Flags: runhidden
Filename: "cmd"; Parameters: "/c mkdir ""{app}\logs"""; Flags: runhidden
Filename: "cmd"; Parameters: "/c mkdir ""{app}\backups"""; Flags: runhidden

; Launch application after install
Filename: "{app}\venv\Scripts\pythonw.exe"; Parameters: """{app}\jj_bot_tray.py"""; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop services before uninstall
Filename: "taskkill"; Parameters: "/F /IM python.exe /FI ""WINDOWTITLE eq *main.py*"""; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM node.exe /FI ""WINDOWTITLE eq *vite*"""; Flags: runhidden

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check if Python is installed
  if not ShellExec('', 'python', '--version', '', SW_HIDE, ewNoWait, ResultCode) then
  begin
    if MsgBox('Python 3.8+ is required but not found. Would you like to download it now?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ResultCode);
    end;
    Result := False;
    Exit;
  end;

  // Check if Node.js is installed
  if not ShellExec('', 'node', '--version', '', SW_HIDE, ewNoWait, ResultCode) then
  begin
    if MsgBox('Node.js 16+ is required but not found. Would you like to download it now?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://nodejs.org/', '', '', SW_SHOW, ewNoWait, ResultCode);
    end;
    Result := False;
    Exit;
  end;
end;
