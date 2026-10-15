; 客行录 · Inno Setup 安装包脚本
;
; 用 build_installer.py 编译（或直接）：
;     D:\Tools\InnoSetup\ISCC.exe installer.iss
;
; 先决条件：已经跑过 build.py，dist\客行录\ 里是刚打好的程序。
;
; 几点说明：
;   1. PrivilegesRequired=lowest —— 默认装到 %LOCALAPPDATA%\Programs\客行录，
;      不需要管理员权限；安装界面里也可以切换成"为所有人安装"。
;   2. 用户数据在 %LOCALAPPDATA%\客行录，和安装目录是两个地方，
;      所以卸载不会动用户的记录、照片和设置。

; 路径都用 SourcePath（= 本 .iss 所在目录）拼出来，整个项目换盘符 / 换机器也能用。
#define AppName "客行录"
#define AppVersion "1.0.0"
#define AppExeName "客行录.exe"
#define SrcDir SourcePath + "\dist\客行录"
#define OutDir SourcePath + "\dist\installer"
#define IcoFile SourcePath + "\assets\app.ico"

[Setup]
; AppId 一旦发布就不要改，否则会被当成另一个软件（升级、卸载都会乱）
AppId={{7C4A1E92-3B6D-4F58-9E21-A5D0C7B4F831}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription={#AppName} · 本地珍藏
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; 一定要显示"选择安装位置"这一步：
; Inno 在"升级安装"时会自动跳过目录选择页，用户就只能在原来的盘（默认 C 盘）。
DisableDirPage=no
DisableProgramGroupPage=yes
DirExistsWarning=yes
AllowNoIcons=yes
UsePreviousTasks=no
OutputDir={#OutDir}
OutputBaseFilename={#AppName}-安装程序-{#AppVersion}
SetupIconFile={#IcoFile}
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern light windows11
WizardSizePercent=130,120
WizardBackColor=$F5F7F8
WizardImageFile=
WizardSmallImageFile=assets\app.png
DisableWelcomePage=no
ShowLanguageDialog=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
CloseApplications=yes
CloseApplicationsFilter=*.*
SetupLogging=yes
RestartApplications=no

[Languages]
; compiler: 前缀 = 相对 Inno Setup 自己的安装目录
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "assets\app.png"; Flags: dontcopy
Source: "{#SrcDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "Kexinglu.Desktop"; IconFilename: "{app}\_internal\assets\app-lu-v1.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    Tasks: desktopicon; AppUserModelID: "Kexinglu.Desktop"; IconFilename: "{app}\_internal\assets\app-lu-v1.ico"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
    Flags: nowait postinstall skipifsilent

[Messages]
chinese.WelcomeLabel1=欢迎来到客行录
chinese.WelcomeLabel2=旅途的片刻，餐桌的味道，散场后的感受。%n%n下一段记录，从这里开始。
chinese.FinishedHeadingLabel=安装完成
chinese.FinishedLabel=客行录已准备就绪。%n%n把今天值得记住的，留给以后的自己。
chinese.WizardSelectDir=安装位置
chinese.SelectDirDesc=选择客行录的安装位置。
chinese.WizardInstalling=正在准备你的客行录
chinese.InstallingLabel=片刻之后，开始下一段记录。
chinese.WizardReady=准备安装
chinese.ReadyLabel1=确认安装位置与快捷方式，随后开始安装。
chinese.ButtonInstall=开始安装(&I)
chinese.ButtonFinish=完成(&F)

chinese.ConfirmUninstall=是否卸载客行录？%n%n将移除应用和快捷方式，保留你的记录、照片与设置。
chinese.UninstalledAll=客行录已卸载。%n%n你的记录、照片与设置仍保存在本机，重新安装后可继续使用。

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Files: TArrayOfString;
  I: Integer;
  Stream: TFileStream;
  FileName: String;
begin
  Result := '';
  SetArrayLength(Files, 4);
  Files[0] := '\_internal\base_library.zip';
  Files[1] := '\{#AppExeName}';
  Files[2] := '\_internal\python314.dll';
  Files[3] := '\_internal\flet_desktop\app\flet\flet.exe';
  for I := 0 to GetArrayLength(Files)-1 do begin
    FileName := ExpandConstant('{app}') + Files[I];
    if FileExists(FileName) then begin
      try
        Stream := TFileStream.Create(FileName, fmOpenRead or fmShareExclusive);
        Stream.Free;
      except
        Log('Upgrade preflight blocked: ' + FileName);
        Result := '客行录仍在运行，或安装目录中的文件正被占用。' + #13#10 +
          '请先保存正在编辑的内容，正常退出客行录，再点击“重试”。' + #13#10 +
          '此时尚未替换应用文件，请不要跳过文件继续安装。' + #13#10 + FileName;
        Exit;
      end;
    end;
  end;
end;

const
  Paper = $F5F7F8;
  Ink = $30332F;
  Muted = $7B8079;
  Sage = $718365;
  Line = $E2E6DF;
var
  ProgressSurface, ProgressTrack, ProgressFill: TPanel;
  ProgressNumber, ProgressStatus: TNewStaticText;
  LastPercent: Integer;

function BrandText(Parent: TWinControl; X, Y, W, H, Size: Integer;
  TextColor: TColor; Words: String): TNewStaticText;
begin
  Result := TNewStaticText.Create(Parent);
  Result.Parent := Parent;
  Result.StyleElements := [];
  Result.AutoSize := False;
  Result.SetBounds(X,Y,W,H);
  Result.Caption := Words;
  Result.Color := Paper;
  Result.Font.Name := 'Microsoft YaHei UI';
  Result.Font.Size := Size;
  Result.Font.Color := TextColor;
  Result.WordWrap := True;
end;

function FlatPanel(Parent: TWinControl; X, Y, W, H: Integer; Fill: TColor): TPanel;
begin
  Result := TPanel.Create(Parent);
  Result.Parent := Parent;
  Result.SetBounds(X,Y,W,H);
  Result.BevelOuter := bvNone;
  Result.ParentBackground := False;
  Result.StyleElements := [];
  Result.Color := Fill;
end;

procedure BrandHeader(Surface: TWinControl);
var Mark: TBitmapImage; LogoPath: String;
begin
  if IsUninstaller then LogoPath := ExpandConstant('{app}\_internal\assets\app.png')
  else LogoPath := ExpandConstant('{tmp}\app.png');
  if FileExists(LogoPath) then begin
    Mark := TBitmapImage.Create(Surface);
    Mark.Parent := Surface;
    Mark.SetBounds(ScaleX(42),ScaleY(30),ScaleX(28),ScaleY(28));
    Mark.Stretch := True;
    Mark.BackColor := Paper;
    Mark.PngImage.LoadFromFile(LogoPath);
  end;
  BrandText(Surface,ScaleX(82),ScaleY(33),ScaleX(160),ScaleY(26),12,Ink,'客行录');
end;

procedure BrandPage(Surface: TNewNotebookPage; Heading, Body: TNewStaticText; IsFinish: Boolean);
var X, W: Integer;
begin
  Surface.Color := Paper;
  X := ScaleX(42);
  W := Surface.Width-X*2;
  BrandHeader(Surface);
  Heading.StyleElements := [];
  Heading.AutoSize := False;
  Heading.Color := Paper;
  Heading.SetBounds(X,ScaleY(134),W,ScaleY(54));
  Heading.Font.Name := 'Microsoft YaHei UI';
  Heading.Font.Size := 25;
  Heading.Font.Style := [];
  Heading.Font.Color := Ink;
  Body.StyleElements := [];
  Body.AutoSize := False;
  Body.Color := Paper;
  Body.SetBounds(X,ScaleY(202),W,ScaleY(62));
  Body.Font.Name := 'Microsoft YaHei UI';
  Body.Font.Size := 11;
  Body.Font.Color := Muted;
  if IsFinish then begin
    Heading.Caption := '安装完成';
    Body.Caption := '客行录已准备就绪。现在，开始记录生活。';
  end else begin
    Heading.Caption := '把日常，留成珍藏。';
    Body.Caption := '旅途、食光与电影，属于你的生活收藏。' + #13#10 + '安装客行录，慢慢记录每一个值得记住的瞬间。';
  end;
  FlatPanel(Surface,X,Surface.Height-ScaleY(95),W,ScaleY(1),Line);
  if not IsFinish then
    BrandText(Surface,X,Surface.Height-ScaleY(68),W,ScaleY(30),9,Muted,'本地记录    /    自由珍藏    /    {#AppVersion}');
end;

procedure CreateProgressPage;
var X, W: Integer;
begin
  ProgressSurface := FlatPanel(WizardForm.InnerPage,0,0,WizardForm.InnerPage.Width,WizardForm.InnerPage.Height,Paper);
  ProgressSurface.Visible := False;
  BrandHeader(ProgressSurface);
  X := ScaleX(42);
  W := ProgressSurface.Width-X*2;
  BrandText(ProgressSurface,X,ScaleY(128),W,ScaleY(48),25,Ink,'正在安装');
  BrandText(ProgressSurface,X,ScaleY(188),W,ScaleY(30),11,Muted,'片刻之后，开启你的生活收藏。');
  ProgressStatus := BrandText(ProgressSurface,X,ScaleY(263),W-ScaleX(95),ScaleY(28),10,Muted,'正在准备安装');
  ProgressNumber := BrandText(ProgressSurface,X+W-ScaleX(90),ScaleY(258),ScaleX(90),ScaleY(32),15,Ink,'0%');
  ProgressNumber.Alignment := taRightJustify;
  ProgressNumber.WordWrap := False;
  ProgressTrack := FlatPanel(ProgressSurface,X,ScaleY(305),W,ScaleY(4),Line);
  ProgressFill := FlatPanel(ProgressTrack,0,0,0,ProgressTrack.Height,Sage);
  LastPercent := -1;
end;

procedure InitializeWizard;
begin
  ExtractTemporaryFile('app.png');
  WizardForm.Caption := '客行录 · 安装';
  WizardForm.Font.Name := 'Microsoft YaHei UI';
  WizardForm.WizardBitmapImage.Visible := False;
  WizardForm.WizardBitmapImage2.Visible := False;
  BrandPage(WizardForm.WelcomePage,WizardForm.WelcomeLabel1,WizardForm.WelcomeLabel2,False);
  BrandPage(WizardForm.FinishedPage,WizardForm.FinishedHeadingLabel,WizardForm.FinishedLabel,True);
  WizardForm.PageNameLabel.Top := ScaleY(8);
  WizardForm.PageNameLabel.Height := ScaleY(28);
  WizardForm.PageDescriptionLabel.Top := ScaleY(38);
  WizardForm.PageNameLabel.Font.Size := 14;
  WizardForm.PageNameLabel.Font.Color := Ink;
  WizardForm.PageDescriptionLabel.Font.Color := Muted;
  WizardForm.WizardSmallBitmapImage.SetBounds(WizardForm.MainPanel.Width-ScaleX(52),ScaleY(12),ScaleX(32),ScaleY(32));
  BrandText(WizardForm,ScaleX(25),WizardForm.CancelButton.Top+ScaleY(5),ScaleX(210),ScaleY(22),9,Muted,'客行录  /  {#AppVersion}');
  CreateProgressPage;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  ProgressSurface.Visible := CurPageID = wpInstalling;
  if CurPageID = wpInstalling then begin
    ProgressSurface.BringToFront;
    WizardForm.ProgressGauge.Visible := False;
    WizardForm.FilenameLabel.Visible := False;
    WizardForm.StatusLabel.Visible := False;
  end;
  if CurPageID = wpWelcome then WizardForm.NextButton.Caption := '开始安装(&N)';
  if CurPageID = wpFinished then begin
    WizardForm.RunList.SetBounds(ScaleX(42),WizardForm.FinishedPage.Height-ScaleY(72),WizardForm.FinishedPage.Width-ScaleX(84),ScaleY(42));
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
var Percent, FillWidth: Integer;
begin
  if MaxProgress <= 0 then Exit;
  Percent := Round(CurProgress * 100.0 / MaxProgress);
  if Percent < 0 then Percent := 0;
  if Percent > 100 then Percent := 100;
  FillWidth := Round(Percent * 1.0 / 100 * ProgressTrack.Width);
  ProgressFill.Width := FillWidth;
  if Percent <> LastPercent then begin
    LastPercent := Percent;
    ProgressNumber.Caption := IntToStr(Percent) + '%';
    ProgressStatus.Caption := '正在写入应用文件';
    ProgressNumber.Repaint;
    ProgressFill.Repaint;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    ProgressNumber.Caption := '100%';
    ProgressFill.Width := ProgressTrack.Width;
    ProgressStatus.Caption := '正在完成安装';
  end;
end;

procedure InitializeUninstallProgressForm;
var Surface: TPanel; X, W: Integer;
begin
  UninstallProgressForm.Caption := '客行录 · 卸载';
  UninstallProgressForm.Font.Name := 'Microsoft YaHei UI';
  Surface := FlatPanel(UninstallProgressForm,0,0,UninstallProgressForm.ClientWidth,
    UninstallProgressForm.CancelButton.Top-ScaleY(18),Paper);
  BrandHeader(Surface);
  X := ScaleX(42);
  W := Surface.Width-X*2;
  BrandText(Surface,X,ScaleY(108),W,ScaleY(48),24,Ink,'正在卸载');
  BrandText(Surface,X,ScaleY(172),W,ScaleY(56),11,Muted,
    '移除应用，保留你的珍藏。' + #13#10 + '记录、照片与设置仍会保存在本机。');
  UninstallProgressForm.ProgressBar.Parent := Surface;
  UninstallProgressForm.ProgressBar.SetBounds(X,Surface.Height-ScaleY(65),W,ScaleY(6));
  BrandText(Surface,X,Surface.Height-ScaleY(44),W,ScaleY(24),9,Muted,'正在移除应用文件与快捷方式');
  Surface.BringToFront;
end;






