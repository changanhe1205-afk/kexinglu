param([int]$Port = 8788)

$ErrorActionPreference = 'Stop'
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    $python = 'C:\Users\chang\AppData\Local\Programs\Python\Python311\python.exe'
}
if (-not (Test-Path $python)) {
    throw '找不到 Python，请先安装 Python 3 并加入 PATH。'
}

Push-Location $PSScriptRoot
try {
    Write-Output "Waylore 本地预览： http://127.0.0.1:$Port"
    & $python -m http.server $Port --bind 127.0.0.1
} finally {
    Pop-Location
}
