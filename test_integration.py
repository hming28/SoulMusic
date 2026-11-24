import os
import shutil
import time
import tkinter as tk
import pygame
from soulmusic import SoulMusicApp, AUDIO_CACHE_DIR
SpotifastCompanionApp = SoulMusicApp


def test_integration():
    app = SpotifastCompanionApp()
    app.withdraw()

    # 1. Test playback with cached track
    print("1. Testing start_playback with cached track...")
    test_mp3 = None
    for f in os.listdir(AUDIO_CACHE_DIR):
        if f.endswith(".mp3"):
            test_mp3 = os.path.join(AUDIO_CACHE_DIR, f)
            break
    assert test_mp3 is not None, "No cached track found for test"
    app.start_playback(test_mp3, start_sec=0.0)

    for _ in range(30):
        app.update()
        while not app.ui_queue.empty():
            task = app.ui_queue.get_nowait()
            task()
        if app.is_playing:
            break
        time.sleep(0.05)

    print(f"Is playing: {app.is_playing}, Current song: {app.current_song.get()}, Duration: {app.total_duration:.2f}s")
    assert app.is_playing, "Expected playback to have started"
    assert app.total_duration > 0, "Expected non-zero duration"

    # 2. Test seeking
    print("2. Testing seeking to 45s...")
    app.seek_to(45.0)
    app.update()
    print(f"After seek to 45s: seek_offset={app.seek_offset_seconds}, progress_scale={app.progress_scale.get()}")
    assert app.seek_offset_seconds == 45.0

    # 3. Test volume
    print("3. Testing volume control to 60%...")
    app.set_volume(60)
    app.update()
    assert app.volume == 60
    assert abs(pygame.mixer.music.get_volume() - 0.6) < 0.05
    print("Volume verified: 60%")

    # 4. Test Pause and Resume
    print("4. Testing pause and resume...")
    app.toggle_play_pause()
    app.update()
    assert app.is_paused
    print("Paused successfully")

    app.toggle_play_pause()
    app.update()
    assert not app.is_paused
    assert app.is_playing
    print("Resumed successfully")

    # 5. Test Stop and File Lock Release
    print("5. Testing stop and file lock release...")
    app.stop_music()
    app.update()
    assert not app.is_playing
    assert not app.is_paused
    assert app.seek_offset_seconds == 0.0

    # Verify audio file is not locked on disk
    curr_f = app.current_file
    if curr_f and os.path.exists(curr_f):
        tmp_check = curr_f + ".test_rename"
        os.rename(curr_f, tmp_check)
        os.rename(tmp_check, curr_f)
        print("File handle verified released (no WinError 32 lock)")

    # 6. Test Spotify URL search via search_entry
    print("6. Testing Spotify URL input in search_entry...")
    spotify_url = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
    app.search_entry.delete(0, tk.END)
    app.search_entry.insert(0, spotify_url)
    app.on_manual_search()

    # Wait up to 15 seconds for Spotify track to resolve and load
    for _ in range(150):
        app.update()
        while not app.ui_queue.empty():
            task = app.ui_queue.get_nowait()
            task()
        if ("Rick Astley" in app.current_song.get() or "Never Gonna Give You Up" in app.current_song.get()) and app.is_playing:
            break
        time.sleep(0.1)

    print(f"Spotify URL resolved: {app.current_song.get()}, is_playing={app.is_playing}")
    assert "Rick Astley" in app.current_song.get() or "Never Gonna Give You Up" in app.current_song.get(), f"Expected track title, got {app.current_song.get()}"
    assert app.is_playing, "Expected Spotify track playback to start"

    # 7. Clean up
    print("7. Testing clean up and shutdown...")
    app.force_cleanup()
    app.destroy()
    print("All integration tests passed successfully!")


if __name__ == "__main__":
    test_integration()

