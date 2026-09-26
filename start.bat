@echo off
setlocal EnableExtensions
title TRAKKOUT - Setup
cd /d "%~dp0"

echo ================================================
echo   TRAKKOUT
echo   First-run setup + launch
echo ================================================
echo.

rem --- Locate a Python interpreter -------------------------------------
set "PYCMD="
where py >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"
if not defined PYCMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
    echo [ERROR] Python 3 was not found on this system.
    echo Install it from https://www.python.org/downloads/
    echo and make sure to check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)
echo Using Python: %PYCMD%
%PYCMD% --version

rem --- Verify it is a working Python 3 (not a Store stub) ------------------
rem The Microsoft Store ships a fake python.exe that only opens the Store;
rem `where` finds it, but it cannot run anything (no version output).
set "PYVER="
for /f "delims=" %%V in ('%PYCMD% --version 2^>^&1') do (
    if not defined PYVER set "PYVER=%%V"
)
echo %PYVER% | findstr /R /C:"^Python 3\." >nul
if errorlevel 1 (
    echo.
    echo [ERROR] "%PYCMD%" is not a working Python 3 interpreter.
    echo This is usually the Microsoft Store stub, which cannot create
    echo virtual environments.
    echo.
    echo Fix:
    echo   1. Install Python from https://www.python.org/downloads/
    echo      ^(check "Add python.exe to PATH"^), then run start.bat again.
    echo   2. Or disable the stub: Windows Settings ^> Apps ^> Advanced app
    echo      settings ^> App execution aliases ^> turn OFF "python.exe".
    echo.
    pause
    exit /b 1
)

rem --- Create virtual environment (first time only) ---------------------
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [1/3] Creating virtual environment...
    %PYCMD% -m venv venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not create the virtual environment (see above^).
        echo Usual causes: no disk space, antivirus blocking it, or
        echo controlled folder access. Fix it and run start.bat again.
        echo.
        pause
        exit /b 1
    )
    rem --- Sanity-check the new environment ------------------------------
    "venv\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ERROR] The virtual environment was created but its Python
        echo does not run. Antivirus, controlled folder access or a full
        echo disk are the usual suspects. Check the messages above.
        echo.
        pause
        exit /b 1
    )
) else (
    echo.
    echo [1/3] Virtual environment already exists - skipping.
)

rem --- Install / update dependencies ------------------------------------
echo [2/3] Installing dependencies (first time may take a while)...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Could not install the dependencies.
    pause
    exit /b 1
)

rem --- FFmpeg check (video generation needs it) ---------------------------
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo [NOTE] FFmpeg was not found on PATH. Video generation needs it:
    echo        winget install Gyan.FFmpeg
    echo        (or set its folder later in File ^> Settings).
    echo.
)

rem --- Launch the app ----------------------------------------------------
echo [3/3] Launching the app...
echo.
start "" "venv\Scripts\pythonw.exe" -m app.main

endlocal
