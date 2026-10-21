[Setup]
AppName=YAVIS
AppVersion=2.0
AppPublisher=YAVIS Project
DefaultDirName={autopf}\YAVIS
DefaultGroupName=YAVIS
OutputDir=Output
OutputBaseFilename=YAVIS-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\YAVIS.exe
PrivilegesRequired=lowest

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: checked
Name: "autostart";   Description: "YAVIS mit Windows starten";      GroupDescription: "Autostart:"; Flags: unchecked

[Files]
Source: "dist\YAVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\YAVIS";                Filename: "{app}\YAVIS.exe"
Name: "{group}\YAVIS deinstallieren"; Filename: "{uninstallexe}"
Name: "{commondesktop}\YAVIS";        Filename: "{app}\YAVIS.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "YAVIS"; ValueData: """{app}\YAVIS.exe"""; \
  Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\YAVIS.exe"; Description: "YAVIS jetzt starten"; \
  Flags: nowait postinstall skipifsilent
