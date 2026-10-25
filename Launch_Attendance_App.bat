@echo off
setlocal enabledelayedexpansion
title Auto Attendance Intelligence System - Launcher

cd /d "%~dp0"
set "PROJECT_DIR=%~dp0"

echo =====================================================================
echo          AUTO ATTENDANCE INTELLIGENCE SYSTEM - LAUNCHER
echo =====================================================================
echo.

:: 1. Detect Python executable
set "PYTHON_EXE="
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
) else (
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=py"
    ) else if exist "C:\Python314\python.exe" (
        set "PYTHON_EXE=C:\Python314\python.exe"
    ) else if exist "C:\Python313\python.exe" (
        set "PYTHON_EXE=C:\Python313\python.exe"
    ) else if exist "C:\Python312\python.exe" (
        set "PYTHON_EXE=C:\Python312\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        set "PYTHON_EXE=C:\Python311\python.exe"
    ) else if exist "C:\Python310\python.exe" (
        set "PYTHON_EXE=C:\Python310\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo During installation, be sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_EXE%
echo.

:: 2. Check if required libraries are installed
echo [*] Checking required dependencies...
"%PYTHON_EXE%" -c "import flask, cv2, numpy, cryptography" >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Missing dependencies detected. Installing required packages from requirements.txt...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
    echo.
) else (
    echo [OK] All dependencies are ready.
    echo.
)

:: 3. Create Desktop shortcut automatically if not already present
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
if exist "%USERPROFILE%\OneDrive\Desktop" (
    set "DESKTOP_DIR=%USERPROFILE%\OneDrive\Desktop"
)
if not exist "!DESKTOP_DIR!\Auto Attendance System.lnk" (
    echo [*] Creating Desktop Shortcut...
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('!DESKTOP_DIR!\Auto Attendance System.lnk'); $s.TargetPath = '%~dp0Launch_Attendance_App.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Auto Attendance Intelligence System'; $s.IconLocation = 'shell32.dll,13'; $s.Save()" >nul 2>nul
    if exist "!DESKTOP_DIR!\Auto Attendance System.lnk" (
        echo [OK] Desktop Shortcut created successfully on your Desktop.
        echo.
    )
)

:: 4. Start the Application
echo [*] Starting Auto Attendance Engine...
echo [*] Web Application will automatically open in your default browser at:
echo     http://127.0.0.1:5055/index.html
echo.
echo [Tip] Keep this console window open while using the attendance system.
echo       Press Ctrl+C to stop the server anytime.
echo.

"%PYTHON_EXE%" main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with an error.
    pause
)
