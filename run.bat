@echo off
chcp 65001 >nul
title SoulMusic
cd /d "%~dp0"

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_EXE=python"
    )
    if not defined PYTHON_EXE (
        where py >nul 2>&1
        if not errorlevel 1 (
            for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')" 2^>nul') do set "PYTHON_EXE=%%I"
        )
    )
    if not defined PYTHON_EXE (
        echo Python 3.9+ not found. Please install Python 3.9+ or run install.ps1.
        pause
        exit /b 1
    )
    echo Creating local virtual environment .venv ...
    "%PYTHON_EXE%" -m venv .venv >nul 2>&1
    if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -c "import customtkinter, pygame, ytmusicapi, yt_dlp, pyperclip, PIL, mutagen" >nul 2>&1
if errorlevel 1 (
    echo Missing dependencies detected. Installing requirements.txt ...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies. Please check your Python / pip installation.
        pause
        exit /b 1
    )
)

set "NEED_FFMPEG=0"
if not exist "ffmpeg.exe" (
    where ffmpeg >nul 2>&1 || set "NEED_FFMPEG=1"
)
if not exist "ffplay.exe" (
    where ffplay >nul 2>&1 || set "NEED_FFMPEG=1"
)
if "%NEED_FFMPEG%"=="1" (
    if exist "get_ffmpeg.ps1" (
        echo FFmpeg not found. Downloading static FFmpeg build ...
        powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0get_ffmpeg.ps1"
    )
)

"%PYTHON_EXE%" soulmusic.py
if errorlevel 1 (
    echo.
    echo Program exited unexpectedly. You can check soulmusic.log for details.
    pause
)
