import os
import sys
import time
import shutil
import unittest
import tkinter as tk
from tkinter import ttk

import pygame

# Import companion module
import spotifast_companion
from spotifast_companion import (
    SpotifastCompanionApp,
    format_time,
    parse_spotify_track_info,
    SPOTIFY_TRACK_REGEX,
    AUDIO_CACHE_DIR,
)


class TestPhase1AudioCoreAndControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()  # Hide GUI window during tests
        cls.app = SpotifastCompanionApp(cls.root)

        # Find an existing test MP3 in cache or fallback to sibling cache
        cls.test_mp3 = None
        os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
        for f in os.listdir(AUDIO_CACHE_DIR):
            if f.endswith(".mp3"):
                p = os.path.join(AUDIO_CACHE_DIR, f)
                if os.path.getsize(p) > 10000:
                    cls.test_mp3 = p
                    break
        if not cls.test_mp3:
            for fallback_dir in [r"D:\Spotifast\cache", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Spotifast", "cache")]:
                if os.path.exists(fallback_dir):
                    for f in os.listdir(fallback_dir):
                        if f.endswith(".mp3"):
                            src = os.path.join(fallback_dir, f)
                            if os.path.getsize(src) > 10000:
                                dst = os.path.join(AUDIO_CACHE_DIR, f)
                                shutil.copy2(src, dst)
                                cls.test_mp3 = dst
                                break
                    if cls.test_mp3:
                        break

        if not cls.test_mp3:
            raise RuntimeError("No cached mp3 found for testing in " + AUDIO_CACHE_DIR)
        print(f"Using test MP3: {cls.test_mp3}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.force_cleanup()
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        # Ensure mixer is initialized
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)

    def test_01_format_time(self):
        """Test time formatting utility"""
        self.assertEqual(format_time(0), "00:00")
        self.assertEqual(format_time(59), "00:59")
        self.assertEqual(format_time(60), "01:00")
        self.assertEqual(format_time(75), "01:15")
        self.assertEqual(format_time(3600), "01:00:00")
        self.assertEqual(format_time(3665), "01:01:05")
        self.assertEqual(format_time(-10), "00:00")
        self.assertEqual(format_time(None), "00:00")
        # Defensive robust inputs
        self.assertEqual(format_time(float("nan")), "00:00")
        self.assertEqual(format_time(float("inf")), "00:00")
        self.assertEqual(format_time("invalid"), "00:00")

    def test_02_ui_widgets_initialized(self):
        """Verify all Phase 1 UI controls exist"""
        self.assertIsNotNone(self.app.progress_scale)
        self.assertIsNotNone(self.app.time_curr_label)
        self.assertIsNotNone(self.app.time_total_label)
        self.assertIsNotNone(self.app.btn_prev)
        self.assertIsNotNone(self.app.btn_play_pause)
        self.assertIsNotNone(self.app.btn_stop)
        self.assertIsNotNone(self.app.btn_next)
        self.assertIsNotNone(self.app.vol_scale)
        self.assertIsNotNone(self.app.vol_val_label)
        self.assertIsNotNone(self.app.search_entry)
        self.assertIsNotNone(self.app.search_btn)

    def test_03_volume_control_realtime(self):
        """Verify volume adjusts in real-time and reflects in pygame.mixer"""
        self.app.set_volume(50)
        self.assertEqual(self.app.volume, 50)
        self.assertEqual(self.app.vol_val_label.cget("text"), "50%")
        # pygame volume is a float between 0.0 and 1.0
        vol = pygame.mixer.music.get_volume()
        self.assertAlmostEqual(vol, 0.5, delta=0.05)

        self.app.set_volume(100)
        self.assertEqual(self.app.volume, 100)
        self.assertAlmostEqual(pygame.mixer.music.get_volume(), 1.0, delta=0.05)

        self.app.set_volume(0)
        self.assertEqual(self.app.volume, 0)
        self.assertAlmostEqual(pygame.mixer.music.get_volume(), 0.0, delta=0.05)

        # Restore default volume
        self.app.set_volume(80)

    def test_04_playback_and_duration(self):
        """Verify starting playback loads audio, sets duration, and updates UI"""
        self.app.current_song.set("Test Audio Track")
        self.app.start_playback(self.test_mp3, start_sec=0.0)

        self.assertTrue(self.app.is_playing)
        self.assertFalse(self.app.is_paused)
        self.assertGreater(self.app.total_duration, 10.0)
        self.assertEqual(self.app.current_file, self.test_mp3)
        self.assertEqual(self.app.btn_play_pause.cget("text"), "⏸ 暂停")

        expected_total_str = format_time(self.app.total_duration)
        self.assertEqual(self.app.time_total_label.cget("text"), expected_total_str)
        self.assertAlmostEqual(self.app.progress_scale.cget("to"), self.app.total_duration, delta=1.0)

    def test_05_seek_functionality(self):
        """Verify absolute timestamp seek mechanism while playing and paused"""
        self.app.start_playback(self.test_mp3, start_sec=0.0)
        time.sleep(0.2)

        target_seek = 30.0
        self.app.seek_to(target_seek)
        self.assertEqual(self.app.seek_offset_seconds, target_seek)
        self.assertAlmostEqual(self.app.progress_scale.get(), target_seek, delta=0.5)
        self.assertEqual(self.app.time_curr_label.cget("text"), format_time(target_seek))
        self.assertTrue(self.app.is_playing)

        # Test seek while paused
        self.app.toggle_play_pause()  # pause
        self.assertTrue(self.app.is_paused)

        target_seek_paused = 50.0
        self.app.seek_to(target_seek_paused)
        self.assertEqual(self.app.seek_offset_seconds, target_seek_paused)
        self.assertTrue(self.app.is_paused)

        # Resume
        self.app.toggle_play_pause()
        self.assertFalse(self.app.is_paused)
        self.assertTrue(self.app.is_playing)

    def test_06_toggle_play_pause(self):
        """Verify toggle play/pause transitions state and button labels"""
        self.app.start_playback(self.test_mp3, start_sec=0.0)
        self.assertTrue(self.app.is_playing)
        self.assertFalse(self.app.is_paused)
        self.assertEqual(self.app.btn_play_pause.cget("text"), "⏸ 暂停")

        # Pause
        self.app.toggle_play_pause()
        self.assertTrue(self.app.is_paused)
        self.assertEqual(self.app.btn_play_pause.cget("text"), "▶ 继续")

        # Unpause
        self.app.toggle_play_pause()
        self.assertFalse(self.app.is_paused)
        self.assertEqual(self.app.btn_play_pause.cget("text"), "⏸ 暂停")

    def test_07_stop_music(self):
        """Verify stop music resets state, slider, and timer labels"""
        self.app.start_playback(self.test_mp3, start_sec=10.0)
        self.app.stop_music()

        self.assertFalse(self.app.is_playing)
        self.assertFalse(self.app.is_paused)
        self.assertEqual(self.app.seek_offset_seconds, 0.0)
        self.assertEqual(self.app.progress_scale.get(), 0.0)
        self.assertEqual(self.app.time_curr_label.cget("text"), "00:00")
        self.assertEqual(self.app.btn_play_pause.cget("text"), "▶ 播放")
        self.assertFalse(pygame.mixer.music.get_busy())

    def test_08_spacebar_focus_guard(self):
        """Verify spacebar toggles playback only when entry is not focused"""
        self.app.start_playback(self.test_mp3, start_sec=0.0)

        # When event widget is search_entry, spacebar should NOT toggle
        class DummyEvent:
            def __init__(self, w):
                self.widget = w

        entry_event = DummyEvent(self.app.search_entry)
        res = self.app.on_spacebar(entry_event)
        self.assertIsNone(res)
        self.assertFalse(self.app.is_paused)

        # When event widget is outside (e.g. root or button), spacebar toggles pause
        other_event = DummyEvent(self.app.btn_play_pause)
        res = self.app.on_spacebar(other_event)
        self.assertEqual(res, "break")
        self.assertTrue(self.app.is_paused)

    def test_09_playlist_navigation(self):
        """Verify Previous and Next buttons operate on playlist queue"""
        # Find 3 real cached MP3 video IDs
        cached_ids = []
        for f in os.listdir(AUDIO_CACHE_DIR):
            if f.endswith(".mp3"):
                cached_ids.append(f[:-4])
                if len(cached_ids) >= 3:
                    break

        self.app.playlist = [
            {"title": f"Track {i}", "artist": f"Artist {i}", "display": f"Artist {i} - Track {i}", "video_id": cid}
            for i, cid in enumerate(cached_ids)
        ]
        self.app.current_index = 0

        # Next -> index 1
        self.app.current_index = 0
        self.app.play_next()
        self.assertEqual(self.app.current_index, 1)

        # Next -> index 2
        self.app.play_next()
        self.assertEqual(self.app.current_index, 2)

        # Next from last track -> loops to 0
        self.app.play_next()
        self.assertEqual(self.app.current_index, 0)

        # Prev within 3 seconds -> previous track
        self.app.current_index = 2
        self.app.seek_offset_seconds = 1.0  # < 3 seconds
        self.app.is_playing = False
        self.app.play_prev()
        self.assertEqual(self.app.current_index, 1)

    def test_10_cleanup_and_exit_guard(self):
        """Verify cleanup terminates audio mixer without lingering"""
        self.app.start_playback(self.test_mp3, start_sec=0.0)
        self.assertTrue(self.app.is_playing)
        self.app.force_cleanup()
        self.assertTrue(pygame.mixer.get_init() is None or not pygame.mixer.music.get_busy())

    def test_11_seek_boundary_edge_cases(self):
        """Test seek with boundary values (negative, beyond total duration, empty track)"""
        self.app.start_playback(self.test_mp3, start_sec=0.0)
        dur = self.app.total_duration

        # Negative seek
        self.app.seek_to(-20.0)
        self.assertEqual(self.app.seek_offset_seconds, 0.0)

        # Seek past end
        self.app.seek_to(dur + 1000.0)
        self.assertAlmostEqual(self.app.seek_offset_seconds, max(0.0, dur - 0.1), delta=0.2)

        # Seek with no file
        self.app.current_file = None
        self.app.total_duration = 0.0
        self.app.seek_to(50.0)  # should not crash
        self.assertEqual(self.app.current_file, None)

    def test_12_empty_playlist_and_single_track(self):
        """Test navigation on empty playlist and single-track playlist"""
        self.app.playlist = []
        self.app.current_index = -1
        # Should not raise exception
        self.app.play_next()
        self.app.play_prev()

        # Single track with real cached id
        cached_id = os.path.basename(self.test_mp3)[:-4]
        self.app.playlist = [
            {"title": "Only One", "artist": "Artist", "display": "Artist - Only One", "video_id": cached_id}
        ]
        self.app.current_index = 0
        self.app.play_next()
        self.assertEqual(self.app.current_index, 0)

    def test_13_volume_boundary_values(self):
        """Test volume with edge inputs"""
        self.app.set_volume(0)
        self.assertEqual(self.app.volume, 0)
        self.app.set_volume(100)
        self.assertEqual(self.app.volume, 100)
        self.app.set_volume("45.6")
        self.assertEqual(self.app.volume, 45)

    def test_14_file_unlock_after_stop(self):
        """Verify that stop_music unloads mixer and unlocks file handle on disk"""
        temp_file = os.path.join(AUDIO_CACHE_DIR, "test_file_lock_check.mp3")
        shutil.copyfile(self.test_mp3, temp_file)
        try:
            self.app.start_playback(temp_file, start_sec=0.0)
            time.sleep(0.1)
            self.app.stop_music()

            # Attempt file removal - if file is still locked, Windows throws PermissionError
            os.remove(temp_file)
            self.assertFalse(os.path.exists(temp_file))
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def test_15_spotify_url_recognition_and_embed_parsing(self):
        """Verify Spotify URL regex and structured Embed metadata extraction"""
        test_urls = [
            ("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT", "4cOdK2wGLETKBW3PvgPWqT"),
            ("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc123xyz", "4cOdK2wGLETKBW3PvgPWqT"),
            ("https://open.spotify.com/intl-ja/track/4cOdK2wGLETKBW3PvgPWqT", "4cOdK2wGLETKBW3PvgPWqT"),
            ("spotify:track:4cOdK2wGLETKBW3PvgPWqT", "4cOdK2wGLETKBW3PvgPWqT"),
        ]
        for url, expected_id in test_urls:
            m = SPOTIFY_TRACK_REGEX.search(url)
            self.assertIsNotNone(m, f"Failed regex match for {url}")
            self.assertEqual(m.group(1), expected_id)

        # Real embed fetch test
        info = parse_spotify_track_info("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "Never Gonna Give You Up")
        self.assertIn("Rick Astley", info["artist"])
        self.assertGreater(info["duration"], 200.0)

    def test_16_search_entry_accepts_spotify_url(self):
        """Verify entering Spotify URL into search bar detects and parses Spotify URL"""
        self.app.search_entry.delete(0, tk.END)
        self.app.search_entry.insert(0, "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
        # Trigger on_manual_search
        self.app.on_manual_search()
        for _ in range(20):
            self.root.update()
            while not self.app.ui_queue.empty():
                self.app.ui_queue.get_nowait()()
            if "Rick Astley" in self.app.status_text.get() or "Rick Astley" in self.app.current_song.get():
                break
            time.sleep(0.05)
        # Ensure status was successfully resolved from Spotify URL to track name
        current_status = self.app.status_text.get()
        current_song = self.app.current_song.get()
        self.assertTrue(
            "Rick Astley" in current_status or "Rick Astley" in current_song or "Spotify" in current_status,
            f"Unexpected status: {current_status}, song: {current_song}",
        )

    def test_17_rapid_track_switch_request_invalidation(self):
        """Verify rapid track switches increment play_request_id and invalidate stale downloads"""
        old_req = self.app.play_request_id
        cached_id = os.path.basename(self.test_mp3)[:-4]
        self.app.playlist = [
            {"title": "Song 1", "display": "Artist - Song 1", "video_id": cached_id, "duration": 180},
            {"title": "Song 2", "display": "Artist - Song 2", "video_id": cached_id, "duration": 180},
        ]
        self.app.play_track_at_index(0)
        req1 = self.app.play_request_id
        self.assertGreater(req1, old_req)

        self.app.play_track_at_index(1)
        req2 = self.app.play_request_id
        self.assertGreater(req2, req1)

        # Verify stale request does not initiate playback
        stale_track = {"title": "Stale", "display": "Stale Track", "video_id": "dummy_stale"}
        self.app._resolve_and_play_track(stale_track, req_id=req1)
        # Current file should not be updated to dummy_stale
        self.assertNotEqual(self.app.current_file, "dummy_stale")

    def test_18_get_or_download_audio_edge_cases(self):
        """Test edge inputs to get_or_download_audio (None, empty string, invalid type)"""
        self.assertIsNone(self.app.get_or_download_audio(None))
        self.assertIsNone(self.app.get_or_download_audio(""))
        self.assertIsNone(self.app.get_or_download_audio("   "))
        self.assertIsNone(self.app.get_or_download_audio(12345))

    def test_19_theme_toggle_and_entry_colors(self):
        """Verify white theme default and dark theme font/background color fix"""
        # 1. 默认浅色/白色主题验证
        self.assertEqual(self.app.theme_mode, "light")
        self.assertEqual(self.app.search_entry.cget("bg"), "#FFFFFF")
        self.assertEqual(self.app.search_entry.cget("fg"), "#111827")
        self.assertEqual(self.app.search_entry.cget("insertbackground"), "#111827")

        # 2. 切换至暗黑主题：输入框背景深色(#282828)，字体纯白(#FFFFFF)，光标白色(#FFFFFF)
        self.app.toggle_theme()
        self.assertEqual(self.app.theme_mode, "dark")
        self.assertEqual(self.app.search_entry.cget("bg"), "#282828")
        self.assertEqual(self.app.search_entry.cget("fg"), "#FFFFFF")
        self.assertEqual(self.app.search_entry.cget("insertbackground"), "#FFFFFF")

        # 3. 再次切换回浅色/白色主题
        self.app.toggle_theme()
        self.assertEqual(self.app.theme_mode, "light")
        self.assertEqual(self.app.search_entry.cget("bg"), "#FFFFFF")
        self.assertEqual(self.app.search_entry.cget("fg"), "#111827")


if __name__ == "__main__":
    unittest.main()
