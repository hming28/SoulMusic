@echo off
chcp 65001 >nul
title SoulMusic
cd /d "%~dp0"

python -c "import customtkinter, pygame, ytmusicapi, yt_dlp, pyperclip, PIL, mutagen" >nul 2>&1
if errorlevel 1 (
    echo Missing dependencies detected. Installing requirements.txt ...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies. Please check your Python / pip installation.
        pause
        exit /b 1
    )
)

python soulmusic.py
if errorlevel 1 (
    echo.
    echo Program exited unexpectedly. You can check soulmusic.log for details.
    pause
)
