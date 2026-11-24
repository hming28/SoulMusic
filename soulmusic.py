import os
import sys
import re
import json
import time
import random
import logging
import threading
import subprocess
import urllib.request
import atexit
import queue
import shutil
from io import BytesIO
from pathlib import Path

# Base directory & logging configuration
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() or "__file__" in globals() else os.path.abspath(os.getcwd())
LOG_FILE = os.path.join(APP_DIR, "soulmusic.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("soulmusic")

try:
    import customtkinter as ctk
    import tkinter as tk
    import pygame
    from ytmusicapi import YTMusic
    from yt_dlp import YoutubeDL
    import pyperclip
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Optional enhanced dependencies (Cover Art & Fast Duration)
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from mutagen.mp3 import MP3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# Paths & binaries
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
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
QUEUE_FILE = os.path.join(APP_DIR, "queue.json")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# Adaptive Theme Palettes (Light, Dark)
COLOR_BG = ("#F8F9FA", "#121212")
COLOR_SURFACE = ("#FFFFFF", "#181818")
COLOR_ELEVATED = ("#EEF2F6", "#242424")
COLOR_INPUT = ("#FFFFFF", "#2A2A2A")
COLOR_BORDER = ("#D1D5DB", "#3A3A3A")
COLOR_HOVER = ("#E2E8F0", "#333333")
COLOR_GREEN = "#1DB954"
COLOR_GREEN_HOVER = "#1ED760"
COLOR_TEXT = ("#111827", "#FFFFFF")
COLOR_SUBTEXT = ("#4B5563", "#B3B3B3")
COLOR_MUTED = ("#9CA3AF", "#7A7A7A")
COLOR_DANGER = ("#DC2626", "#E5534B")

# URL Matching Patterns
SPOTIFY_TRACK_REGEX = re.compile(
    r"spotify(?::track:|(?:\.com/(?:[a-zA-Z-]+/)?track/))([a-zA-Z0-9]+)"
)
SPOTIFY_COLLECTION_REGEX = re.compile(
    r"spotify(?::(playlist|album):|(?:\.com/(?:[a-zA-Z-]+/)?(playlist|album)/))([a-zA-Z0-9]+)"
)
YOUTUBE_URL_REGEX = re.compile(
    r"(?:youtube\.com/watch\?.*?v=|youtu\.be/|music\.youtube\.com/watch\?.*?v=)([a-zA-Z0-9_-]{11})"
)

DEFAULT_CONFIG = {
    "volume": 80,
    "muted": False,
    "always_on_top": True,
    "clipboard_enabled": True,
    "clipboard_mode": "play",  # "play" or "queue"
    "play_mode": "list",       # "list" | "one" | "shuffle"
    "cache_limit_mb": 500,
    "lang": "en",              # Default English
    "theme_mode": "light",     # Default Light / White theme
}

PENALTY_KEYWORDS = ("karaoke", "instrumental", "slowed", "sped up", "8d audio", "nightcore", "cover", "live")

# Internationalization Dictionary
I18N = {
    "en": {
        "title": "SoulMusic",
        "pin_on": "📌 Pin",
        "pin_off": "📌 Pin",
        "clip_on": "📋 Clip",
        "clip_off": "📋 Clip",
        "clip_mode_play": "▶ Auto",
        "clip_mode_queue": "+ Queue",
        "lang_toggle": "🌐 中文",
        "cache_prefix": "Cache",
        "queue_btn": "Queue ({count})",
        "queue_title": "Playback Queue ({count} tracks)",
        "queue_empty": "Queue is empty. Copy Spotify link or search song above.",
        "clear_queue": "Clear Queue",
        "search_placeholder": "Paste Spotify/YouTube link, or type song title...",
        "search_btn": "🔍 Play / Search",
        "ready": "Ready",
        "ready_sub": "Copy Spotify / YouTube link, or search song above",
        "status_idle": "Idle · Listening to clipboard",
        "status_clip_on": "Clipboard listener started",
        "status_clip_off": "Clipboard listener paused",
        "status_clip_mode_q": "Clipboard mode: Auto add to queue",
        "status_clip_mode_p": "Clipboard mode: Instant play",
        "status_playing": "Playing",
        "status_paused": "Paused",
        "status_stopped": "Stopped",
        "status_finished": "Finished",
        "play_btn": "▶ Play",
        "pause_btn": "⏸ Pause",
        "resume_btn": "▶ Resume",
        "play": "▶ Play",
        "pause": "⏸ Pause",
        "resume": "▶ Resume",
        "loading_btn": "⏳ Loading",
        "mode_list": "🔁 Loop All",
        "mode_one": "🔂 Loop One",
        "mode_shuffle": "🔀 Shuffle",
        "search_results_title": "Search Results: {query}",
        "close_results": "Close Results",
        "no_results": "No tracks found for '{query}'",
        "add_queue": "+ Queue",
        "resolving_spotify_track": "Resolving Spotify track link...",
        "resolving_spotify_coll": "Resolving Spotify collection...",
        "resolving_youtube": "Resolving YouTube link...",
        "searching": "Searching: {query}...",
        "found_candidates": "Found {count} results. Click Play or + Queue.",
        "preparing_cache": "Preparing audio stream...",
        "cache_cleared": "Cache cleared ({count} files removed)",
        "cache_already_empty": "Cache is clean",
    },
    "zh": {
        "title": "SoulMusic - 音乐伴侣播放器",
        "pin_on": "📌 置顶",
        "pin_off": "📌 置顶",
        "clip_on": "📋 监听",
        "clip_off": "📋 监听",
        "clip_mode_play": "▶ 自动",
        "clip_mode_queue": "+ 队列",
        "lang_toggle": "🌐 EN",
        "cache_prefix": "缓存",
        "queue_btn": "队列 ({count})",
        "queue_title": "播放队列 ({count} 首)",
        "queue_empty": "队列为空，复制 Spotify 链接或在上方搜索添加歌曲",
        "clear_queue": "清空队列",
        "search_placeholder": "粘贴 Spotify/YouTube 链接，或输入歌名搜索...",
        "search_btn": "🔍 播放 / 搜索",
        "ready": "准备就绪",
        "ready_sub": "复制 Spotify / YouTube 链接，或在上方输入歌名",
        "status_idle": "待命 · 剪贴板监听中",
        "status_clip_on": "剪贴板监听已开启",
        "status_clip_off": "剪贴板监听已暂停",
        "status_clip_mode_q": "复制链接模式: 自动加入队列",
        "status_clip_mode_p": "复制链接模式: 立即切歌播放",
        "status_playing": "正在播放",
        "status_paused": "已暂停",
        "status_stopped": "已停止",
        "status_finished": "播放完毕",
        "play_btn": "▶ 播放",
        "pause_btn": "⏸ 暂停",
        "resume_btn": "▶ 继续",
        "play": "▶ 播放",
        "pause": "⏸ 暂停",
        "resume": "▶ 继续",
        "loading_btn": "⏳ 载入",
        "mode_list": "🔁 列表",
        "mode_one": "🔂 单曲",
        "mode_shuffle": "🔀 随机",
        "search_results_title": "搜索结果: {query}",
        "close_results": "关闭结果",
        "no_results": "未找到与“{query}”相关的曲目",
        "add_queue": "+ 队列",
        "resolving_spotify_track": "正在解析 Spotify 单曲链接...",
        "resolving_spotify_coll": "正在解析 Spotify 歌单/专辑...",
        "resolving_youtube": "正在解析 YouTube 链接...",
        "searching": "正在搜索: {query}...",
        "found_candidates": "找到 {count} 条候选结果，请点击播放或加入队列",
        "preparing_cache": "正在准备音频缓存...",
        "cache_cleared": "已清理 {count} 个缓存文件",
        "cache_already_empty": "缓存已清空",
    },
}


def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS"""
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


def load_json_safe(filepath, default):
    if not os.path.exists(filepath):
        return default.copy() if isinstance(default, (dict, list)) else default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict) and isinstance(data, dict):
            merged = default.copy()
            merged.update(data)
            return merged
        if isinstance(default, list) and isinstance(data, list):
            return data
    except Exception as e:
        logger.warning("Failed to load JSON (%s): %s", filepath, e)
    return default.copy() if isinstance(default, (dict, list)) else default


def save_json_safe(filepath, data):
    tmp = f"{filepath}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, filepath)
    except Exception as e:
        logger.warning("Failed to save JSON (%s): %s", filepath, e)


def fetch_url_text(url, timeout=7):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_spotify_track_info(url_or_id):
    """Parse Spotify single track metadata (title, artist, duration, cover)"""
    m = SPOTIFY_TRACK_REGEX.search(url_or_id)
    if not m:
        return None
    track_id = m.group(1)
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    try:
        html = fetch_url_text(embed_url, timeout=7)
        match_json = re.search(r'<script id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html)
        if match_json:
            data = json.loads(match_json.group(1))
            entity = (
                data.get("props", {})
                .get("pageProps", {})
                .get("state", {})
                .get("data", {})
                .get("entity", {})
            )
            title = entity.get("name") or entity.get("title")
            artists = ", ".join([a.get("name", "") for a in entity.get("artists", []) if a.get("name")])
            dur_ms = entity.get("duration", 0) or 0
            dur_sec = dur_ms / 1000.0 if dur_ms else 0.0

            cover_url = ""
            images = (
                entity.get("visualIdentity", {}).get("image")
                or entity.get("coverArt", {}).get("sources")
                or []
            )
            if isinstance(images, list) and images:
                cover_url = images[0].get("url", "")

            if title:
                display = f"{artists} - {title}" if artists else title
                return {
                    "track_id": track_id,
                    "title": title,
                    "artist": artists,
                    "display": display,
                    "duration": dur_sec,
                    "cover_url": cover_url,
                }
    except Exception as e:
        logger.warning("Spotify Embed track parse failed (%s): %s", track_id, e)

    # Fallback to standard track page title
    try:
        html = fetch_url_text(f"https://open.spotify.com/track/{track_id}", timeout=7)
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
                    "cover_url": "",
                }
    except Exception as e:
        logger.warning("Spotify fallback page parse failed (%s): %s", track_id, e)

    return None


def parse_spotify_collection(url):
    """Parse Spotify album or playlist track list"""
    m = SPOTIFY_COLLECTION_REGEX.search(url)
    if not m:
        return None, []
    kind = m.group(1) or m.group(2)
    coll_id = m.group(3)
    embed_url = f"https://open.spotify.com/embed/{kind}/{coll_id}"

    try:
        html = fetch_url_text(embed_url, timeout=8)
        match_json = re.search(r'<script id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html)
        if not match_json:
            return None, []
        data = json.loads(match_json.group(1))
        entity = (
            data.get("props", {})
            .get("pageProps", {})
            .get("state", {})
            .get("data", {})
            .get("entity", {})
        )
        coll_name = entity.get("name") or entity.get("title") or f"Spotify {kind}"
        track_list = entity.get("trackList") or []
        items = []
        for t in track_list:
            title = t.get("title") or t.get("name") or ""
            artist = t.get("subtitle") or ""
            dur_ms = t.get("duration", 0) or 0
            if title:
                display = f"{artist} - {title}" if artist else title
                items.append(
                    {
                        "title": title,
                        "artist": artist,
                        "display": display,
                        "duration": dur_ms / 1000.0 if dur_ms else 0.0,
                        "cover_url": "",
                        "video_id": None,
                    }
                )
        return coll_name, items
    except Exception as e:
        logger.warning("Spotify collection parse failed (%s/%s): %s", kind, coll_id, e)
        return None, []


def parse_duration_str(dur_str):
    """Convert '3:45' or '1:02:10' into seconds"""
    if not dur_str or not isinstance(dur_str, str):
        return 0.0
    parts = dur_str.strip().split(":")
    try:
        nums = [int(p) for p in parts]
        if len(nums) == 2:
            return float(nums[0] * 60 + nums[1])
        if len(nums) == 3:
            return float(nums[0] * 3600 + nums[1] * 60 + nums[2])
    except ValueError:
        pass
    return 0.0


def score_ytmusic_candidate(candidate, query, target_duration=0.0):
    """Score YouTube Music candidates (penalty keywords + duration proximity)"""
    score = 100.0
    cand_title = (candidate.get("title") or "").lower()
    query_lower = (query or "").lower()

    # Keyword penalty
    for kw in PENALTY_KEYWORDS:
        if kw in cand_title and kw not in query_lower:
            score -= 35.0

    # Duration delta score
    cand_dur = candidate.get("duration_seconds")
    if not cand_dur and candidate.get("duration"):
        cand_dur = parse_duration_str(candidate.get("duration"))
    if target_duration > 0 and cand_dur:
        diff = abs(float(cand_dur) - float(target_duration))
        if diff <= 3.0:
            score += 25.0
        elif diff <= 8.0:
            score += 10.0
        elif diff > 25.0:
            score -= min(50.0, diff * 0.8)

    # Prioritize official song category
    if candidate.get("resultType") == "song":
        score += 12.0

    return score


def format_ytmusic_item(item):
    video_id = item.get("videoId")
    title = item.get("title") or "Unknown"
    artists_list = item.get("artists") or []
    artist = ", ".join([a.get("name", "") for a in artists_list if isinstance(a, dict) and a.get("name")])
    display = f"{artist} - {title}" if artist else title

    duration = 0.0
    if "duration_seconds" in item and item["duration_seconds"]:
        try:
            duration = float(item["duration_seconds"])
        except (TypeError, ValueError):
            duration = 0.0
    elif item.get("duration"):
        duration = parse_duration_str(item.get("duration"))

    thumbs = item.get("thumbnails") or []
    cover_url = thumbs[-1].get("url", "") if thumbs and isinstance(thumbs[-1], dict) else ""

    return {
        "title": title,
        "artist": artist,
        "display": display,
        "video_id": video_id,
        "duration": duration,
        "cover_url": cover_url,
    }


def get_mp3_duration_fast(filepath, hint_duration=0.0):
    """Retrieve audio duration quickly without heavy pygame.Sound full decode"""
    if hint_duration and hint_duration > 0:
        return float(hint_duration)
    if HAS_MUTAGEN:
        try:
            audio = MP3(filepath)
            if audio.info and audio.info.length > 0:
                return float(audio.info.length)
        except Exception as e:
            logger.debug("mutagen length read failed: %s", e)
    try:
        snd = pygame.mixer.Sound(filepath)
        length = float(snd.get_length())
        del snd
        if length > 0:
            return length
    except Exception:
        pass
    return 180.0


def get_cache_stats(cache_dir=AUDIO_CACHE_DIR):
    """Return count and total MB of audio cache"""
    total_bytes = 0
    count = 0
    if os.path.isdir(cache_dir):
        for entry in os.scandir(cache_dir):
            if entry.is_file():
                try:
                    total_bytes += entry.stat().st_size
                    count += 1
                except OSError:
                    pass
    return count, total_bytes / (1024.0 * 1024.0)


def enforce_lru_cache_limit(max_mb=500, protect_path=None, cache_dir=AUDIO_CACHE_DIR):
    """Prune oldest cache files exceeding max_mb"""
    if max_mb <= 0 or not os.path.isdir(cache_dir):
        return 0
    max_bytes = max_mb * 1024 * 1024
    files = []
    total_bytes = 0
    for entry in os.scandir(cache_dir):
        if entry.is_file() and entry.name.endswith((".mp3", ".webm", ".m4a", ".opus", ".wav")):
            try:
                st = entry.stat()
                total_bytes += st.st_size
                files.append((st.st_mtime, st.st_size, entry.path))
            except OSError:
                pass

    if total_bytes <= max_bytes:
        return 0

    files.sort(key=lambda x: x[0])
    removed = 0
    protect_norm = os.path.normcase(os.path.abspath(protect_path)) if protect_path else ""
    for _, size, path in files:
        if total_bytes <= max_bytes:
            break
        if protect_norm and os.path.normcase(os.path.abspath(path)) == protect_norm:
            continue
        try:
            os.remove(path)
            total_bytes -= size
            removed += 1
        except OSError:
            pass
    return removed


class SoulMusicApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__()

        # Load persisted config and queue
        self.config_data = load_json_safe(CONFIG_FILE, DEFAULT_CONFIG)
        self.playlist = load_json_safe(QUEUE_FILE, [])
        self.current_index = 0 if self.playlist else -1
        self.lang = self.config_data.get("lang", "en")
        self.theme_mode = self.config_data.get("theme_mode", "light")

        ctk.set_appearance_mode(self.theme_mode)
        ctk.set_default_color_theme("green")

        # Window settings
        self.title(self.t("title"))
        self.configure(fg_color=COLOR_BG)
        self.compact_height = 340
        self.expanded_height = 580
        self.window_width = 630
        self.queue_visible = False
        self.search_visible = False
        self.geometry(f"{self.window_width}x{self.compact_height}")
        self.minsize(580, self.compact_height)
        self.attributes("-topmost", bool(self.config_data.get("always_on_top", True)))

        # Initialize audio engine
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except Exception as e:
            logger.error("pygame.mixer init error: %s", e)

        self.ytmusic = YTMusic()

        # Concurrency & lifecycle
        self.lock = threading.RLock()
        self.download_locks = {}
        self.download_locks_guard = threading.Lock()
        self.stop_event = threading.Event()
        self.play_request_id = 0
        self.ui_queue = queue.Queue()

        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.is_seeking = False
        self.is_loading = False
        self.current_file = None
        self.total_duration = 0.0
        self.seek_offset_seconds = 0.0
        self.volume = int(self.config_data.get("volume", 80))
        self.muted = bool(self.config_data.get("muted", False))
        self.play_mode = self.config_data.get("play_mode", "list")
        self.clipboard_enabled = bool(self.config_data.get("clipboard_enabled", True))
        self.clipboard_mode = self.config_data.get("clipboard_mode", "play")
        self.cache_limit_mb = int(self.config_data.get("cache_limit_mb", 500))

        self.last_clipboard = ""
        self.cover_ctk_image = None
        self.search_results = []

        # Setup UI
        self.setup_ui()
        self.apply_volume()
        self.refresh_queue_ui()
        self.refresh_cache_badge()

        # Backwards-compatibility aliases for tests and external scripts
        self.progress_scale = self.progress_slider
        self.time_curr_label = self.lbl_time_curr
        self.time_total_label = self.lbl_time_total
        self.vol_scale = self.vol_slider
        self.vol_val_label = self.lbl_vol
        self.search_btn = self.btn_search
        self.vol_label = type("LabelAdapter", (), {
            "cget": lambda s, p: "🔊 Volume:" if self.lang == "en" else "🔊 音量:",
            "configure": lambda s, **kw: None,
        })()
        self.theme_mode = self.config_data.get("theme_mode", "light")
        self.current_song = type("StringAdapter", (), {
            "get": lambda s: self.lbl_title.cget("text"),
            "set": lambda s, v: self.lbl_title.configure(text=v)
        })()
        self.status_text = type("StringAdapter", (), {
            "get": lambda s: self.lbl_status.cget("text"),
            "set": lambda s, v: self.set_status(v)
        })()

        # Bind events
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
        atexit.register(self.force_cleanup)
        self.bind("<space>", self.on_spacebar)

        # Polling & clipboard thread
        self.after(200, self.update_playback_loop)
        self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.clipboard_thread.start()

    def set_volume(self, val):
        self.on_volume_change(val)

    def toggle_theme(self):
        new_mode = "light" if self.theme_mode.lower() == "dark" else "dark"
        self.apply_theme(new_mode)
        self.config_data["theme_mode"] = self.theme_mode
        self.persist_config()

    def apply_theme(self, mode):
        self.theme_mode = mode.lower()
        ctk.set_appearance_mode(self.theme_mode)
        if hasattr(self, "btn_theme"):
            self.btn_theme.configure(text="🌙" if self.theme_mode == "light" else "☀️")

    def resolve_and_play(self, query, hint_duration=0.0):
        self.safe_ui_call(self.set_loading, True)
        self.safe_ui_call(self.set_status, self.t("searching", query=query))
        self.safe_ui_call(self.lbl_title.configure, text=query)
        self.safe_ui_call(self.lbl_artist.configure, text="Searching audio source...")

        # 1. Smart match with candidate scoring (filters karaoke/covers and checks duration)
        matched = self.find_best_ytmusic_match(query, target_duration=hint_duration)

        # 2. Direct v1 fallback if smart match found nothing
        if not matched:
            try:
                results = self.ytmusic.search(query, filter="songs") or self.ytmusic.search(query) or []
                for r in results:
                    if r.get("videoId"):
                        matched = format_ytmusic_item(r)
                        break
            except Exception as e:
                logger.error("Direct search fallback failed: %s", e)

        if matched:
            self.add_track_to_queue(matched, play_now=True)
        else:
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, f"Audio source not found: {query}", COLOR_DANGER)
            self.safe_ui_call(self.btn_play_pause.configure, text=self.t("play_btn"))

    def t(self, key, **kwargs):
        """Translate key into current language"""
        table = I18N.get(self.lang, I18N["en"])
        val = table.get(key, I18N["en"].get(key, key))
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

    def toggle_language(self):
        """Toggle between English and Chinese"""
        self.lang = "zh" if self.lang == "en" else "en"
        self.config_data["lang"] = self.lang
        self.persist_config()
        self.update_ui_language()

    def update_ui_language(self):
        """Refresh UI labels when language changes"""
        self.title(self.t("title"))
        self.btn_lang.configure(text=self.t("lang_toggle"))
        self.btn_topmost.configure(text=self._topmost_label())
        self.btn_clip.configure(text=self._clipboard_label())
        self.btn_clip_mode.configure(text=self._clip_mode_label())
        self.btn_mode.configure(text=self._play_mode_label())
        self.btn_search.configure(text=self.t("search_btn"))
        self.search_entry.configure(placeholder_text=self.t("search_placeholder"))
        self.refresh_cache_badge()
        self.refresh_queue_ui()
        if not self.is_playing and not self.is_paused:
            self.lbl_title.configure(text=self.t("ready"))
            self.lbl_artist.configure(text=self.t("ready_sub"))
            self.set_status(self.t("status_idle"))
        elif self.is_paused:
            self.btn_play_pause.configure(text=self.t("resume_btn"))
            self.set_status(self.t("status_paused"), COLOR_SUBTEXT)
        elif self.is_playing:
            self.btn_play_pause.configure(text=self.t("pause_btn"))
            self.set_status(self.t("status_playing"))

    # ----------------- UI Construction -----------------
    def setup_ui(self):
        self.container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=14, pady=12)

        # 1. Top bar (Pin / Clipboard / Mode / Language / Cache / Queue)
        top_bar = ctk.CTkFrame(self.container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 8))

        self.btn_topmost = ctk.CTkButton(
            top_bar,
            text=self._topmost_label(),
            width=62,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_GREEN if self.config_data.get("always_on_top", True) else COLOR_ELEVATED,
            hover_color=COLOR_GREEN_HOVER if self.config_data.get("always_on_top", True) else COLOR_HOVER,
            text_color="#000000" if self.config_data.get("always_on_top", True) else COLOR_TEXT,
            corner_radius=13,
            command=self.toggle_topmost,
        )
        self.btn_topmost.pack(side="left", padx=(0, 5))

        self.btn_clip = ctk.CTkButton(
            top_bar,
            text=self._clipboard_label(),
            width=64,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_GREEN if self.clipboard_enabled else COLOR_ELEVATED,
            hover_color=COLOR_GREEN_HOVER if self.clipboard_enabled else COLOR_HOVER,
            text_color="#000000" if self.clipboard_enabled else COLOR_TEXT,
            corner_radius=13,
            command=self.toggle_clipboard,
        )
        self.btn_clip.pack(side="left", padx=(0, 5))

        self.btn_clip_mode = ctk.CTkButton(
            top_bar,
            text=self._clip_mode_label(),
            width=68,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_SUBTEXT,
            corner_radius=13,
            command=self.toggle_clipboard_mode,
        )
        self.btn_clip_mode.pack(side="left", padx=(0, 5))

        self.btn_lang = ctk.CTkButton(
            top_bar,
            text=self.t("lang_toggle"),
            width=58,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=13,
            command=self.toggle_language,
        )
        self.btn_lang.pack(side="left", padx=(0, 5))

        self.btn_theme = ctk.CTkButton(
            top_bar,
            text="🌙" if self.theme_mode == "light" else "☀️",
            width=34,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=13,
            command=self.toggle_theme,
        )
        self.btn_theme.pack(side="left", padx=(0, 5))

        self.btn_cache = ctk.CTkButton(
            top_bar,
            text=f"{self.t('cache_prefix')} 0MB",
            width=76,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_SUBTEXT,
            corner_radius=13,
            command=self.clear_cache_action,
        )
        self.btn_cache.pack(side="right")

        self.btn_queue_toggle = ctk.CTkButton(
            top_bar,
            text=self.t("queue_btn", count=0),
            width=84,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=13,
            command=self.toggle_queue_panel,
        )
        self.btn_queue_toggle.pack(side="right", padx=(0, 6))

        # 2. Search bar
        search_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text=self.t("search_placeholder"),
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLOR_INPUT,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text_color=COLOR_MUTED,
            corner_radius=8,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.search_entry.bind("<Return>", lambda e: self.on_manual_search())

        self.btn_clear_search = ctk.CTkButton(
            search_frame,
            text="✕",
            width=32,
            height=36,
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=8,
            command=self.clear_search_input,
        )
        self.btn_clear_search.pack(side="left", padx=(0, 6))

        self.btn_search = ctk.CTkButton(
            search_frame,
            text=self.t("search_btn"),
            width=100,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_GREEN,
            hover_color=COLOR_GREEN_HOVER,
            text_color="#000000",
            corner_radius=8,
            command=self.on_manual_search,
        )
        self.btn_search.pack(side="right")

        # 3. Now Playing Card (Cover + Title + Artist + Status)
        now_card = ctk.CTkFrame(self.container, fg_color=COLOR_SURFACE, corner_radius=10)
        now_card.pack(fill="x", pady=(0, 8))

        self.cover_label = ctk.CTkLabel(
            now_card,
            text="♪",
            width=68,
            height=68,
            fg_color=COLOR_ELEVATED,
            text_color=COLOR_GREEN,
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            corner_radius=8,
        )
        self.cover_label.pack(side="left", padx=10, pady=10)

        info_box = ctk.CTkFrame(now_card, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True, padx=(2, 12), pady=10)

        self.lbl_title = ctk.CTkLabel(
            info_box,
            text=self.t("ready"),
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
            justify="left",
        )
        self.lbl_title.pack(fill="x")

        self.lbl_artist = ctk.CTkLabel(
            info_box,
            text=self.t("ready_sub"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_SUBTEXT,
            anchor="w",
            justify="left",
        )
        self.lbl_artist.pack(fill="x", pady=(2, 4))

        self.lbl_status = ctk.CTkLabel(
            info_box,
            text=self.t("status_idle"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_GREEN,
            anchor="w",
            justify="left",
        )
        self.lbl_status.pack(fill="x")

        # 4. Progress bar
        self.loading_bar = ctk.CTkProgressBar(
            self.container,
            height=4,
            mode="indeterminate",
            progress_color=COLOR_GREEN,
            fg_color=COLOR_ELEVATED,
        )

        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.pack(fill="x", pady=(2, 6))

        self.lbl_time_curr = ctk.CTkLabel(
            prog_frame,
            text="00:00",
            width=44,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_SUBTEXT,
            anchor="e",
        )
        self.lbl_time_curr.pack(side="left", padx=(0, 6))

        self.progress_slider = ctk.CTkSlider(
            prog_frame,
            from_=0,
            to=100,
            height=16,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_GREEN,
            progress_color=COLOR_GREEN,
            fg_color="#333333",
            command=self.on_slider_drag,
        )
        self.progress_slider.set(0)
        self.progress_slider.pack(side="left", fill="x", expand=True)
        self.progress_slider.bind("<ButtonPress-1>", self.on_seek_press)
        self.progress_slider.bind("<ButtonRelease-1>", self.on_seek_release)

        self.lbl_time_total = ctk.CTkLabel(
            prog_frame,
            text="00:00",
            width=44,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_SUBTEXT,
            anchor="w",
        )
        self.lbl_time_total.pack(side="left", padx=(6, 0))

        # 5. Controls + Volume
        ctrl_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=(2, 6))

        self.btn_mode = ctk.CTkButton(
            ctrl_frame,
            text=self._play_mode_label(),
            width=76,
            height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_SUBTEXT,
            corner_radius=8,
            command=self.cycle_play_mode,
        )
        self.btn_mode.pack(side="left", padx=(0, 6))

        self.btn_prev = ctk.CTkButton(
            ctrl_frame,
            text="⏮",
            width=44,
            height=34,
            font=ctk.CTkFont(size=14),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=8,
            command=self.play_prev,
        )
        self.btn_prev.pack(side="left", padx=(0, 6))

        self.btn_play_pause = ctk.CTkButton(
            ctrl_frame,
            text=self.t("play_btn"),
            width=92,
            height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_GREEN,
            hover_color=COLOR_GREEN_HOVER,
            text_color="#000000",
            corner_radius=17,
            command=self.toggle_play_pause,
        )
        self.btn_play_pause.pack(side="left", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="⏹",
            width=40,
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=8,
            command=self.stop_music,
        )
        self.btn_stop.pack(side="left", padx=(0, 6))

        self.btn_next = ctk.CTkButton(
            ctrl_frame,
            text="⏭",
            width=44,
            height=34,
            font=ctk.CTkFont(size=14),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=8,
            command=self.play_next,
        )
        self.btn_next.pack(side="left", padx=(0, 10))

        self.btn_mute = ctk.CTkButton(
            ctrl_frame,
            text="🔇" if self.muted else "🔊",
            width=34,
            height=34,
            fg_color="transparent",
            hover_color=COLOR_ELEVATED,
            text_color=COLOR_TEXT,
            corner_radius=8,
            command=self.toggle_mute,
        )
        self.btn_mute.pack(side="left")

        self.vol_slider = ctk.CTkSlider(
            ctrl_frame,
            from_=0,
            to=100,
            width=85,
            height=14,
            button_color=COLOR_TEXT,
            button_hover_color=COLOR_GREEN,
            progress_color=COLOR_GREEN,
            fg_color="#333333",
            command=self.on_volume_change,
        )
        self.vol_slider.set(0 if self.muted else self.volume)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(2, 4))

        self.lbl_vol = ctk.CTkLabel(
            ctrl_frame,
            text="0%" if self.muted else f"{self.volume}%",
            width=36,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_SUBTEXT,
            anchor="e",
        )
        self.lbl_vol.pack(side="right")

        # 6. Collapsible Drawer Frame (Search results & Queue)
        self.drawer_frame = ctk.CTkFrame(self.container, fg_color=COLOR_SURFACE, corner_radius=10)
        self.drawer_header = ctk.CTkFrame(self.drawer_frame, fg_color="transparent")
        self.drawer_header.pack(fill="x", padx=10, pady=(8, 4))

        self.lbl_drawer_title = ctk.CTkLabel(
            self.drawer_header,
            text=self.t("queue_title", count=len(self.playlist)),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT,
        )
        self.lbl_drawer_title.pack(side="left")

        self.btn_drawer_action = ctk.CTkButton(
            self.drawer_header,
            text=self.t("clear_queue"),
            width=76,
            height=24,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=COLOR_ELEVATED,
            hover_color=COLOR_DANGER,
            text_color=COLOR_SUBTEXT,
            corner_radius=6,
            command=self.on_drawer_action,
        )
        self.btn_drawer_action.pack(side="right")

        self.drawer_scroll = ctk.CTkScrollableFrame(
            self.drawer_frame,
            fg_color="transparent",
            scrollbar_button_color="#3A3A3A",
            scrollbar_button_hover_color="#555555",
        )
        self.drawer_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    # ----------------- Top Controls & Drawer -----------------
    def _topmost_label(self):
        return self.t("pin_on") if self.config_data.get("always_on_top", True) else self.t("pin_off")

    def _clipboard_label(self):
        return self.t("clip_on") if self.clipboard_enabled else self.t("clip_off")

    def _clip_mode_label(self):
        return self.t("clip_mode_play") if self.clipboard_mode == "play" else self.t("clip_mode_queue")

    def _play_mode_label(self):
        return {"list": self.t("mode_list"), "one": self.t("mode_one"), "shuffle": self.t("mode_shuffle")}.get(self.play_mode, self.t("mode_list"))

    def toggle_topmost(self):
        new_val = not bool(self.config_data.get("always_on_top", True))
        self.config_data["always_on_top"] = new_val
        self.attributes("-topmost", new_val)
        self.btn_topmost.configure(
            text=self._topmost_label(),
            fg_color=COLOR_GREEN if new_val else COLOR_ELEVATED,
            hover_color=COLOR_GREEN_HOVER if new_val else COLOR_HOVER,
            text_color="#000000" if new_val else COLOR_TEXT,
        )
        self.persist_config()

    def toggle_clipboard(self):
        self.clipboard_enabled = not self.clipboard_enabled
        self.config_data["clipboard_enabled"] = self.clipboard_enabled
        self.btn_clip.configure(
            text=self._clipboard_label(),
            fg_color=COLOR_GREEN if self.clipboard_enabled else COLOR_ELEVATED,
            hover_color=COLOR_GREEN_HOVER if self.clipboard_enabled else COLOR_HOVER,
            text_color="#000000" if self.clipboard_enabled else COLOR_TEXT,
        )
        self.set_status(self.t("status_clip_on") if self.clipboard_enabled else self.t("status_clip_off"))
        self.persist_config()

    def toggle_clipboard_mode(self):
        self.clipboard_mode = "queue" if self.clipboard_mode == "play" else "play"
        self.config_data["clipboard_mode"] = self.clipboard_mode
        self.btn_clip_mode.configure(text=self._clip_mode_label())
        self.set_status(self.t("status_clip_mode_q") if self.clipboard_mode == "queue" else self.t("status_clip_mode_p"))
        self.persist_config()

    def cycle_play_mode(self):
        order = ["list", "one", "shuffle"]
        idx = order.index(self.play_mode) if self.play_mode in order else 0
        self.play_mode = order[(idx + 1) % len(order)]
        self.config_data["play_mode"] = self.play_mode
        self.btn_mode.configure(text=self._play_mode_label())
        self.persist_config()

    def set_drawer_open(self, mode):
        """mode: None | 'queue' | 'search'"""
        if mode is None:
            self.queue_visible = False
            self.search_visible = False
            self.drawer_frame.pack_forget()
            self.geometry(f"{self.window_width}x{self.compact_height}")
            return

        self.queue_visible = (mode == "queue")
        self.search_visible = (mode == "search")
        if not self.drawer_frame.winfo_ismapped():
            self.drawer_frame.pack(fill="both", expand=True, pady=(6, 0))
            self.geometry(f"{self.window_width}x{self.expanded_height}")

    def toggle_queue_panel(self):
        if self.queue_visible:
            self.set_drawer_open(None)
        else:
            self.set_drawer_open("queue")
            self.refresh_queue_ui()

    def on_drawer_action(self):
        if self.search_visible:
            self.set_drawer_open(None)
        else:
            self.clear_queue()

    def clear_search_input(self):
        self.search_entry.delete(0, "end")
        if self.search_visible:
            self.set_drawer_open(None)

    def set_status(self, text, color=COLOR_GREEN):
        self.lbl_status.configure(text=text, text_color=color)

    def set_loading(self, loading):
        self.is_loading = loading
        try:
            if loading:
                if not self.loading_bar.winfo_ismapped():
                    self.loading_bar.pack(fill="x", pady=(0, 4), before=self.lbl_time_curr.master)
                self.loading_bar.start()
            else:
                self.loading_bar.stop()
                if self.loading_bar.winfo_ismapped():
                    self.loading_bar.pack_forget()
        except Exception:
            pass

    def refresh_cache_badge(self):
        cnt, mb = get_cache_stats()
        self.btn_cache.configure(text=f"{self.t('cache_prefix')} {mb:.0f}MB")

    def clear_cache_action(self):
        removed = enforce_lru_cache_limit(max_mb=0.001, protect_path=self.current_file)
        self.refresh_cache_badge()
        self.set_status(self.t("cache_cleared", count=removed) if removed else self.t("cache_already_empty"))

    # ----------------- Volume & Seeking -----------------
    def on_volume_change(self, val):
        self.volume = int(float(val))
        if self.volume > 0 and self.muted:
            self.muted = False
            self.btn_mute.configure(text="🔊")
        self.apply_volume()
        self.config_data["volume"] = self.volume
        self.config_data["muted"] = self.muted
        self.persist_config()

    def toggle_mute(self):
        self.muted = not self.muted
        self.btn_mute.configure(text="🔇" if self.muted else "🔊")
        self.vol_slider.set(0 if self.muted else self.volume)
        self.apply_volume()
        self.config_data["muted"] = self.muted
        self.persist_config()

    def apply_volume(self):
        effective = 0 if self.muted else self.volume
        self.lbl_vol.configure(text=f"{effective}%")
        try:
            pygame.mixer.music.set_volume(effective / 100.0)
        except Exception:
            pass

    def on_seek_press(self, _event):
        if self.current_file and self.total_duration > 0:
            self.is_seeking = True

    def on_slider_drag(self, val):
        if self.is_seeking and self.total_duration > 0:
            self.lbl_time_curr.configure(text=format_time(float(val)))

    def on_seek_release(self, _event):
        if not self.is_seeking:
            return
        try:
            target = float(self.progress_slider.get())
            self.seek_to(target)
        finally:
            self.is_seeking = False

    def seek_to(self, target_seconds):
        if not self.current_file or self.total_duration <= 0:
            return
        target = max(0.0, min(max(0.0, self.total_duration - 0.2), float(target_seconds)))
        self.seek_offset_seconds = target
        self.progress_slider.set(target)
        self.lbl_time_curr.configure(text=format_time(target))
        try:
            if self.is_paused:
                pygame.mixer.music.play(start=target)
                pygame.mixer.music.pause()
            elif self.is_playing:
                pygame.mixer.music.play(start=target)
            else:
                self.start_playback(self.current_file, start_sec=target)
        except Exception as e:
            logger.warning("Seek error: %s", e)
            self.set_status(f"Seek error: {e}", COLOR_DANGER)

    def get_current_seconds(self):
        if not self.is_playing:
            return self.seek_offset_seconds
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self.seek_offset_seconds
        return self.seek_offset_seconds + (pos_ms / 1000.0)

    # ----------------- Playback Control -----------------
    def on_spacebar(self, event=None):
        focused = self.focus_get()
        if (focused is not None and isinstance(focused, (tk.Entry, ctk.CTkEntry))) or \
           (event is not None and getattr(event, "widget", None) is not None and (
               isinstance(event.widget, (tk.Entry, ctk.CTkEntry)) or
               event.widget == getattr(self, "search_entry", None) or
               getattr(event.widget, "_entry", None) is not None
           )):
            return None
        self.toggle_play_pause()
        return "break"

    def toggle_play_pause(self):
        if not self.current_file:
            with self.lock:
                if self.playlist:
                    idx = self.current_index if 0 <= self.current_index < len(self.playlist) else 0
                    self.play_track_at_index(idx)
            return

        if self.is_playing:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.btn_play_pause.configure(text=self.t("pause_btn"))
                self.set_status(self.t("status_playing"))
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.btn_play_pause.configure(text=self.t("resume_btn"))
                self.set_status(self.t("status_paused"), COLOR_SUBTEXT)
        else:
            self.start_playback(self.current_file, start_sec=float(self.progress_slider.get()))

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
        self.progress_slider.set(0)
        self.lbl_time_curr.configure(text="00:00")
        self.btn_play_pause.configure(text=self.t("play_btn"))
        self.set_status(self.t("status_stopped"), COLOR_SUBTEXT)

    def play_prev(self):
        with self.lock:
            if not self.playlist:
                if self.current_file:
                    self.seek_to(0.0)
                return
            if self.get_current_seconds() > 3.0 or self.current_index <= 0:
                self.seek_to(0.0)
            else:
                self.play_track_at_index(self.current_index - 1)

    def _compute_next_index(self):
        n = len(self.playlist)
        if n == 0:
            return -1
        if self.play_mode == "one":
            return self.current_index if 0 <= self.current_index < n else 0
        if self.play_mode == "shuffle" and n > 1:
            choices = [i for i in range(n) if i != self.current_index]
            return random.choice(choices)
        return (self.current_index + 1) % n

    def play_next(self):
        with self.lock:
            if not self.playlist:
                return
            if self.play_mode == "shuffle" and len(self.playlist) > 1:
                next_idx = random.choice([i for i in range(len(self.playlist)) if i != self.current_index])
            else:
                next_idx = (self.current_index + 1) % len(self.playlist)
            self.play_track_at_index(next_idx)

    def on_track_finished(self):
        self.is_playing = False
        self.is_paused = False
        with self.lock:
            if not self.playlist:
                self.stop_music()
                return
            if self.play_mode == "one":
                self.seek_to(0.0)
                self.start_playback(self.current_file, start_sec=0.0, hint_duration=self.total_duration)
                return
            if len(self.playlist) > 1:
                next_idx = self._compute_next_index()
                self.play_track_at_index(next_idx)
                return
        self.stop_music()
        self.set_status(self.t("status_finished"), COLOR_SUBTEXT)

    def play_track_at_index(self, index):
        with self.lock:
            if index < 0 or index >= len(self.playlist):
                return
            self.current_index = index
            track = self.playlist[index]
            self.play_request_id += 1
            req_id = self.play_request_id

        self.btn_play_pause.configure(text=self.t("loading_btn"))
        self.progress_slider.set(0)
        self.lbl_time_curr.configure(text="00:00")
        self.set_loading(True)
        self.refresh_queue_ui()
        threading.Thread(target=self._resolve_and_play_track, args=(track, req_id), daemon=True).start()

    # ----------------- Queue Management -----------------
    def add_track_to_queue(self, track, play_now=False):
        with self.lock:
            found_idx = -1
            if track.get("video_id"):
                for idx, item in enumerate(self.playlist):
                    if item.get("video_id") == track["video_id"]:
                        found_idx = idx
                        break
            if found_idx >= 0:
                target_idx = found_idx
            else:
                self.playlist.append(track)
                target_idx = len(self.playlist) - 1
            self.persist_queue()

        self.safe_ui_call(self.refresh_queue_ui)
        if play_now:
            self.safe_ui_call(self.play_track_at_index, target_idx)
        else:
            self.safe_ui_call(self.set_status, f"Queued: {track.get('display', track.get('title'))}")

    def remove_queue_item(self, index):
        with self.lock:
            if index < 0 or index >= len(self.playlist):
                return
            self.playlist.pop(index)
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                self.current_index = min(self.current_index, len(self.playlist) - 1)
            self.persist_queue()
        self.refresh_queue_ui()

    def clear_queue(self):
        with self.lock:
            self.playlist.clear()
            self.current_index = -1
            self.persist_queue()
        self.refresh_queue_ui()
        self.set_status(self.t("queue_empty"), COLOR_SUBTEXT)

    def refresh_queue_ui(self):
        count = len(self.playlist)
        self.btn_queue_toggle.configure(text=self.t("queue_btn", count=count))
        if not self.queue_visible:
            return

        self.lbl_drawer_title.configure(text=self.t("queue_title", count=count))
        self.btn_drawer_action.configure(text=self.t("clear_queue"))
        for w in self.drawer_scroll.winfo_children():
            w.destroy()

        if count == 0:
            ctk.CTkLabel(
                self.drawer_scroll,
                text=self.t("queue_empty"),
                text_color=COLOR_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            ).pack(pady=24)
            return

        for idx, track in enumerate(self.playlist):
            is_curr = (idx == self.current_index)
            row = ctk.CTkFrame(
                self.drawer_scroll,
                fg_color=COLOR_ELEVATED if is_curr else "transparent",
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            prefix = "▶ " if is_curr else f"{idx + 1}. "
            dur_txt = format_time(track.get("duration", 0)) if track.get("duration") else "--:--"
            label_text = f"{prefix}{track.get('display', track.get('title', 'Unknown'))}"

            btn_song = ctk.CTkButton(
                row,
                text=label_text,
                anchor="w",
                height=30,
                fg_color="transparent",
                hover_color=COLOR_HOVER,
                text_color=COLOR_GREEN if is_curr else COLOR_TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold" if is_curr else "normal"),
                command=lambda i=idx: self.play_track_at_index(i),
            )
            btn_song.pack(side="left", fill="x", expand=True, padx=(4, 4))

            ctk.CTkLabel(
                row,
                text=dur_txt,
                width=42,
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=COLOR_MUTED,
            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(
                row,
                text="✕",
                width=26,
                height=26,
                fg_color="transparent",
                hover_color=COLOR_DANGER,
                text_color=COLOR_MUTED,
                corner_radius=6,
                command=lambda i=idx: self.remove_queue_item(i),
            ).pack(side="right", padx=(0, 4))

    def render_search_results_ui(self, query, items):
        self.search_results = items
        self.set_drawer_open("search")
        self.lbl_drawer_title.configure(text=self.t("search_results_title", query=query))
        self.btn_drawer_action.configure(text=self.t("close_results"))
        for w in self.drawer_scroll.winfo_children():
            w.destroy()

        if not items:
            ctk.CTkLabel(
                self.drawer_scroll,
                text=self.t("no_results", query=query),
                text_color=COLOR_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            ).pack(pady=24)
            return

        for track in items:
            row = ctk.CTkFrame(self.drawer_scroll, fg_color=COLOR_ELEVATED, corner_radius=6)
            row.pack(fill="x", pady=3)

            dur_txt = format_time(track.get("duration", 0)) if track.get("duration") else "--:--"
            txt = f"{track['title']}\n{track['artist']} · {dur_txt}" if track["artist"] else f"{track['title']} · {dur_txt}"

            ctk.CTkLabel(
                row,
                text=txt,
                anchor="w",
                justify="left",
                font=ctk.CTkFont(family="Segoe UI", size=11.5),
                text_color=COLOR_TEXT,
            ).pack(side="left", fill="x", expand=True, padx=10, pady=6)

            ctk.CTkButton(
                row,
                text=self.t("add_queue"),
                width=64,
                height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color=COLOR_ELEVATED,
                hover_color=COLOR_HOVER,
                text_color=COLOR_TEXT,
                corner_radius=6,
                command=lambda t=track: self.add_track_to_queue(t, play_now=False),
            ).pack(side="right", padx=(4, 6))

            ctk.CTkButton(
                row,
                text=self.t("play_btn"),
                width=64,
                height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=COLOR_GREEN,
                hover_color=COLOR_GREEN_HOVER,
                text_color="#000000",
                corner_radius=6,
                command=lambda t=track: self._pick_search_and_play(t),
            ).pack(side="right", padx=(4, 0))

    def _pick_search_and_play(self, track):
        self.set_drawer_open(None)
        self.add_track_to_queue(track, play_now=True)

    # ----------------- Clipboard & Link Resolution -----------------
    def on_manual_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        if SPOTIFY_TRACK_REGEX.search(query):
            self.set_status(self.t("resolving_spotify_track"))
            self.set_loading(True)
            threading.Thread(target=self.handle_spotify_track_url, args=(query, True), daemon=True).start()
        elif SPOTIFY_COLLECTION_REGEX.search(query):
            self.set_status(self.t("resolving_spotify_coll"))
            self.set_loading(True)
            threading.Thread(target=self.handle_spotify_collection_url, args=(query,), daemon=True).start()
        elif YOUTUBE_URL_REGEX.search(query):
            self.set_status(self.t("resolving_youtube"))
            self.set_loading(True)
            threading.Thread(target=self.handle_youtube_url, args=(query, True), daemon=True).start()
        else:
            self.set_status(self.t("searching", query=query))
            self.set_loading(True)
            threading.Thread(target=self.resolve_and_play, args=(query,), daemon=True).start()

    def monitor_clipboard(self):
        while not self.stop_event.is_set():
            self.stop_event.wait(1.0)
            if self.stop_event.is_set() or not self.clipboard_enabled:
                continue
            try:
                clip = (pyperclip.paste() or "").strip()
                if not clip or clip == self.last_clipboard:
                    continue
                self.last_clipboard = clip
                play_now = (self.clipboard_mode == "play")

                if SPOTIFY_TRACK_REGEX.search(clip):
                    self.safe_ui_call(self.set_status, self.t("resolving_spotify_track"))
                    self.safe_ui_call(self.set_loading, True)
                    threading.Thread(target=self.handle_spotify_track_url, args=(clip, play_now), daemon=True).start()
                elif SPOTIFY_COLLECTION_REGEX.search(clip):
                    self.safe_ui_call(self.set_status, self.t("resolving_spotify_coll"))
                    self.safe_ui_call(self.set_loading, True)
                    threading.Thread(target=self.handle_spotify_collection_url, args=(clip,), daemon=True).start()
            except Exception:
                pass

    def handle_spotify_track_url(self, url, play_now=True):
        info = parse_spotify_track_info(url)
        if not info:
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, "Failed to resolve Spotify track", COLOR_DANGER)
            return

        query = info.get("display") or info.get("title")
        matched = self.find_best_ytmusic_match(query, target_duration=info.get("duration", 0.0))
        if not matched:
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, f"Audio source not found: {query}", COLOR_DANGER)
            return

        if info.get("cover_url"):
            matched["cover_url"] = info["cover_url"]
        if info.get("duration", 0) > 0:
            matched["duration"] = info["duration"]
        matched["title"] = info.get("title") or matched["title"]
        matched["artist"] = info.get("artist") or matched["artist"]
        matched["display"] = info.get("display") or matched["display"]

        self.add_track_to_queue(matched, play_now=play_now)
        if not play_now:
            self.safe_ui_call(self.set_loading, False)

    def handle_spotify_collection_url(self, url):
        coll_name, tracks = parse_spotify_collection(url)
        if not tracks:
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, "Failed to read playlist or album", COLOR_DANGER)
            return

        start_idx = len(self.playlist)
        with self.lock:
            self.playlist.extend(tracks)
            self.persist_queue()

        self.safe_ui_call(self.set_loading, False)
        self.safe_ui_call(self.refresh_queue_ui)
        self.safe_ui_call(self.set_status, f"Imported '{coll_name}' ({len(tracks)} tracks)")
        if not self.is_playing:
            self.safe_ui_call(self.play_track_at_index, start_idx)

    def handle_youtube_url(self, url, play_now=True):
        m = YOUTUBE_URL_REGEX.search(url)
        if not m:
            self.safe_ui_call(self.set_loading, False)
            return
        video_id = m.group(1)
        track = {
            "title": f"YouTube ({video_id})",
            "artist": "YouTube",
            "display": f"YouTube ({video_id})",
            "video_id": video_id,
            "duration": 0.0,
            "cover_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        }
        try:
            res = self.ytmusic.get_song(video_id)
            vd = res.get("videoDetails", {})
            if vd.get("title"):
                track["title"] = vd["title"]
                track["artist"] = vd.get("author", "")
                track["display"] = f"{track['artist']} - {track['title']}" if track["artist"] else track["title"]
                track["duration"] = float(vd.get("lengthSeconds", 0) or 0)
        except Exception as e:
            logger.debug("Failed to get YouTube metadata: %s", e)

        self.add_track_to_queue(track, play_now=play_now)
        if not play_now:
            self.safe_ui_call(self.set_loading, False)

    def search_top_candidates(self, query):
        try:
            results = self.ytmusic.search(query, filter="songs") or self.ytmusic.search(query) or []
            items = []
            for r in results:
                if r.get("videoId"):
                    items.append(format_ytmusic_item(r))
                if len(items) >= 5:
                    break
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.render_search_results_ui, query, items)
            self.safe_ui_call(self.set_status, self.t("found_candidates", count=len(items)))
        except Exception as e:
            logger.error("Search failed: %s", e)
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, f"Search failed: {e}", COLOR_DANGER)

    def find_best_ytmusic_match(self, query, target_duration=0.0):
        try:
            results = self.ytmusic.search(query, filter="songs") or self.ytmusic.search(query) or []
            candidates = [r for r in results[:6] if r.get("videoId")]
            if not candidates:
                return None
            best = max(candidates, key=lambda c: score_ytmusic_candidate(c, query, target_duration))
            return format_ytmusic_item(best)
        except Exception as e:
            logger.error("YTMusic match failed (%s): %s", query, e)
            return None

    # ----------------- Audio Download & Prefetch -----------------
    def _get_video_lock(self, video_id):
        with self.download_locks_guard:
            if video_id not in self.download_locks:
                self.download_locks[video_id] = threading.Lock()
            return self.download_locks[video_id]

    def _resolve_and_play_track(self, track, req_id):
        with self.lock:
            if req_id != self.play_request_id:
                return

        if not track.get("video_id"):
            query = track.get("display") or track.get("title")
            self.safe_ui_call(self.set_status, f"Matching audio: {query}...")
            matched = self.find_best_ytmusic_match(query, target_duration=track.get("duration", 0.0))
            if not matched:
                self.safe_ui_call(self.set_loading, False)
                self.safe_ui_call(self.set_status, f"Failed to match: {query}", COLOR_DANGER)
                self.safe_ui_call(self.btn_play_pause.configure, text=self.t("play_btn"))
                return
            track["video_id"] = matched["video_id"]
            if not track.get("cover_url"):
                track["cover_url"] = matched.get("cover_url", "")
            if not track.get("duration"):
                track["duration"] = matched.get("duration", 0.0)
            self.persist_queue()

        video_id = track["video_id"]
        title = track.get("title") or track.get("display", "Unknown")
        artist = track.get("artist") or "YouTube Music"

        self.safe_ui_call(self.lbl_title.configure, text=title)
        self.safe_ui_call(self.lbl_artist.configure, text=artist)
        self.safe_ui_call(self.set_status, self.t("preparing_cache"))

        if track.get("cover_url"):
            threading.Thread(target=self._load_cover_art, args=(track["cover_url"], req_id), daemon=True).start()

        target_file = self.get_or_download_audio(video_id)

        with self.lock:
            if req_id != self.play_request_id:
                return

        if not target_file:
            self.safe_ui_call(self.set_loading, False)
            self.safe_ui_call(self.set_status, "Failed to get audio stream", COLOR_DANGER)
            self.safe_ui_call(self.btn_play_pause.configure, text=self.t("play_btn"))
            return

        hint_dur = track.get("duration", 0.0)
        self.safe_ui_call(self.start_playback, target_file, 0.0, hint_dur)
        self.safe_ui_call(self.refresh_cache_badge)

        threading.Thread(target=self._prefetch_next_track, args=(req_id,), daemon=True).start()

    def _prefetch_next_track(self, req_id):
        time.sleep(1.5)
        with self.lock:
            if req_id != self.play_request_id or len(self.playlist) <= 1 or self.play_mode == "one":
                return
            next_idx = (self.current_index + 1) % len(self.playlist)
            next_track = self.playlist[next_idx]

        vid = next_track.get("video_id")
        if not vid:
            matched = self.find_best_ytmusic_match(
                next_track.get("display") or next_track.get("title"),
                target_duration=next_track.get("duration", 0.0),
            )
            if not matched:
                return
            vid = matched["video_id"]
            next_track["video_id"] = vid
            if not next_track.get("cover_url"):
                next_track["cover_url"] = matched.get("cover_url", "")
            self.persist_queue()

        self.get_or_download_audio(vid)
        self.safe_ui_call(self.refresh_cache_badge)

    def _load_cover_art(self, url, req_id):
        if not HAS_PIL or not url:
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = resp.read()
            img = Image.open(BytesIO(raw)).convert("RGB")
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(68, 68))
            with self.lock:
                if req_id != self.play_request_id:
                    return
            self.safe_ui_call(self._apply_cover_art, ctk_img)
        except Exception as e:
            logger.debug("Cover art download failed: %s", e)

    def _apply_cover_art(self, ctk_img):
        self.cover_ctk_image = ctk_img
        self.cover_label.configure(image=ctk_img, text="")

    def get_or_download_audio(self, video_id):
        if not video_id or not isinstance(video_id, str):
            return None
        video_id = video_id.strip()
        if not video_id:
            return None

        vid_lock = self._get_video_lock(video_id)
        with vid_lock:
            mp3_file = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.mp3")
            if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
                try:
                    os.utime(mp3_file, None)
                except OSError:
                    pass
                return mp3_file

            # Transcode if other formats exist
            for ext in ("webm", "m4a", "opus", "wav"):
                cand = os.path.join(AUDIO_CACHE_DIR, f"{video_id}.{ext}")
                if os.path.exists(cand) and os.path.getsize(cand) > 10000:
                    ffmpeg_cmd = FFMPEG_BIN if os.path.exists(FFMPEG_BIN) else "ffmpeg"
                    cmd = [
                        ffmpeg_cmd, "-y", "-i", cand,
                        "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
                        mp3_file,
                    ]
                    subprocess.run(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
                        enforce_lru_cache_limit(self.cache_limit_mb, protect_path=mp3_file)
                        return mp3_file

            try:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(AUDIO_CACHE_DIR, f"{video_id}.%(ext)s"),
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
                if shutil.which("node"):
                    ydl_opts["js_runtimes"] = {"node": {}}
                if os.path.exists(FFMPEG_BIN):
                    ydl_opts["ffmpeg_location"] = os.path.dirname(FFMPEG_BIN)

                with YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

                if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 10000:
                    enforce_lru_cache_limit(self.cache_limit_mb, protect_path=mp3_file)
                    return mp3_file
            except Exception as e:
                logger.error("yt-dlp download failed (%s): %s", video_id, e)

        return None

    def start_playback(self, filepath, start_sec=0.0, hint_duration=0.0):
        try:
            self.set_loading(False)
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load(filepath)
            self.apply_volume()

            self.total_duration = get_mp3_duration_fast(filepath, hint_duration=hint_duration)
            scale_max = max(1.0, self.total_duration)
            self.progress_slider.configure(to=scale_max)
            self.lbl_time_total.configure(text=format_time(self.total_duration))

            self.seek_offset_seconds = start_sec
            self.progress_slider.set(start_sec)
            self.lbl_time_curr.configure(text=format_time(start_sec))

            pygame.mixer.music.play(start=start_sec)
            self.is_playing = True
            self.is_paused = False
            self.current_file = filepath
            self.btn_play_pause.configure(text=self.t("pause_btn"))
            self.set_status(self.t("status_playing"))
        except Exception as e:
            logger.error("Playback failed: %s", e)
            self.set_loading(False)
            self.set_status(f"Playback failed: {e}", COLOR_DANGER)
            self.is_playing = False
            self.is_paused = False
            self.btn_play_pause.configure(text=self.t("play_btn"))

    # ----------------- Lifecycle & Polling -----------------
    def safe_ui_call(self, fn, *args, **kwargs):
        self.ui_queue.put(lambda: fn(*args, **kwargs))

    def update_playback_loop(self):
        while not self.ui_queue.empty():
            try:
                task = self.ui_queue.get_nowait()
                task()
            except Exception as e:
                logger.warning("UI task exception: %s", e)

        try:
            if self.is_playing and not self.is_paused:
                busy = pygame.mixer.music.get_busy()
                pos_ms = pygame.mixer.music.get_pos()
                if not busy and pos_ms == -1:
                    self.on_track_finished()
                elif not self.is_seeking and self.total_duration > 0:
                    curr = min(self.seek_offset_seconds + max(0.0, pos_ms / 1000.0), self.total_duration)
                    self.progress_slider.set(curr)
                    self.lbl_time_curr.configure(text=format_time(curr))
        except Exception:
            pass

        if not self.stop_event.is_set():
            self.after(200, self.update_playback_loop)

    def persist_config(self):
        save_json_safe(CONFIG_FILE, self.config_data)

    def persist_queue(self):
        save_json_safe(QUEUE_FILE, self.playlist)

    def on_window_close(self):
        self.stop_event.set()
        self.persist_config()
        self.persist_queue()
        self.force_cleanup()
        try:
            self.destroy()
        except Exception:
            pass

    def force_cleanup(self):
        self.stop_event.set()
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.quit()
        except Exception:
            pass


# Backward compatibility alias
SpotifastCompanionApp = SoulMusicApp


if __name__ == "__main__":
    app = SoulMusicApp()
    app.mainloop()
