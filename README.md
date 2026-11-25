<div align="center">

# 🎵 SoulMusic

**Modern Desktop Music Companion Player**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=flat)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v2.1-orange?style=flat)]()
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-teal?style=flat)]()

*Modern Card UI · High-Res Cover Art · Smart Audio Scoring · Batch Playlist Resolution · Zero-Login*

[English](#-english) • [中文说明](#-中文说明)

</div>

---

# 🌐 English

## 📖 Introduction

**SoulMusic** is a modern, zero-login desktop companion music player.

It acts as an intelligent desktop companion that **automatically monitors your clipboard for music share links**, parses track, album, and playlist metadata without requiring any login, and accurately matches audio streams with multi-dimensional candidate scoring for instant playback and local caching.

It also serves as a standalone music workstation, supporting direct search, queue drawer management, album/playlist batch parsing, and adaptive light/dark appearance modes.

---

## 🔄 Version Evolution (v1.0.0 vs v2.0.0)

| Dimension | v1.0.0 (Stable Legacy) | v2.0.0 (Current Modern Release) |
| :--- | :--- | :--- |
| **GUI Architecture** | Lightweight native Tkinter + TTK (~30MB RAM) | Modern CustomTkinter (rounded cards, smooth fluid layout) |
| **Theme System** | Default clean white + dark theme toggle | Native adaptive Light / Dark theme system |
| **Cover Art** | Text-only title & status | High-resolution album cover art rendering (Pillow) |
| **Link Support** | Spotify single track / manual search query | Spotify single track + Album / Playlist batch resolution + YouTube links |
| **Matching Algorithm** | Basic YTMusic query retrieval | Multi-dimensional smart scoring (filters covers/karaoke, validates duration) |
| **Playback Modes** | Sequential queue playback | Loop All / Loop One / Shuffle modes |
| **State Persistence** | In-memory only (clears upon exit) | Local JSON persistence (preserves config & queue) |
| **Cache Management** | Full local cache | Automatic 500MB LRU cache pruning threshold |
| **Dependencies** | 4 basic libraries (`pygame`, `yt-dlp`, `ytmusicapi`, `pyperclip`) | Enhanced with `customtkinter`, `Pillow`, and `mutagen` |

---

## ✨ Features in v2.0.0

| Feature | Description |
| :--- | :--- |
| 🖼️ **Modern Card Interface** | Built with CustomTkinter featuring dark/light card aesthetics, fluid controls, and high-resolution album cover art via Pillow. |
| 🎨 **Adaptive Theme System** | Starts in an **elegant white theme by default**, with one-click toggling to a dark theme. Input fields and text colors automatically adapt with crisp contrast. |
| 🌐 **Bilingual Support** | **English by default**; switch between English and Chinese (`🌐 中文` / `🌐 EN`) on the fly. |
| 📦 **Album & Playlist Resolution** | Paste any Spotify playlist or album URL; SoulMusic batch-extracts all tracks into your playback queue. |
| 🎯 **Smart Audio Matching** | Advanced candidate ranking algorithm filters out covers, live versions, sped-up/slowed tracks, and karaoke renditions while validating song durations. |
| 🔀 **Multiple Playback Modes** | Supports **Loop All (🔁)**, **Loop One (🔂)**, and **Shuffle (🔀)**. |
| 💾 **Queue & Config Persistence** | Saves volume, repeat mode, pin state, and playlist queue to local JSON files across app restarts. |
| 🧹 **Smart Cache Pruning** | Keeps track of cached audio sizes with a 500MB safety threshold and a one-click cache purge button. |

---

## 🖥️ UI Layout Overview

```text
+--------------------------------------------------------------------------+
|  SoulMusic                                                        - [x]  |
+--------------------------------------------------------------------------+
|  [📌 Pin: ON] [📋 Clip: ON] [Auto: Play] [🌐 中文] [🌙]    [Queue (3)] [Cache] |
|                                                                          |
|  [ Paste Spotify/YouTube link, or type song title... ] [✕] [🔍 Play/Search]|
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  | [ Cover Art ]  Song Title                                          |  |
|  | [   68x68   ]  Artist Name                                         |  |
|  |                Status: Playing                                     |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  01:23  ===================O---------------------------------  03:45     |
|                                                                          |
|  [🔁 Loop All]  [⏮]  [⏸ Pause]  [⏹]  [⏭]    [🔊] --------O--  80%     |
|                                                                          |
|  ▼ Playback Queue (3 tracks)                                [Clear Queue] |
|    ▶ 1. Artist 1 - Track 1                                               |
|      2. Artist 2 - Track 2                                               |
|      3. Artist 3 - Track 3                                               |
+--------------------------------------------------------------------------+
```

---

## 🚀 Quick Start

### ⚡ One-Command Install & Run (Recommended)
Run a single command on any new laptop (automatically handles Python, virtual environment `.venv`, dependencies, FFmpeg, Desktop shortcut, and launch):

- **Windows (PowerShell)**:
  ```powershell
  irm https://raw.githubusercontent.com/hming28/SoulMusic/main/install.ps1 | iex
  ```
- **macOS / Linux (Bash)**:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/hming28/SoulMusic/main/install.sh | bash
  ```

### 🛠️ Manual Setup
1. **Clone & Run (Windows)**:
   ```powershell
   git clone https://github.com/hming28/SoulMusic.git && cd SoulMusic && .\run.bat
   ```
   *(Double-clicking `run.bat` automatically creates `.venv`, installs `requirements.txt`, downloads FFmpeg if missing, and starts SoulMusic.)*
2. **Command Line (Cross-platform)**:
   ```bash
   git clone https://github.com/hming28/SoulMusic.git
   cd SoulMusic
   pip install -r requirements.txt
   python soulmusic.py
   ```

---

## 💡 Usage Scenarios

### Scenario 1: Clipboard Auto-Detection
1. Click **Share ➔ Copy Link** on any song, album, or playlist in your music app.
2. SoulMusic automatically captures the link from your clipboard and resolves the metadata immediately.

### Scenario 2: Search & Batch Add
1. Type a track title or artist into the search bar and press **Enter**.
2. Select your desired match from the candidates panel to play immediately or add to queue.

### Scenario 3: Theme and Language Switching
- Click **`🌙` / `☀️`** on the top bar to toggle between Light and Dark modes.
- Click **`🌐 中文` / `🌐 EN`** to switch UI language between English and Chinese.

---

## ⌨️ Shortcuts Guide

| Key | Action | Description |
| :---: | :---: | :--- |
| **Space** | Play / Pause | Global shortcut; types normal space characters when search box is focused. |
| **Enter** | Search & Play | Triggers search when typing in the search box. |
| **Left Click Drag** | Seek / Volume | Click or drag on the progress bar or volume slider for real-time control. |

---

## 📁 Project Structure

```text
SoulMusic/
├── soulmusic.py             # Main v2.0.0 CustomTkinter application
├── install.ps1              # One-command Windows installer & launcher
├── install.sh               # One-command macOS/Linux installer & launcher
├── requirements.txt         # Core dependencies (customtkinter, Pillow, mutagen, etc.)
├── get_ffmpeg.ps1           # Automated FFmpeg build downloader
├── run.bat                  # One-click Windows launcher (.venv + deps + FFmpeg)
├── test_phase1.py           # Comprehensive unit test suite (20/20 passing)
├── test_integration.py      # End-to-end integration test
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
└── README.md                # Bilingual documentation
```

---

# 🇨🇳 中文说明

## 📖 项目简介

**SoulMusic** 是一款现代、免登录的桌面音乐伴侣播放器。

应用作为后台智能伴侣，**自动侦测并捕获在音频软件或网页中复制的歌曲、歌单与专辑分享链接**，在本地免登录解析元数据，通过多维智能打分算法秒级匹配最佳音源，进行流媒体播放与本地缓存。同时具备独立的歌曲搜索、队列抽屉管理、专辑批量解析与自适应深浅主题系统。

---

## 🔄 版本演进对比 (v1.0.0 vs v2.0.0)

| 核心维度 | v1.0.0 (当前稳定发布版) | v2.0.0 (进阶规划版) |
| :--- | :--- | :--- |
| **GUI 架构** | 轻量级原生 Tkinter + TTK（极低内存，~30MB） | 现代 CustomTkinter（圆角卡片、流体动效） |
| **主题方案** | 默认优雅白色主题 + 暗黑夜间主题（一键切换） | 原生深色/浅色自适应主题系统 |
| **封面展示** | 纯文本曲目与状态 | 支持高清专辑封面大图渲染（Pillow） |
| **链接支持** | Spotify 单曲链接 / 关键字手动搜索 | Spotify 单曲 + 歌单/专辑批量解析 + YouTube 链接 |
| **匹配算法** | 基础 YTMusic 歌曲检索 | 多维智能打分算法（过滤翻唱/伴奏，校验时长） |
| **播放模式** | 列表顺序播放 | 列表循环 / 单曲循环 / 随机播放 |
| **状态持久化** | 内存状态（随关随清） | 本地 JSON 持久化（记录配置与播放队列） |
| **缓存管理** | 本地全量缓存 | 具备 500MB 阈值自动清理机制 |
| **依赖环境** | 仅 4 个基础库（pygame, yt-dlp, ytmusicapi, pyperclip） | 增加 ctk, pillow, mutagen 增强库 |

---

## ✨ v2.0.0 核心特性

- 🖼️ **现代卡片式界面**：基于 CustomTkinter 构建，具备圆角卡片、流畅动效以及 Pillow 驱动的高清专辑封面渲染。
- 🎨 **自适应主题系统**：**默认优雅白色主题**，支持一键切换至暗黑主题，输入框背景与字体对比度清晰明亮。
- 🌐 **默认英文与双语切换**：启动默认英文，支持点击 `🌐 中文` 随时实时无缝切换至中文。
- 📦 **歌单/专辑批量解析**：支持复制 Spotify 歌单与专辑链接，一键批量解析并全量导入播放队列。
- 🎯 **多维智能音源匹配**：多维智能打分算法，自动过滤翻唱、伴奏、加速/慢速版本，校准歌曲时长。
- 🔀 **丰富播放模式**：支持列表循环（🔁）、单曲循环（🔂）与随机播放（🔀）。
- 💾 **状态与队列持久化**：本地 JSON 自动保存音量、置顶状态、播放队列与配置，重启软件无需重新配置。
- 🧹 **500MB 智能缓存管理**：动态监控音频缓存空间，提供 500MB 自动清理与一键清空功能。

---

## 🚀 快速上手

### ⚡ 一行命令下载并直接运行（推荐）
在任何一台新电脑上，只需执行一条命令即可自动完成下载、Python 环境检查（Windows 支持自动安装）、`.venv` 虚拟环境配置、依赖安装、FFmpeg 下载、创建桌面快捷方式并启动程序：

- **Windows (PowerShell)**：
  ```powershell
  irm https://raw.githubusercontent.com/hming28/SoulMusic/main/install.ps1 | iex
  ```
- **macOS / Linux (Bash)**：
  ```bash
  curl -fsSL https://raw.githubusercontent.com/hming28/SoulMusic/main/install.sh | bash
  ```

### 🛠️ 手动 / 本地运行
1. **一行克隆并启动（Windows）**：
   ```powershell
   git clone https://github.com/hming28/SoulMusic.git && cd SoulMusic && .\run.bat
   ```
   *（双击或运行 `run.bat` 会自动创建 `.venv`、安装 `requirements.txt`、补齐 FFmpeg 并启动程序。）*
2. **命令行启动**：
   ```bash
   pip install -r requirements.txt
   python soulmusic.py
   ```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
