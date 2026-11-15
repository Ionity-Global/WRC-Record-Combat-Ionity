# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Settings. Everything has a working default; config.json only needs the
values you want to change. It lives next to the EXE (or the script)."""
import json
import os
import sys
from dataclasses import asdict, dataclass, field


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_output_dir():
    return os.path.join(os.path.expanduser("~"), "Videos", "WRC")


@dataclass
class Config:
    # --- what starts a recording ---------------------------------------
    trigger_mode: str = "enemy"        # enemy | pvp_combat | any_combat
    linger_seconds: float = 10.0       # keep recording this long after the enemy is gone
    start_confirm: int = 2             # readings in a row before starting
    min_clip_seconds: float = 5.0      # shorter clips are deleted
    max_clip_minutes: float = 30.0     # longer fights are split into files of this length

    # --- death cam and AFK ----------------------------------------------
    deathcam: bool = True              # record every fight on standby; keep it only if you die
    deathcam_seconds: float = 20.0     # how much to keep from before the death
    deathcam_after: float = 5.0        # and how long to keep rolling after it
    afk_record: bool = True            # keep the clip when you are attacked while AFK

    # --- video (auto-attuned; "auto"/0 means let WRC decide) -----------
    output_dir: str = field(default_factory=default_output_dir)
    container: str = "mp4"             # mp4 | mkv
    codec: str = "auto"                # auto | av1 | hevc | h264
    fps: int = 0                       # 0 = match the monitor, capped at 60
    quality: int = 0                   # 0 = auto. Lower = better and bigger (sane range 20-36)
    max_height: int = 0                # 0 = native. e.g. 1440 downscales a 4K screen
    bits_per_pixel: float = 0.045      # bitrate ceiling = width * height * fps * this
    audio_device: str = "auto"         # auto | none | exact DirectShow device name
    max_storage_gb: float = 20.0       # oldest clips are deleted beyond this. 0 = never delete

    # --- detection -----------------------------------------------------
    wow_path: str = ""                 # World of Warcraft folder, if WRC cannot find it (for the in-game clip list)
    hotkey: str = "ctrl+alt+r"         # quick record key, works while WoW has focus. "" = off
    scan_hz: float = 8.0               # beacon readings per second
    ffmpeg_path: str = ""              # empty = find automatically

    def max_bitrate(self, width, height, fps):
        return max(1_500_000, int(width * height * fps * self.bits_per_pixel))


def config_path():
    return os.path.join(app_dir(), "config.json")


def load(path=None):
    path = path or config_path()
    cfg = Config()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, type(getattr(cfg, key))(value))
    return cfg


def save(cfg, path=None):
    path = path or config_path()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(asdict(cfg), fh, indent=2)
    return path
