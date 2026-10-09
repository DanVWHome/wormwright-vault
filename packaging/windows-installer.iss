#define AppVersion "0.3.2"
[Setup]
AppId={{A42A398C-91E7-4C36-A1E4-AB351BE3DF27}
AppName=Wormwright Vault
AppVersion={#AppVersion}
AppVerName=Wormwright Vault 0.3.2 preview 2
AppPublisher=Wormwright
AppPublisherURL=https://wormwright.com
DefaultDirName={localappdata}\Programs\Wormwright Vault
DefaultGroupName=Wormwright Vault
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\installer-input\WormwrightVault\docs\LICENSE
OutputDir=..\dist-installer
OutputBaseFilename=wormwright-vault_0.3.2_windows_x64_preview2_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\WormwrightVault.exe
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "..\installer-input\WormwrightVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Wormwright Vault"; Filename: "{app}\WormwrightVault.exe"
Name: "{group}\Wormwright Vault Manager"; Filename: "{app}\WormwrightVault.exe"; Parameters: "--manager"
Name: "{autodesktop}\Wormwright Vault"; Filename: "{app}\WormwrightVault.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\WormwrightVault.exe"; Description: "Open Wormwright Vault"; Flags: nowait postinstall skipifsilent
