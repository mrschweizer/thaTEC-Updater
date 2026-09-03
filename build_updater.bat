@echo off
setlocal
pushd "%~dp0"

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed for this Python interpreter.
    echo Install it with: python -m pip install pyinstaller
    popd
    exit /b 1
)

if not exist "thaTEC-core.zip" (
    echo Missing thaTEC-core.zip next to this batch file.
    popd
    exit /b 1
)

python -m PyInstaller --noconfirm --clean --onedir --name thaTEC-Updater updater.py
if errorlevel 1 (
    echo PyInstaller failed.
    popd
    exit /b 1
)

copy /Y "thaTEC-core.zip" "dist\thaTEC-Updater\thaTEC-core.zip" >nul
if errorlevel 1 (
    echo Could not copy thaTEC-core.zip to the output folder.
    popd
    exit /b 1
)

echo.
echo Build complete:
dist\thaTEC-Updater\thaTEC-Updater.exe
popd
endlocal
