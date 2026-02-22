@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  MashupID — Windows Launcher
REM  Double-click this file to setup and run MashupID on Windows
REM ═══════════════════════════════════════════════════════════════════

title MashupID

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║        MashupID — Windows Setup ^& Launcher       ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python not found!
    echo  Install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  [1/4] Python found:
python --version

REM Install requirements
echo.
echo  [2/4] Installing dependencies...
python -m pip install PyQt6 numpy scipy sounddevice pyinstaller --quiet --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo  WARNING: Some packages may have failed. Continuing...
)

REM Try pyaudio for Windows microphone support
echo.
echo  [3/4] Installing audio backend for Windows...
python -m pip install pipwin --quiet >nul 2>&1
python -m pipwin install pyaudio >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    python -m pip install pyaudio --quiet >nul 2>&1
)

REM Choose what to do
echo.
echo  [4/4] Choose an option:
echo.
echo   [1] Run app NOW  (no build, just run with Python)
echo   [2] Build .exe   (creates dist\MashupID.exe)
echo   [3] Create demo songs   (adds test songs to database)
echo   [4] Exit
echo.
set /p choice="  Enter choice (1-4): "

if "%choice%"=="1" goto run_app
if "%choice%"=="2" goto build_exe
if "%choice%"=="3" goto demo
if "%choice%"=="4" exit /b 0

:run_app
echo.
echo  Starting MashupID...
python main.py
goto end

:build_exe
echo.
echo  Building MashupID.exe (this takes 2-5 minutes)...
python -m PyInstaller MashupID.spec --clean --noconfirm
if exist dist\MashupID.exe (
    echo.
    echo  SUCCESS! File created: dist\MashupID.exe
    echo  You can copy this .exe to any Windows PC and run it directly.
    explorer dist
) else (
    echo  Build failed. Try running: python main.py directly.
)
goto end

:demo
echo.
echo  Creating demo songs...
python setup_and_build.py --demo
goto end

:end
echo.
pause
