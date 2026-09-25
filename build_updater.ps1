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

    python -m PyInstaller --noconfirm --clean --onedir --name labMule-Updater updater.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    $outputDirectory = Join-Path $workspace "dist\thaTEC-Updater\_internal"
    $bundledArchive = Join-Path $outputDirectory "thaTEC-core.zip"
    # Write the filtered archive in a single pass instead of copying and reopening it:
    # a freshly copied file is often briefly locked by antivirus/indexer scans.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $bundledArchive) {
        Remove-Item -LiteralPath $bundledArchive -Force
    }
    $sourceZip = [System.IO.Compression.ZipFile]::OpenRead($archive)
    try {
        $targetZip = [System.IO.Compression.ZipFile]::Open($bundledArchive, [System.IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($entry in $sourceZip.Entries) {
                if ($entry.Name -eq "thaTEC-core.db") {
                    continue
                }
                $newEntry = $targetZip.CreateEntry($entry.FullName, [System.IO.Compression.CompressionLevel]::Optimal)
                $newEntry.LastWriteTime = $entry.LastWriteTime
                if ($entry.FullName.EndsWith("/")) {
                    continue
                }
                $sourceStream = $entry.Open()
                $targetStream = $newEntry.Open()
                try {
                    $sourceStream.CopyTo($targetStream)
                }
                finally {
                    $targetStream.Dispose()
                    $sourceStream.Dispose()
                }
            }
        }
        finally {
            $targetZip.Dispose()
        }
    }
    finally {
        $sourceZip.Dispose()
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

