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
    print(f"Missing required dependency: {e}")
    sys.exit(1)

# Base directory and binary paths (dynamic relative path with fallback)
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() or "__file__" in globals() else os.path.abspath(os.getcwd())
FFPLAY_BIN = os.path.join(APP_DIR, "ffplay.exe")
FFMPEG_BIN = os.path.join(APP_DIR, "ffmpeg.exe")

if not os.path.exists(FFMPEG_BIN):
    for fallback_dir in [r"D:\Spotifast", os.path.join(os.path.dirname(APP_DIR), "Spotifast")]:
        cand = os.path.join(fallback_dir, "ffmpeg.exe")
        if os.path.exists(cand):
            FFMPEG_BIN = cand
            break
    if not os.path.exists(FFMPEG_BIN):
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            FFMPEG_BIN = which_ffmpeg

if not os.path.exists(FFPLAY_BIN):
    for fallback_dir in [r"D:\Spotifast", os.path.join(os.path.dirname(APP_DIR), "Spotifast")]:
        cand = os.path.join(fallback_dir, "ffplay.exe")
        if os.path.exists(cand):
            FFPLAY_BIN = cand
            break
    if not os.path.exists(FFPLAY_BIN):
        which_ffplay = shutil.which("ffplay")
        if which_ffplay:
            FFPLAY_BIN = which_ffplay

AUDIO_CACHE_DIR = os.path.join(APP_DIR, "cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# Initialize audio engine (pygame.mixer)
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2)
except Exception as e:
    print(f"pygame.mixer initialization error: {e}")

ytmusic = YTMusic()

# Spotify track regex pattern
SPOTIFY_TRACK_REGEX = re.compile(r"spotify(?::track:|(?:\.com/(?:[a-zA-Z-]+/)?track/))([a-zA-Z0-9]+)")

# Internationalization dictionary (Default: English)
I18N = {
    "en": {
        "title": "SoulMusic - Music Companion Player",
        "ready": "Ready - Copy a Spotify track link or search below",
        "idle": "Status: Idle (Listening to clipboard...)",
        "search_btn": "🔍 Play / Search",
        "theme_dark": "🌙 Dark",
        "theme_light": "☀️ Light",
        "lang_toggle": "🌐 中文",
        "prev": "⏮ Prev",
        "play": "⏯ Play",
        "pause": "⏸ Pause",
        "resume": "▶ Resume",
        "stop": "⏹ Stop",
        "next": "⏭ Next",
        "volume": "🔊 Volume:",
        "hint": "💡 Shortcuts: Space = Play/Pause | Drag progress bar to seek & adjust volume",
        "detected_spotify": "Detected Spotify link, resolving...",
        "matching": "Matching best audio source: {query}...",
        "loading": "Loading: {query}",
        "found_audio": "Found: {title}, preparing high-quality audio...",
        "status_playing": "Status: Playing 🎵 ({title})",
        "status_paused": "Status: Paused ⏸",
        "status_stopped": "Status: Stopped ⏹",
        "status_finished": "Status: Finished 🏁",
        "err_resolve_spotify": "Failed to resolve Spotify link or track not found",
        "err_no_audio": "No playable audio found for: {query}",
        "err_fetch_audio": "Failed to fetch audio: {title}",
        "err_seek": "Failed to seek: {err}",
        "err_playback": "Playback failed: {err}",
        "err_match": "Matching failed: {err}",
        "loading_btn": "⏳ Loading",
    },
    "zh": {
        "title": "SoulMusic - 音乐伴侣播放器",
        "ready": "准备就绪 - 复制 Spotify 歌曲链接或在下方搜索",
        "idle": "状态: 待命 (监听剪贴板中...)",
        "search_btn": "🔍 播放 / 搜索",
        "theme_dark": "🌙 深色",
        "theme_light": "☀️ 浅色",
        "lang_toggle": "🌐 EN",
        "prev": "⏮ 上一首",
        "play": "⏯ 播放",
        "pause": "⏸ 暂停",
        "resume": "▶ 继续",
        "stop": "⏹ 停止",
        "next": "⏭ 下一首",
        "volume": "🔊 音量:",
        "hint": "💡 快捷键: 空格键暂停/继续 | 支持拖拽进度条跳转与实时音量调节",
        "detected_spotify": "侦测到 Spotify 链接，正在解析...",
        "matching": "正在匹配最佳音源: {query}...",
        "loading": "正在载入: {query}",
        "found_audio": "已找到: {title}，正在准备高音质音频...",
        "status_playing": "状态: 正在播放中 🎵 ({title})",
        "status_paused": "状态: 已暂停 ⏸",
        "status_stopped": "状态: 已停止 ⏹",
        "status_finished": "状态: 播放完毕 🏁",
        "err_resolve_spotify": "未能解析 Spotify 链接或歌曲不存在",
        "err_no_audio": "未找到可播放的音源: {query}",
        "err_fetch_audio": "获取音频失败: {title}",
        "err_seek": "跳转进度失败: {err}",
        "err_playback": "播放失败: {err}",
        "err_match": "匹配失败: {err}",
        "loading_btn": "⏳ 载入中",
    },
}


def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS with defensive bounds"""
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
    """Extract track_id and query Spotify public embed API for track metadata"""
    m = SPOTIFY_TRACK_REGEX.search(url_or_id)
    if not m:
        return None
    track_id = m.group(1)
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    # 1. Parse via public Embed JSON (free, no key needed, accurate duration)
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

    # 2. Fallback to standard track page title
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
        self.root.title("SoulMusic - Music Companion Player")
        self.root.geometry("540x295")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Default language: en (English)
        self.lang = "en"

        # Default theme mode: light (White theme)
        self.theme_mode = "light"

        # Thread synchronization and request ID
        self.lock = threading.RLock()
        self.play_request_id = 0

        # State variables
        self.current_song = tk.StringVar(value=self.t("ready"))
        self.status_text = tk.StringVar(value=self.t("idle"))

        self.is_playing = False
        self.is_paused = False
        self.is_seeking = False
        self.current_file = None
        self.total_duration = 0.0
        self.seek_offset_seconds = 0.0
        self.volume = 80

        # Playlist queue and index
        self.playlist = []
        self.current_index = -1

        # Thread-safe UI dispatch queue
        self.ui_queue = queue.Queue()

        # Clipboard & process handles
        self.last_clipboard = ""
        self.ffplay_proc = None

        # Build UI and apply default white theme
        self.setup_ui()
        self.apply_theme(self.theme_mode)

        # Window exit protection
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        atexit.register(self.force_cleanup)

        # Global hotkey protection: Space for Play/Pause
        self.root.bind_class("TButton", "<space>", self.on_spacebar)
        self.root.bind_class("Horizontal.TScale", "<space>", self.on_spacebar)
        self.root.bind("<space>", self.on_spacebar)

        # Start playback progress polling (every 200ms)
        self.root.after(200, self.update_playback_loop)

        # Start background clipboard listener
        self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.clipboard_thread.start()

    def t(self, key, **kwargs):
        """Translate a string key into the current language"""
        table = I18N.get(self.lang, I18N["en"])
        template = table.get(key, I18N["en"].get(key, key))
        if kwargs:
            try:
                return template.format(**kwargs)
            except Exception:
                return template
        return template

    def toggle_language(self):
        """Toggle between English and Chinese"""
        self.lang = "zh" if self.lang == "en" else "en"
        self.update_ui_language()

    def update_ui_language(self):
        """Update all UI text when language changes"""
        self.root.title(self.t("title"))
        if hasattr(self, "btn_lang"):
            self.btn_lang.config(text=self.t("lang_toggle"))
        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text=self.t("theme_dark" if self.theme_mode == "light" else "theme_light"))
        if hasattr(self, "search_btn"):
            self.search_btn.config(text=self.t("search_btn"))
        if hasattr(self, "btn_prev"):
            self.btn_prev.config(text=self.t("prev"))
        if hasattr(self, "btn_stop"):
            self.btn_stop.config(text=self.t("stop"))
        if hasattr(self, "btn_next"):
            self.btn_next.config(text=self.t("next"))
        if hasattr(self, "vol_label"):
            self.vol_label.config(text=self.t("volume"))
        if hasattr(self, "hint_label"):
            self.hint_label.config(text=self.t("hint"))

        # Update play/pause button state
        if hasattr(self, "btn_play_pause"):
            if self.is_playing:
                if self.is_paused:
                    self.btn_play_pause.config(text=self.t("resume"))
                else:
                    self.btn_play_pause.config(text=self.t("pause"))
            else:
                self.btn_play_pause.config(text=self.t("play"))

        # Update default status text if not actively playing
        if not self.is_playing and not self.is_paused:
            if not self.current_file:
                self.current_song.set(self.t("ready"))
                self.status_text.set(self.t("idle"))
            else:
                self.status_text.set(self.t("status_stopped"))

    def toggle_theme(self):
        """Toggle between Light and Dark themes"""
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text=self.t("theme_dark" if self.theme_mode == "light" else "theme_light"))
        self.apply_theme(self.theme_mode)

    def apply_theme(self, mode):
        """Apply theme styling with precise color bounds for entries and labels"""
        self.theme_mode = mode
        style = ttk.Style()
        style.theme_use("clam")

        if mode == "light":
            # Clean Modern White Theme (Default)
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
            # Modern Dark Theme
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
            entry_fg = "#FFFFFF"
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

        # 1. Track title display
        title_label = ttk.Label(
            main_frame,
            textvariable=self.current_song,
            style="Song.TLabel",
            wraplength=510,
            justify=tk.CENTER,
            anchor="center",
        )
        title_label.pack(fill=tk.X, pady=(0, 2))

        # 2. Status message label
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_text,
            style="Status.TLabel",
            wraplength=510,
            justify=tk.CENTER,
            anchor="center",
        )
        status_label.pack(fill=tk.X, pady=(0, 8))

        # 3. Search and top controls bar
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))

        # Search entry box
        self.search_entry = tk.Entry(
            search_frame,
            font=("Segoe UI", 9),
            relief="flat",
            highlightthickness=1,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        self.search_entry.bind("<Return>", lambda e: self.on_manual_search())

        self.search_btn = ttk.Button(search_frame, text=self.t("search_btn"), command=self.on_manual_search)
        self.search_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Theme toggle button
        self.btn_theme = ttk.Button(
            search_frame,
            text=self.t("theme_dark" if self.theme_mode == "light" else "theme_light"),
            width=7,
            command=self.toggle_theme,
        )
        self.btn_theme.pack(side=tk.LEFT, padx=(0, 4))

        # Language toggle button
        self.btn_lang = ttk.Button(
            search_frame,
            text=self.t("lang_toggle"),
            width=6,
            command=self.toggle_language,
        )
        self.btn_lang.pack(side=tk.RIGHT)

        # 4. Progress bar and time labels
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(2, 6))

        self.time_curr_label = ttk.Label(progress_frame, text="00:00", style="Time.TLabel", width=6, anchor="e")
        self.time_curr_label.pack(side=tk.LEFT, padx=(0, 6))

        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL)
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_scale.bind("<ButtonPress-1>", self.on_seek_press)
        self.progress_scale.bind("<B1-Motion>", self.on_seek_motion)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_seek_release)

        self.time_total_label = ttk.Label(progress_frame, text="00:00", style="Time.TLabel", width=6, anchor="w")
        self.time_total_label.pack(side=tk.LEFT, padx=(6, 0))

        # 5. Playback control buttons
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(4, 6))

        self.btn_prev = ttk.Button(controls_frame, text=self.t("prev"), width=9, command=self.play_prev)
        self.btn_prev.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_play_pause = ttk.Button(controls_frame, text=self.t("play"), width=9, command=self.toggle_play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_stop = ttk.Button(controls_frame, text=self.t("stop"), width=9, command=self.stop_music)
        self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        self.btn_next = ttk.Button(controls_frame, text=self.t("next"), width=9, command=self.play_next)
        self.btn_next.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)

        # 6. Volume bar
        vol_frame = ttk.Frame(main_frame)
        vol_frame.pack(fill=tk.X, pady=(4, 6))

        self.vol_label = ttk.Label(vol_frame, text=self.t("volume"))
        self.vol_label.pack(side=tk.LEFT, padx=(0, 6))

        self.vol_scale = ttk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume)
        self.vol_scale.set(self.volume)
        self.vol_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.vol_val_label = ttk.Label(vol_frame, text=f"{self.volume}%", width=5, anchor="e")
        self.vol_val_label.pack(side=tk.LEFT, padx=(6, 0))

        # 7. Hotkey instructions
        self.hint_label = ttk.Label(
            main_frame,
            text=self.t("hint"),
            style="Hint.TLabel",
            anchor="center",
        )
        self.hint_label.pack(side=tk.BOTTOM, fill=tk.X)

    # ----------------- Volume and Seek Controls -----------------
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
            self.status_text.set(self.t("err_seek", err=e))

    def get_current_seconds(self):
        if not self.is_playing:
            return self.seek_offset_seconds
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self.seek_offset_seconds
        return self.seek_offset_seconds + (pos_ms / 1000.0)

    # ----------------- Playback Control -----------------
    def on_spacebar(self, event=None):
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
                self.btn_play_pause.config(text=self.t("pause"))
                self.status_text.set(self.t("status_playing", title=self.current_song.get()))
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.btn_play_pause.config(text=self.t("resume"))
                self.status_text.set(self.t("status_paused"))
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
        self.btn_play_pause.config(text=self.t("play"))
        self.status_text.set(self.t("status_stopped"))

    def play_prev(self):
        with self.lock:
            if not self.playlist:
                if self.current_file:
                    self.seek_to(0.0)
                return

            curr_sec = self.get_current_seconds()
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

        self.btn_play_pause.config(text=self.t("loading_btn"))
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
            self.status_text.set(self.t("status_finished"))

    def safe_ui_call(self, fn, *args, **kwargs):
        """Dispatch task to UI main thread queue"""
        self.ui_queue.put(lambda: fn(*args, **kwargs))

    def update_playback_loop(self):
        # 1. Process tasks from background threads
        while not self.ui_queue.empty():
            try:
                task = self.ui_queue.get_nowait()
                task()
            except Exception as e:
                print(f"UI task error: {e}")

        # 2. Poll playback progress
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

    # ----------------- Window Exit Cleanup -----------------
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

    # ----------------- Search and Stream Download -----------------
    def on_manual_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        if SPOTIFY_TRACK_REGEX.search(query):
            self.safe_ui_call(self.status_text.set, self.t("detected_spotify"))
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
                        self.safe_ui_call(self.status_text.set, self.t("detected_spotify"))
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
            self.safe_ui_call(self.status_text.set, self.t("err_resolve_spotify"))

    def resolve_and_play(self, query, hint_duration=0.0):
        self.safe_ui_call(self.status_text.set, self.t("matching", query=query))
        self.safe_ui_call(self.current_song.set, self.t("loading", query=query))

        with self.lock:
            self.play_request_id += 1
            req_id = self.play_request_id

        try:
            results = ytmusic.search(query, filter="songs")
            if not results:
                results = ytmusic.search(query)

            if not results:
                self.safe_ui_call(self.status_text.set, self.t("err_no_audio", query=query))
                self.safe_ui_call(self.btn_play_pause.config, text=self.t("play"))
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
            self.safe_ui_call(self.status_text.set, self.t("err_match", err=e))
            self.safe_ui_call(self.btn_play_pause.config, text=self.t("play"))
            print(f"Error: {e}")

    def _resolve_and_play_track(self, track, req_id=None):
        video_id = track.get("video_id")
        display_title = track.get("display")

        with self.lock:
            if req_id is not None and req_id != self.play_request_id:
                return

        self.safe_ui_call(self.status_text.set, self.t("found_audio", title=display_title))
        self.safe_ui_call(self.current_song.set, display_title)

        target_file = self.get_or_download_audio(video_id)

        with self.lock:
            if req_id is not None and req_id != self.play_request_id:
                return

        if not target_file:
            self.safe_ui_call(self.status_text.set, self.t("err_fetch_audio", title=display_title))
            self.safe_ui_call(self.btn_play_pause.config, text=self.t("play"))
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

        # If cache exists in non-mp3 format, transcode to 192k mp3
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

        # Otherwise download with yt-dlp and extract 192k mp3
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(AUDIO_CACHE_DIR, f"{video_id}.%(ext)s"),
                "ffmpeg_location": os.path.dirname(FFMPEG_BIN) if os.path.exists(FFMPEG_BIN) else (APP_DIR if os.path.exists(os.path.join(APP_DIR, "ffmpeg.exe")) else None),
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

            # Get duration
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

            self.btn_play_pause.config(text=self.t("pause"))
            display_title = self.current_song.get()
            self.status_text.set(self.t("status_playing", title=display_title))
        except Exception as e:
            self.status_text.set(self.t("err_playback", err=e))
            self.is_playing = False
            self.is_paused = False
            self.btn_play_pause.config(text=self.t("play"))


# Backward compatibility alias
SpotifastCompanionApp = SoulMusicApp


if __name__ == "__main__":
    root = tk.Tk()
    app = SoulMusicApp(root)
    root.mainloop()
