# SoulMusic

SoulMusic 是一个基于 Python 的轻量桌面音乐伴侣播放器。

## 功能特性

- **剪贴板监听**：自动检测复制的音乐分享链接并解析。
- **免登录解析**：无需开发者 Key 即可快速解析歌曲元数据。
- **高音质流媒体播放**：基于优质网络音源自动匹配与流式缓存。
- **现代播放控制**：支持播放、暂停、停止、切歌、音量调节与进度拖拽。
- **快捷键支持**：空格键暂停/播放，回车键快捷搜索。

## 安装与运行

### 1. 安装依赖

`ash
pip install -r requirements.txt
`

### 2. 下载 FFmpeg（可选，用于音频转码）

Windows 用户可直接运行配套脚本：

`powershell
powershell -ExecutionPolicy Bypass -File .\get_ffmpeg.ps1
`

### 3. 启动程序

运行主程序：

`ash
python soulmusic.py
`

或双击运行 启动SoulMusic.bat。

## 开源协议

本项目采用 MIT 许可证。
