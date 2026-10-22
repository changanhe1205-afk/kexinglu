param(
    [Parameter(Mandatory=$true)][string]$Profile,
    [string]$SigningName = 'default_release'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$buildProfile = Join-Path $repo 'build/harmony-app/ohos/build-profile.json5'
if (-not (Test-Path -LiteralPath $buildProfile)) { throw 'Prepare the Harmony workspace and generate local signing materials with DevEco first.' }
$profilePath = (Resolve-Path -LiteralPath $Profile).Path
Add-Type -AssemblyName System.Security
$cms = New-Object System.Security.Cryptography.Pkcs.SignedCms
$cms.Decode([IO.File]::ReadAllBytes($profilePath))
$cms.CheckSignature($true)
$manifest = [Text.Encoding]::UTF8.GetString($cms.ContentInfo.Content) | ConvertFrom-Json
if ($manifest.type -ne 'release' -or $manifest.'app-distribution-type' -ne 'app_gallery') {
    throw 'Use a Release Profile for AppGallery distribution.'
}
if ($manifest.'bundle-info'.'bundle-name' -ne 'com.changanhe.kexinglu') { throw 'Profile bundle name does not match Kexinglu.' }
$config = [IO.File]::ReadAllText($buildProfile) | ConvertFrom-Json
$signing = @($config.app.signingConfigs | Where-Object name -eq $SigningName)
if ($signing.Count -ne 1) { throw 'Generate the named local release signing configuration with DevEco first.' }
$pem = $manifest.'bundle-info'.'distribution-certificate'
$bytes = [Convert]::FromBase64String(($pem -replace '-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\s', ''))
$profileCertificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList @(,$bytes)
$chain = [IO.File]::ReadAllText($signing[0].material.certpath)
$matched = $false
# The local PEM contains a chain. The first certificate may be a root;
# compare the complete chain before concluding that a Profile is unrelated.
foreach ($block in [regex]::Matches($chain, '-----BEGIN CERTIFICATE-----([\s\S]*?)-----END CERTIFICATE-----')) {
    $certificateBytes = [Convert]::FromBase64String(($block.Groups[1].Value -replace '\s', ''))
    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList @(,$certificateBytes)
    if ($certificate.Thumbprint -eq $profileCertificate.Thumbprint) { $matched = $true }
    $certificate.Dispose()
}
$profileCertificate.Dispose()
if (-not $matched) { throw 'Profile certificate does not match the local signing chain. Select the matching release certificate in AppGallery Connect.' }
$signing[0].material.profile = $profilePath
foreach ($product in $config.app.products) {
    $product | Add-Member -NotePropertyName signingConfig -NotePropertyValue $SigningName -Force
}
$json = $config | ConvertTo-Json -Depth 40
[IO.File]::WriteAllText($buildProfile, $json, [Text.UTF8Encoding]::new($false))
Write-Output 'Release Profile validated and linked in the ignored local build workspace.'
