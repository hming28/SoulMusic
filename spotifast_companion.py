"""
Spotifast Companion (Legacy Entry Point)
This module provides backward compatibility with the original Spotifast Companion.
Please use soulmusic.py for new developments.
"""
from soulmusic import *
from soulmusic import (
    SoulMusicApp,
    SoulMusicApp as SpotifastCompanionApp,
    format_time,
    parse_spotify_track_info,
    SPOTIFY_TRACK_REGEX,
    AUDIO_CACHE_DIR,
)

if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    app = SoulMusicApp(root)
    root.mainloop()
