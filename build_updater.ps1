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
    $bundledArchive = Join-Path $outputDirectory "thaTEC-core.zip"
    Copy-Item -LiteralPath $archive -Destination $bundledArchive -Force

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::Open($bundledArchive, [System.IO.Compression.ZipArchiveMode]::Update)
    try {
        @($zip.Entries | Where-Object { $_.Name -eq "thaTEC-core.db" }) | ForEach-Object { $_.Delete() }
    }
    finally {
        $zip.Dispose()
    }

    $distDirectory = Join-Path $workspace "dist\thaTEC-Updater"
    $distArchive = Join-Path $workspace "dist\thaTEC-Updater.zip"
    Compress-Archive -LiteralPath $distDirectory -DestinationPath $distArchive -Force

    Write-Host ""
    Write-Host "Build complete:"
    Write-Host (Join-Path $distDirectory "thaTEC-Updater.exe")
    Write-Host $distArchive
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}

