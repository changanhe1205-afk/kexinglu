param([switch]$Check, [switch]$Emulator)
$ErrorActionPreference = 'Stop'
$env:PUB_CACHE = 'D:/Tools/pub-cache'
$env:TEMP = 'D:/Tools/tmp'
$env:TMP = 'D:/Tools/tmp'
$env:JAVA_HOME = 'D:/Java/jdk-21.0.10'
$env:ANDROID_HOME = 'D:/Tools/android-sdk'
$flutter = 'D:/Tools/flutter/bin/flutter.bat'
Push-Location $PSScriptRoot
try {
    if ($Check) {
        & $flutter analyze --no-pub
        if ($LASTEXITCODE -ne 0) { throw 'Static analysis failed' }
        & $flutter test --no-pub
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    } else {
        # Public version stays fixed; Android requires increasing build codes
        # to install over previously delivered builds without clearing data.
        $manifestPath = Join-Path $PSScriptRoot 'pubspec.yaml'
        $manifestText = Get-Content -LiteralPath $manifestPath -Raw
        $versionMatch = [regex]::Match($manifestText, '(?m)^version: 1\.0\.0\+(\d+)\s*$')
        if (-not $versionMatch.Success) { throw 'Expected fixed Android version 1.0.0+BUILD in pubspec.yaml' }
        $buildNumber = [int]$versionMatch.Groups[1].Value + 1
        $manifestText = [regex]::Replace($manifestText, '(?m)^version: [^\r\n]+', "version: 1.0.0+$buildNumber")
        [IO.File]::WriteAllText($manifestPath, $manifestText, [Text.UTF8Encoding]::new($false))
        $architectures = if ($Emulator) { 'android-arm64,android-x64' } else { 'android-arm64' }
        & $flutter build apk --no-pub --release --target-platform $architectures
        if ($LASTEXITCODE -ne 0) { throw 'APK build failed' }
        $apkPath = Join-Path $PSScriptRoot 'build/app/outputs/flutter-apk/app-release.apk'
        $deliveryDir = Join-Path $PSScriptRoot '../dist/android'
        New-Item -ItemType Directory -Path $deliveryDir -Force | Out-Null
        $deliveryPath = Join-Path $deliveryDir 'Kexinglu-Android-1.0.0.apk'
        Copy-Item -LiteralPath $apkPath -Destination $deliveryPath -Force
        Write-Output $deliveryPath
    }
} finally { Pop-Location }
