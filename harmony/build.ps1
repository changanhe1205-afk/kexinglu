param(
    [string]$FlutterRoot = 'D:/Tools/flutter-harmony',
    [string]$StudioRoot = 'D:/Tools/DevEcoStudio',
    [string]$PluginCache = 'D:/Tools/harmony-plugins',
    [string]$Python = 'D:/Waylore/.venv314/Scripts/python.exe',
    [switch]$CheckOnly,
    [switch]$Signed,
    [ValidateSet('hap','app')][string]$Package = 'hap',
    [ValidateSet('ohos-arm64','ohos-x64')][string]$TargetPlatform = 'ohos-arm64',
    [ValidateSet('release','debug')][string]$BuildMode = 'release'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$workspace = Join-Path $repo 'build/harmony-app'
$flutter = Join-Path $FlutterRoot 'bin/flutter.bat'
if (-not (Test-Path -LiteralPath $flutter)) { throw 'Install the pinned Flutter OH SDK in toolchain.lock.json first.' }
$env:PUB_CACHE = Join-Path (Split-Path $FlutterRoot -Parent) 'pub-cache-harmony'
$env:DEVECO_CLI_STUDIO_PATH = $StudioRoot
$env:DEVECO_SDK_HOME = Join-Path $StudioRoot 'sdk'
$env:HOS_SDK_HOME = $env:DEVECO_SDK_HOME
$env:JAVA_HOME = Join-Path $StudioRoot 'jbr'
$env:PATH = (Join-Path $StudioRoot 'tools/hvigor/bin') + ';' + (Join-Path $StudioRoot 'tools/ohpm/bin') + ';' + (Join-Path $StudioRoot 'tools/node') + ';' + $env:PATH
& $Python (Join-Path $PSScriptRoot 'prepare.py') --cache $PluginCache
if ($LASTEXITCODE -ne 0) { throw 'Harmony workspace preparation failed.' }
Push-Location $workspace
$nativeProfile = Join-Path $workspace 'ohos/build-profile.json5'
$originalNativeProfile = $null
try {
    & $flutter pub get
    if ($LASTEXITCODE -ne 0) { throw 'Harmony plugin/SDK setup failed.' }
    & $flutter analyze --no-pub
    if ($LASTEXITCODE -ne 0) { throw 'Dart analysis failed.' }
    & $flutter test --no-pub
    if ($LASTEXITCODE -ne 0) { throw 'Flutter tests failed.' }
    if ($CheckOnly) { return }
    $flags = @('build', $Package, "--$BuildMode", '--no-pub', '--target-platform', $TargetPlatform)
    if (-not $Signed) {
        $flags += '--no-codesign'
        # Hvigor still signs when a product references a local signing config,
        # even with Flutter's --no-codesign. Temporarily detach that reference.
        $originalNativeProfile = [IO.File]::ReadAllText($nativeProfile)
        $unsignedProfile = $originalNativeProfile -replace '"signingConfig"\s*:\s*"[^"]*"\s*,?', ''
        [IO.File]::WriteAllText($nativeProfile, $unsignedProfile, [Text.UTF8Encoding]::new($false))
    }
    & $flutter @flags
    if ($LASTEXITCODE -ne 0) { throw 'Native HarmonyOS compilation failed; no package is ready for publication.' }
    Write-Output 'Build complete. Signing and device/store validation must be checked before public delivery.'
} finally {
    if ($null -ne $originalNativeProfile) {
        [IO.File]::WriteAllText($nativeProfile, $originalNativeProfile, [Text.UTF8Encoding]::new($false))
    }
    Pop-Location
}
