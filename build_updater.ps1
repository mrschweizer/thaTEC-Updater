$ErrorActionPreference = "Stop"
$workspace = $PSScriptRoot

try {
    Set-Location $workspace

    python -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed for this Python interpreter. Install it with: python -m pip install pyinstaller"
    }

    $archive = Join-Path $workspace "thaTEC-core.zip"
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
        throw "Missing thaTEC-core.zip next to this script."
    }

    python -m PyInstaller --noconfirm --clean --onedir --name thaTEC-Updater updater.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $outputDirectory = Join-Path $workspace "dist\thaTEC-Updater\_internal"
    Copy-Item -LiteralPath $archive -Destination (Join-Path $outputDirectory "thaTEC-core.zip") -Force

    Write-Host ""
    Write-Host "Build complete:"
    Write-Host (Join-Path $outputDirectory "thaTEC-Updater.exe")
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
