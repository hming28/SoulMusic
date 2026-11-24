import os
import sys
import time
import shutil
import threading
import subprocess
import urllib.request
import re
import json
import atexit
import queue
import tkinter as tk
from tkinter import ttk

try:
    import pygame
    from ytmusicapi import YTMusic
    from yt_dlp import YoutubeDL
    import pyperclip
except ImportError as e:
    print(f"缺少必要依赖: {e}")
    sys.exit(1)

# 基础目录与二进制路径 (支持动态相对路径、本地目录与系统环境变量 fallback)
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() or "__file__" in globals() else os.path.abspath(os.getcwd())
FFPLAY_BIN = os.path.join(APP_DIR, "ffplay.exe")
FFMPEG_BIN = os.path.join(APP_DIR, "ffmpeg.exe")

if not os.path.exists(FFMPEG_BIN):
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        FFMPEG_BIN = which_ffmpeg

if not os.path.exists(FFPLAY_BIN):
    which_ffplay = shutil.which("ffplay")
    if which_ffplay:
        FFPLAY_BIN = which_ffplay

AUDIO_CACHE_DIR = os.path.join(APP_DIR, "cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# 初始化底层音频引擎 (pygame.mixer)
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2)
except Exception as e:
    print(f"pygame.mixer 初始化异常: {e}")

ytmusic = YTMusic()

# Spotify 单曲匹配正则 (支持国际化前缀、带参数链接与 spotify:track: URI)
SPOTIFY_TRACK_REGEX = re.compile(r"spotify(?::track:|(?:\.com/(?:[a-zA-Z-]+/)?track/))([a-zA-Z0-9]+)")


def format_time(seconds):
    """格式化秒数为 MM:SS 或 HH:MM:SS，支持异常输入防御"""
    try:
        val = float(seconds)
        if val != val or val < 0 or val == float("inf"):
            val = 0.0
    except (TypeError, ValueError):
        val = 0.0
    m, s = divmod(int(val), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def parse_spotify_track_info(url_or_id):
    """从 Spotify 链接或 URI 提取 track_id，并通过公开 Embed 接口精准解析曲名、歌手与时长"""
    m = SPOTIFY_TRACK_REGEX.search(url_or_id)
    if not m:
        return None
    track_id = m.group(1)
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    # 1. 优先通过公开 Embed 结构化 JSON 解析（免登录、免 key、带精确时长）
    try:
        req = urllib.request.Request(
            embed_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="ignore")
        match_json = re.search(r'<script id=[\"\']__NEXT_DATA__[\"\'][^>]*>(.*?)</script>', html)
        if match_json:
            data = json.loads(match_json.group(1))
            props = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
            title = props.get("name") or props.get("title")
            artists = ", ".join([a.get("name") for a in props.get("artists", []) if "name" in a])
            dur_ms = props.get("duration", 0)
            dur_sec = (dur_ms / 1000.0) if dur_ms else 0.0
            if title:
                display = f"{artists} - {title}" if artists else title
                return {
                    "track_id": track_id,
                    "title": title,
                    "artist": artists,
                    "display": display,
                    "duration": dur_sec,
                }
    except Exception:
        pass

    # 2. 备用通过标准 track 页面提取元数据并剔除常见后缀
    try:
        norm_url = f"https://open.spotify.com/track/{track_id}"
        req = urllib.request.Request(
            norm_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="ignore")
        t_m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        if t_m:
            raw = t_m.group(1).split("|")[0].strip()
            cleaned = re.sub(
                r"\s*-\s*(?:song(?:\s*,\s*lyrics)?(?:\s*,\s*and\s*music\s*video)?\s*by|single\s*by|album\s*by|ep\s*by).*",
                "",
                raw,
                flags=re.IGNORECASE,
            ).strip()
            if cleaned:
                return {
                    "track_id": track_id,
                    "title": cleaned,
                    "artist": "",
                    "display": cleaned,
                    "duration": 0.0,
                }
    except Exception:
        pass

    return None


class SoulMusicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SoulMusic - 音乐伴侣播放器")
        self.root.geometry("520x295")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # 默认主题模式: light (白色/浅色主题)
        self.theme_mode = "light"

        # 线程锁与请求序列号 (彻底解决多线程与快速切歌时音频覆盖的竞争条件)
        self.lock = threading.RLock()
        self.play_request_id = 0

        # 状态变量
        self.current_song = tk.StringVar(value="准备就绪 - 复制 Spotify 歌曲链接或在下方搜索")
        self.status_text = tk.StringVar(value="状态: 待命 (监听剪贴板中...)")

        self.is_playing = False
        self.is_paused = False
        self.is_seeking = False
        self.current_file = None
        self.total_duration = 0.0
        self.seek_offset_seconds = 0.0
        self.volume = 80

        # 播放队列与索引
        self.playlist = []  # 存储 track dict: {'title': ..., 'artist': ..., 'display': ..., 'video_id': ..., 'duration': ...}
        self.current_index = -1

        # 线程安全 UI 调度队列
        self.ui_queue = queue.Queue()

        # 剪贴板与历史记录
        self.last_clipboard = ""
        self.ffplay_proc = None

        # 构建界面并应用默认白色主题
        self.setup_ui()
        self.apply_theme(self.theme_mode)

        # 退出安全防护 (彻底解决后台残留发声与文件句柄锁定)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        atexit.register(self.force_cleanup)

        # 全局快捷键与控件焦点防护: 空格键播放/暂停 (焦点在输入框时不触发，在按钮时不重复触发)
        self.root.bind_class("TButton", "<space>", self.on_spacebar)
        self.root.bind_class("Horizontal.TScale", "<space>", self.on_spacebar)
        self.root.bind("<space>", self.on_spacebar)

        # 启动进度条平滑定时轮询 (每 200ms)
        self.root.after(200, self.update_playback_loop)

        # 启动后台剪贴板监听
        self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.clipboard_thread.start()

    def toggle_theme(self):
        """切换深色/浅色主题"""
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text="🌙 深色" if self.theme_mode == "light" else "☀️ 浅色")
        self.apply_theme(self.theme_mode)

    def apply_theme(self, mode):
        """应用主题配置，彻底解决暗黑模式下输入框白底白字问题"""
        self.theme_mode = mode
        style = ttk.Style()
        style.theme_use("clam")

        if mode == "light":
            # 浅色 / 白色主题 (Default White Theme)
            bg = "#F5F6F8"
            fg = "#1F2937"
            song_fg = "#15803D"
            status_fg = "#4B5563"
            time_fg = "#4B5563"
            hint_fg = "#6B7280"
            btn_bg = "#E5E7EB"
            btn_fg = "#111827"
            btn_hover = "#D1D5DB"
            entry_bg = "#FFFFFF"
            entry_fg = "#111827"
            entry_border = "#D1D5DB"
            trough = "#E5E7EB"
        else:
            # 深色 / 暗黑主题 (Dark Theme)
            bg = "#181818"
            fg = "#FFFFFF"
            song_fg = "#1DB954"
            status_fg = "#B3B3B3"
            time_fg = "#B3B3B3"
            hint_fg = "#777777"
            btn_bg = "#282828"
            btn_fg = "#FFFFFF"
            btn_hover = "#3E3E3E"
            entry_bg = "#282828"
            entry_fg = "#FFFFFF"     # 彻底修复暗黑模式下输入框文字白底白字问题
            entry_border = "#3E3E3E"
            trough = "#2E2E2E"

        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("Song.TLabel", background=bg, foreground=song_fg, font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background=bg, foreground=status_fg, font=("Segoe UI", 9))
        style.configure("Time.TLabel", background=bg, foreground=time_fg, font=("Consolas", 9))
        style.configure("Hint.TLabel", background=bg, foreground=hint_fg, font=("Segoe UI", 8))
        style.configure(
            "TButton",
            background=btn_bg,
            foreground=btn_fg,
            borderwidth=1,
            focusthickness=2,
            font=("Segoe UI", 9),
        )
        style.map("TButton", background=[("active", btn_hover), ("pressed", "#1DB954")])
        style.configure("Horizontal.TScale", background=bg, troughcolor=trough)

        if hasattr(self, "search_entry"):
            self.search_entry.configure(
                bg=entry_bg,
                fg=entry_fg,
                insertbackground=entry_fg,
                selectbackground="#1DB954",
                selectforeground="#FFFFFF",
                highlightbackground=entry_border,
                highlightcolor="#1DB954",
            )

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 歌曲标题显示
        title_label = ttk.Label(
            main_frame,
            textvariable=self.current_song,
            style="Song.TLabel",
            wraplength=490,
            justify=tk.CENTER,
            anchor="center",
        )
        title_label.pack(fill=tk.X, pady=(0, 2))

        # 2. 状态标签
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_text,
            style="Status.TLabel",
            wraplength=490,
            justify=tk.CENTER,
            anchor="center",
        )
        status_label.pack(fill=tk.X, pady=(0, 8))

        # 3. 搜索与手动播放栏
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))

        # 搜索输入框 (使用精准色彩控制的 Entry 控件，防止系统主题渲染冲突)
        self.search_entry = tk.Entry(
            search_frame,
            font=("Segoe UI", 9),
            relief="flat",
            highlightthickness=1,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        self.search_entry.bind("<Return>", lambda e: self.on_manual_search())

        self.search_btn = ttk.Button(search_frame, text="🔍 播放 / 搜索", command=self.on_manual_search)
        self.search_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 主题切换按钮
        self.btn_theme = ttk.Button(
            search_frame,
            text="🌙 深色" if self.theme_mode == "light" else "☀️ 浅色",
            width=7,
            command=self.toggle_theme,
        )
        self.btn_theme.pack(side=tk.RIGHT)

        # 4. 进度条与播放时间
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(2, 6))

        self.time_curr_label = ttk.Label(progress_frame, text="00:00", style="Time.TLabel", width=6, anchor="e")
        self.time_curr_label.pack(side=tk.LEFT, padx=(0, 6))

        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL)
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # 绑定进度条事件: 鼠标按下、拖拽、松开精准跳转
        self.progress_scale.bind("<ButtonPress-1>", self.on_seek_press)
        self.progress_scale.bind("<B1-Motion>", self.on_seek_motion)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_seek_release)

        self.time_total_label = ttk.Label(progress_frame, text="00:00", style="Time.TLabel", width=6, anchor="w")
        self.time_total_label.pack(side=tk.LEFT, padx=(6, 0))

        # 5. 标准控制栏 (上一首 / 播放暂停 / 停止 / 下一首)
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(4, 6))

        self.btn_prev = ttk.Button(controls_frame, text="⏮ 上一首", width=9, command=self.play_prev)
        self.btn_prev.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_play_pause = ttk.Button(controls_frame, text="⏯ 播放", width=9, command=self.toggle_play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_stop = ttk.Button(controls_frame, text="⏹ 停止", width=9, command=self.stop_music)
        self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_next = ttk.Button(controls_frame, text="⏭ 下一首", width=9, command=self.play_next)
        self.btn_next.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        # 6. 音量调节栏 (实时毫秒级响应)
        vol_frame = ttk.Frame(main_frame)
        vol_frame.pack(fill=tk.X, pady=(4, 6))

        vol_label = ttk.Label(vol_frame, text="🔊 音量:")
        vol_label.pack(side=tk.LEFT, padx=(0, 6))

        self.vol_scale = ttk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume)
        self.vol_scale.set(self.volume)
        self.vol_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.vol_val_label = ttk.Label(vol_frame, text=f"{self.volume}%", width=5, anchor="e")
        self.vol_val_label.pack(side=tk.LEFT, padx=(6, 0))

        # 7. 快捷键与使用提示
        hint_label = ttk.Label(
            main_frame,
            text="💡 快捷键: 空格键暂停/继续 | 支持拖拽进度条跳转与实时音量调节",
            style="Hint.TLabel",
            anchor="center",
        )
        hint_label.pack(side=tk.BOTTOM, fill=tk.X)

    # ----------------- 音量与 Seek 控制 -----------------
    def set_volume(self, val):
        self.volume = int(float(val))
        if hasattr(self, "vol_val_label"):
            self.vol_val_label.config(text=f"{self.volume}%")
        try:
            pygame.mixer.music.set_volume(self.volume / 100.0)
        except Exception:
            pass

    def on_seek_press(self, event):
        if not self.current_file or self.total_duration <= 0:
            return
        self.is_seeking = True
        width = self.progress_scale.winfo_width()
        if width > 0:
            target_sec = max(0.0, min(1.0, event.x / width)) * self.total_duration
            self.progress_scale.set(target_sec)
            self.time_curr_label.config(text=format_time(target_sec))

    def on_seek_motion(self, event):
        if not self.is_seeking or self.total_duration <= 0:
            return
        width = self.progress_scale.winfo_width()
        if width > 0:
            target_sec = max(0.0, min(1.0, event.x / width)) * self.total_duration
            self.progress_scale.set(target_sec)
            self.time_curr_label.config(text=format_time(target_sec))

    def on_seek_release(self, event):
        if not self.is_seeking:
            return
        try:
            width = self.progress_scale.winfo_width()
            if width > 0:
                target_sec = max(0.0, min(1.0, event.x / width)) * self.total_duration
            else:
                target_sec = self.progress_scale.get()
            self.seek_to(target_sec)
        finally:
            self.is_seeking = False

    def seek_to(self, target_seconds):
        if not self.current_file or self.total_duration <= 0:
            return
        target = max(0.0, min(max(0.0, self.total_duration - 0.1), float(target_seconds)))
        self.seek_offset_seconds = target
        self.progress_scale.set(target)
        self.time_curr_label.config(text=format_time(target))

        try:
            if self.is_paused:
                pygame.mixer.music.play(start=target)
                pygame.mixer.music.pause()
            elif self.is_playing:
                pygame.mixer.music.play(start=target)
            else:
                self.start_playback(self.current_file, start_sec=target)
        except Exception as e:
            self.status_text.set(f"跳转进度失败: {e}")

    def get_current_seconds(self):
        if not self.is_playing:
            return self.seek_offset_seconds
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self.seek_offset_seconds
        return self.seek_offset_seconds + (pos_ms / 1000.0)

    # ----------------- 基础播放控制 -----------------
    def on_spacebar(self, event=None):
        # 如果当前焦点在输入框中，正常输入空格，不拦截
        widget = getattr(event, "widget", None) if event else None
        focused = self.root.focus_get()
        if (
            widget == self.search_entry
            or isinstance(widget, (ttk.Entry, tk.Entry))
            or focused == self.search_entry
            or isinstance(focused, (ttk.Entry, tk.Entry))
        ):
            return None
        self.toggle_play_pause()
        return "break"

    def toggle_play_pause(self):
        if not self.current_file:
            with self.lock:
                if self.playlist:
                    target_idx = self.current_index if (0 <= self.current_index < len(self.playlist)) else 0
                    self.play_track_at_index(target_idx)
            return

        if self.is_playing:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.btn_play_pause.config(text="⏸ 暂停")
                self.status_text.set(f"状态: 正在播放中 🎵 ({self.current_song.get()})")
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.btn_play_pause.config(text="▶ 继续")
                self.status_text.set("状态: 已暂停 ⏸")
        else:
            current_sec = self.progress_scale.get()
            self.start_playback(self.current_file, start_sec=current_sec)

    def stop_music(self):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.seek_offset_seconds = 0.0
        self.progress_scale.set(0)
        self.time_curr_label.config(text="00:00")
        self.btn_play_pause.config(text="▶ 播放")
        self.status_text.set("状态: 已停止 ⏹")

    def play_prev(self):
        with self.lock:
            if not self.playlist:
                if self.current_file:
                    self.seek_to(0.0)
                return

            curr_sec = self.get_current_seconds()
            # 若当前曲目已播放超过 3 秒，按上一首习惯回到开头
            if curr_sec > 3.0 or self.current_index <= 0:
                self.seek_to(0.0)
            else:
                prev_idx = max(0, self.current_index - 1)
                self.play_track_at_index(prev_idx)

    def play_next(self):
        with self.lock:
            if not self.playlist:
                return
            next_idx = (self.current_index + 1) % len(self.playlist)
            self.play_track_at_index(next_idx)

    def play_track_at_index(self, index):
        with self.lock:
            if index < 0 or index >= len(self.playlist):
                return
            self.current_index = index
            track = self.playlist[index]
            self.play_request_id += 1
            req_id = self.play_request_id

        # 重置视觉状态并异步载入音源
        self.btn_play_pause.config(text="⏳ 载入中")
        self.progress_scale.set(0)
        self.time_curr_label.config(text="00:00")
        threading.Thread(target=self._resolve_and_play_track, args=(track, req_id), daemon=True).start()

    def on_track_finished(self):
        self.is_playing = False
        self.is_paused = False
        if self.playlist and len(self.playlist) > 1:
            self.play_next()
        else:
            self.stop_music()
            self.status_text.set("状态: 播放完毕 🏁")

    def safe_ui_call(self, fn, *args, **kwargs):
        """线程安全地向 UI 主线程队列投递任务"""
        self.ui_queue.put(lambda: fn(*args, **kwargs))

    def update_playback_loop(self):
        # 1. 优先处理来自后台线程的 UI 刷新任务
        while not self.ui_queue.empty():
            try:
                task = self.ui_queue.get_nowait()
                task()
            except Exception as e:
                print(f"UI 任务执行异常: {e}")

        # 2. 轮询音频播放进度
        try:
            if self.is_playing and not self.is_paused:
                busy = pygame.mixer.music.get_busy()
                pos_ms = pygame.mixer.music.get_pos()

                if not busy and pos_ms == -1:
                    self.on_track_finished()
                elif not self.is_seeking and self.total_duration > 0:
                    current_sec = self.seek_offset_seconds + max(0.0, pos_ms / 1000.0)
                    current_sec = min(current_sec, self.total_duration)
                    self.progress_scale.set(current_sec)
                    self.time_curr_label.config(text=format_time(current_sec))
        except Exception:
            pass
        finally:
            self.root.after(200, self.update_playback_loop)

    # ----------------- 窗口析构与清理 -----------------
    def on_window_close(self):
        self.force_cleanup()
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def force_cleanup(self):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.quit()
        except Exception:
            pass
        if hasattr(self, "ffplay_proc") and self.ffplay_proc:
            try:
                self.ffplay_proc.terminate()
            except Exception:
                pass

    # ----------------- 搜索与音源下载/播放 -----------------
    def on_manual_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        if SPOTIFY_TRACK_REGEX.search(query):
            self.safe_ui_call(self.status_text.set, "侦测到 Spotify 链接，正在解析...")
            threading.Thread(target=self.resolve_spotify_url, args=(query,), daemon=True).start()
        else:
            threading.Thread(target=self.resolve_and_play, args=(query,), daemon=True).start()

    def monitor_clipboard(self):
        while True:
            time.sleep(1.0)
            try:
                clip = pyperclip.paste().strip()
                if clip and clip != self.last_clipboard:
                    self.last_clipboard = clip
                    if SPOTIFY_TRACK_REGEX.search(clip):
                        self.safe_ui_call(self.status_text.set, "侦测到 Spotify 链接，正在解析...")
                        threading.Thread(target=self.resolve_spotify_url, args=(clip,), daemon=True).start()
            except Exception:
                pass

    def resolve_spotify_url(self, url):
        info = parse_spotify_track_info(url)
        if info:
            search_query = info.get("display") or info.get("title")
            duration = info.get("duration", 0.0)
            self.resolve_and_play(search_query, hint_duration=duration)
        else:
            self.safe_ui_call(self.status_text.set, "未能解析 Spotify 链接或歌曲不存在")

    def resolve_and_play(self, query, hint_duration=0.0):
        self.safe_ui_call(self.status_text.set, f"正在匹配最佳音源: {query}...")
        self.safe_ui_call(self.current_song.set, f"正在载入: {query}")

        with self.lock:
            self.play_request_id += 1
            req_id = self.play_request_id

        try:
            results = ytmusic.search(query, filter="songs")
            if not results:
                results = ytmusic.search(query)

            if not results:
                self.safe_ui_call(self.status_text.set, f"未找到可播放的音源: {query}")
                self.safe_ui_call(self.btn_play_pause.config, text="▶ 播放")
                return

            best_song = results[0]
            video_id = best_song.get("videoId")
            title = best_song.get("title")
            artist = ", ".join([a["name"] for a in best_song.get("artists", []) if "name" in a]) if "artists" in best_song else ""
            display_title = f"{artist} - {title}" if artist else title

            duration = hint_duration
            if not duration and "duration_seconds" in best_song:
                try:
                    duration = float(best_song.get("duration_seconds", 0.0))
                except Exception:
                    pass

            track = {
                "title": title,
                "artist": artist,
                "display": display_title,
                "video_id": video_id,
                "duration": duration,
            }

            with self.lock:
                found_idx = -1
                for idx, item in enumerate(self.playlist):
                    if item.get("video_id") == video_id:
                        found_idx = idx
                        break
                if found_idx >= 0:
                    self.current_index = found_idx
                else:
                    self.playlist.append(track)
                    self.current_index = len(self.playlist) - 1

            self._resolve_and_play_track(track, req_id)
        except Exception as e:
            self.safe_ui_call(self.status_text.set, f"匹配失败: {e}")
            self.safe_ui_call(self.btn_play_pause.config, text="▶ 播放")
            print(f"Error: {e}")

    def _resolve_and_play_track(self, track, req_id=None):
        video_id = track.get("video_id")
        display_title = track.get("display")

        with self.lock:
            if req_id is not None and req_id != self.play_request_id:
                return

        self.safe_ui_call(self.status_text.set, f"已找到: {display_title}，正在准备高音质音频...")
        self.safe_ui_call(self.current_song.set, display_title)

        target_file = self.get_or_download_audio(video_id)

        with self.lock:
            if req_id is not None and req_id != self.play_request_id:
                return

        if not target_file:
            self.safe_ui_call(self.status_text.set, f"获取音频失败: {display_title}")
            self.safe_ui_call(self.btn_play_pause.config, text="▶ 播放")
            return

        hint_duration = track.get("duration", 0.0)
        self.safe_ui_call(self.start_playback, target_file, 0.0, hint_duration)

    def get_or_download_audio(self, video_id):
        if not video_id or not isinstance(video_id, str):
            return None
        video_id = video_id.strip()
        if not video_id:
            return None

        mp3_file = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.mp3")
        if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
            return mp3_file

        # 如果存在非 mp3 格式的缓存，使用 ffmpeg 极速转码为标准 mp3
        for ext in ["webm", "m4a", "opus", "wav"]:
            cand = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.{ext}")
            if os.path.exists(cand) and os.path.getsize(cand) > 10000:
                cmd = [
                    FFMPEG_BIN,
                    "-y",
                    "-i",
                    cand,
                    "-vn",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    mp3_file,
                ]
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
                    return mp3_file

        # 否则通过 yt-dlp 下载并自动提取为 192k mp3
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(AUDIO_CACHE_DIR, f"{video_id}.%(ext)s"),
                "ffmpeg_location": APP_DIR if os.path.exists(os.path.join(APP_DIR, "ffmpeg.exe")) else None,
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

            if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
                return mp3_file
        except Exception as e:
            print(f"yt-dlp download error: {e}")

        return None

    def start_playback(self, filepath, start_sec=0.0, hint_duration=0.0):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(self.volume / 100.0)

            # 获取精准音频总时长 (优先使用元数据，其次使用 pygame Sound 解码)
            if hint_duration and hint_duration > 0:
                self.total_duration = float(hint_duration)
            else:
                try:
                    snd = pygame.mixer.Sound(filepath)
                    self.total_duration = float(snd.get_length())
                    del snd
                except Exception:
                    if not self.total_duration or self.total_duration <= 0:
                        self.total_duration = 180.0

            scale_max = max(1.0, self.total_duration)
            self.progress_scale.config(to=scale_max)
            self.time_total_label.config(text=format_time(self.total_duration))

            self.seek_offset_seconds = start_sec
            pygame.mixer.music.play(start=start_sec)
            self.is_playing = True
            self.is_paused = False
            self.current_file = filepath

            self.btn_play_pause.config(text="⏸ 暂停")
            display_title = self.current_song.get()
            self.status_text.set(f"状态: 正在播放中 🎵 ({display_title})")
        except Exception as e:
            self.status_text.set(f"播放失败: {e}")
            self.is_playing = False
            self.is_paused = False
            self.btn_play_pause.config(text="▶ 播放")


# 向后兼容别名
SpotifastCompanionApp = SoulMusicApp


if __name__ == "__main__":
    root = tk.Tk()
    app = SoulMusicApp(root)
    root.mainloop()
