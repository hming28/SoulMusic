<div align="center">

# 🎵 SoulMusic

**Lightweight Desktop Music Companion Player**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=flat)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.1.0-orange?style=flat)]()
[![GUI](https://img.shields.io/badge/GUI-Tkinter%20%2F%20TTK-teal?style=flat)]()

*Minimalist · Fast Matching · Clipboard Auto-Detection · Dual Themes · Multilingual*

[English](#-english) • [中文说明](#-中文说明)

</div>

---

# 🌐 English

## 📖 Introduction

**SoulMusic** is a lightweight, zero-login desktop companion music player.

It acts as a background companion that **automatically detects and captures music share links copied to your clipboard**, resolves track metadata locally without any login, and matches the audio source for high-quality streaming and local caching.

It also functions as an independent mini player, allowing you to directly search and play any song by track title or artist.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 🎨 **Dual Themes** | **Clean White Theme by default**; seamlessly switch to **Dark Theme** with one click. Entry colors are fine-tuned to avoid any contrast issues. |
| 🌐 **Multilingual Support** | **English by default**; toggle between English and Chinese (`🌐 中文` / `🌐 EN`) at any time. |
| 📋 **Smart Clipboard Listener** | Copy a song link in any music client or web player; SoulMusic captures and starts playing automatically. |
| ⚡ **Zero-Login & Zero-Config** | Resolves metadata through public structured endpoints without requiring an account or API key. |
| 🎧 **High-Fidelity Audio** | Automatically matches audio tracks, extracts 192kbps MP3s, and caches locally for instant playback. |
| 🎛️ **Full Playback Controls** | Smooth seekbar with millisecond jumping, track queue, 0-100% linear volume slider, and live status. |
| ⌨️ **Safe Hotkeys** | Global Spacebar for Play/Pause (smartly detects focus when typing to prevent interference). |

---

## 🖥️ UI Overview

```text
+--------------------------------------------------------------------+
|  SoulMusic - Music Companion Player                         - [x]  |
+--------------------------------------------------------------------+
|                       Artist - Track Title                         |
|            Status: Playing 🎵 (Artist - Track Title)               |
|                                                                    |
|  [ Search song or paste link...    ] [🔍 Play/Search] [🌙 Dark] [🌐]|
|                                                                    |
|  01:23  ===================O---------------------  04:29           |
|                                                                    |
|  [⏮ Prev]         [⏸ Pause]         [⏹ Stop]         [⏭ Next]    |
|                                                                    |
|  🔊 Volume: -------------------O---  80%                           |
|                                                                    |
|  💡 Shortcuts: Space = Play/Pause | Drag slider to seek & volume   |
+--------------------------------------------------------------------+
```

---

## 🚀 Quick Start (3 Minutes)

### Step 1: Install Python

Ensure Python 3.9 or higher is installed on your computer (make sure **Add Python to PATH** is checked during installation).

### Step 2: Clone and Install Dependencies

Open a terminal (PowerShell, Command Prompt, or Bash) in your desired folder:

```bash
git clone https://github.com/hming28/SoulMusic.git
cd SoulMusic
pip install -r requirements.txt
```

### Step 3: Get FFmpeg (Recommended)

FFmpeg handles fast audio extraction and transcoding. Windows users can run the built-in downloader:

```powershell
powershell -ExecutionPolicy Bypass -File .\get_ffmpeg.ps1
```
*(If FFmpeg is already installed and in your system PATH, you can skip this step.)*

### Step 4: Run the Player

- **Windows Users**: Double-click **`run.bat`**.
- **Command Line**:
  ```bash
  python soulmusic.py
  ```

---

## 💡 Usage Scenarios

### Scenario 1: Clipboard Companion
1. Click **Share ➔ Copy Song Link** in your music app or web browser.
2. Switch to SoulMusic; it automatically parses the track and starts playing!

### Scenario 2: Direct Search
1. Type any song title or artist in the search box.
2. Press **Enter** or click **`🔍 Play / Search`**.

### Scenario 3: Theme and Language Switching
- Click **`🌙 Dark` / `☀️ Light`** to switch between light and dark modes.
- Click **`🌐 中文` / `🌐 EN`** to toggle between English and Chinese interface languages.

---

## ⌨️ Shortcuts Guide

| Key | Action | Description |
| :---: | :---: | :--- |
| **Space** | Play / Pause | Global shortcut; types normal spaces when the search box is focused. |
| **Enter** | Search & Play | Triggers search when typing in the search box. |
| **Left Click Drag** | Seek / Volume | Click or drag on the progress bar or volume slider for real-time control. |

---

## 📁 Project Structure

```text
SoulMusic/
├── soulmusic.py             # Main player core application
├── requirements.txt         # Core Python dependencies
├── get_ffmpeg.ps1           # Automated FFmpeg build downloader
├── run.bat                  # One-click Windows launcher
├── test_phase1.py           # Unit test suite (20/20 tests passing)
├── test_integration.py      # End-to-end integration test
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
└── README.md                # Bilingual documentation
```

---

## ❓ FAQ

<details>
<summary><b>Q1: Do I need to create an account or log in?</b></summary>
No. SoulMusic resolves public track data and streams audio without requiring any account login.
</details>

<details>
<summary><b>Q2: Does it download the same song repeatedly?</b></summary>
No. Played songs are cached in the local <code>cache/</code> directory. Subsequent plays load directly from the local cache with zero latency.
</details>

<details>
<summary><b>Q3: Is the text clear in dark mode?</b></summary>
Yes. In dark mode, the input box uses a <code>#282828</code> background with crisp <code>#FFFFFF</code> white font and cursor.
</details>

---
---

# 🇨🇳 中文说明

## 📖 项目简介

**SoulMusic** 是一款轻量、免登录的桌面音乐伴侣播放器。

应用能够作为后台伴侣，**自动侦测并捕获在音频平台中复制的歌曲分享链接**，在本地免登录解析元数据，并秒级匹配音源进行流媒体播放与本地缓存。同时支持直接通过歌曲名称或歌手搜索并点播。

---

## ✨ 核心特性

- 🎨 **默认白色现代主题**：清爽通透，支持一键切换至夜间暗黑主题，输入框字体对比度清晰。
- 🌐 **默认英文界面与双语切换**：启动默认英文，支持点击 `🌐 中文` 实时无缝切换至中文。
- 📋 **剪贴板自动识别**：复制歌曲链接即可自动播放，无需手动粘贴。
- ⚡ **免登录零配置**：采用公开结构化接口解析机制，无需账号或 API Key。
- 🎧 **高保真流式引擎**：自动提取 192kbps MP3 本地缓存，二次播放秒开。
- 🎛️ **现代播放控制**：精准进度轴拖拽、队列管理、0-100% 实时音量调节与防误触快捷键。

---

## 🚀 3分钟快速上手

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
2. **下载 FFmpeg（Windows 用户可选）**：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\get_ffmpeg.ps1
   ```
3. **启动运行**：
   - 双击运行 **`run.bat`** 或在终端执行 `python soulmusic.py`。

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
