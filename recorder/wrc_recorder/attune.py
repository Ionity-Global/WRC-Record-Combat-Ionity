# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Auto-attune: find FFmpeg, then find by trial the best encoder, option set
and screen-capture method this PC can actually run. Nothing is assumed from
the hardware name; every choice is proven with a short real test."""
import io
import json
import logging
import os
import re
import shutil
import urllib.request
import zipfile
from dataclasses import asdict, dataclass

from . import winutil
from .config import app_dir

log = logging.getLogger("wrc")

FFMPEG_URL = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
              "ffmpeg-master-latest-win64-gpl.zip")

# Best compression first. (name, codec family, kind)
ENCODERS = [
    ("av1_nvenc", "av1", "nvenc"), ("hevc_nvenc", "hevc", "nvenc"),
    ("av1_amf", "av1", "amf"), ("hevc_amf", "hevc", "amf"),
    ("av1_qsv", "av1", "qsv"), ("hevc_qsv", "hevc", "qsv"),
    ("h264_nvenc", "h264", "nvenc"), ("h264_amf", "h264", "amf"), ("h264_qsv", "h264", "qsv"),
    ("libx264", "h264", "cpu"), ("libx265", "hevc", "cpu"),
]
DEFAULT_QUALITY = {"av1": 32, "hevc": 27, "h264": 23}
CAPTURE_MODES = ["dda_gpu_init", "dda_gpu", "dda_cpu", "gdi"]
LOOPBACK_HINTS = ("stereo mix", "virtual-audio-capturer", "cable output", "what u hear",
                  "loopback", "voicemeeter out")


@dataclass
class Plan:
    ffmpeg: str
    encoder: str = "libx264"
    family: str = "h264"
    kind: str = "cpu"
    variant: int = 0
    capture: str = "gdi"
    audio: str = ""          # DirectShow device name, empty = no audio


def encoder_variants(kind, family, quality, maxrate, fps):
    """Option sets for an encoder kind, richest first. The probe keeps the first that runs."""
    q, mr, buf = str(quality), str(maxrate), str(maxrate * 2)
    target = str(int(maxrate * 0.6))
    gop = ["-g", str(int(fps) * 2)]
    if kind == "nvenc":
        capped = ["-rc", "vbr", "-cq", q, "-b:v", "0", "-maxrate", mr, "-bufsize", buf]
        sets = [
            ["-preset", "p5", "-tune", "hq"] + capped + ["-spatial-aq", "1", "-temporal-aq", "1"],
            ["-preset", "p5"] + capped,
            ["-b:v", target, "-maxrate", mr, "-bufsize", buf],
        ]
    elif kind == "amf":
        sets = [
            ["-usage", "transcoding", "-quality", "quality", "-rc", "vbr_peak",
             "-b:v", target, "-maxrate", mr, "-bufsize", buf],
            ["-b:v", target, "-maxrate", mr],
        ]
    elif kind == "qsv":
        sets = [
            ["-preset", "medium", "-global_quality", q],
            ["-b:v", target, "-maxrate", mr],
        ]
    elif family == "hevc":
        sets = [["-preset", "ultrafast", "-crf", q]]
    else:
        sets = [["-preset", "veryfast", "-crf", q, "-maxrate", mr, "-bufsize", buf]]
    return [s + gop for s in sets]


def find_ffmpeg(cfg):
    base = app_dir()
    exe = "ffmpeg.exe" if winutil.IS_WINDOWS else "ffmpeg"
    for cand in (cfg.ffmpeg_path, os.path.join(base, exe), os.path.join(base, "ffmpeg", "bin", exe),
                 os.path.join(base, "ffmpeg", exe), shutil.which("ffmpeg")):
        if cand and os.path.isfile(cand):
            return cand
    return None


def download_ffmpeg():
    """Fetch FFmpeg next to the app (Windows only). Returns its path or None."""
    if not winutil.IS_WINDOWS:
        return None
    target = os.path.join(app_dir(), "ffmpeg.exe")
    log.info("FFmpeg not found. Downloading it once (about 150 MB) ...")
    try:
        with urllib.request.urlopen(FFMPEG_URL, timeout=60) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            name = next(n for n in zf.namelist() if n.endswith("bin/ffmpeg.exe"))
            with zf.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
        log.info("FFmpeg saved to %s", target)
        return target
    except Exception as exc:
        log.error("Could not download FFmpeg (%s). Put ffmpeg.exe next to WRC-Recorder.exe.", exc)
        return None


def probe_encoder(ffmpeg, name, opts):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
           "testsrc2=s=640x360:r=30", "-frames:v", "10", "-pix_fmt", "yuv420p",
           "-c:v", name] + opts + ["-f", "null", "-"]
    code, _, _ = winutil.run(cmd, timeout=30)
    return code == 0


def list_audio_devices(ffmpeg):
    if not winutil.IS_WINDOWS:
        return []
    _, _, err = winutil.run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], 15)
    return re.findall(r'"([^"]+)"\s+\(audio\)', err)


def audio_flow(ffmpeg, device, seconds=2.0):
    """Capture a moment of audio from a device. Returns (fraction of the expected
    data that arrived, peak level 0..1). A device that delivers little or nothing
    must not be recorded: FFmpeg would hold the video back waiting for it."""
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "dshow", "-i", "audio=" + device,
           "-t", str(seconds), "-ac", "2", "-ar", "48000", "-f", "s16le", "-"]
    import time
    t0 = time.time()
    code, raw, _ = winutil.run(cmd, timeout=seconds + 10)
    took = time.time() - t0
    if code != 0 or not raw:
        return 0.0, 0.0
    import numpy as np
    samples = np.frombuffer(raw[:len(raw) // 2 * 2], dtype=np.int16)
    fraction = len(raw) / (seconds * 48000 * 4)
    if took > seconds * 2.5:                 # arrived, but far slower than real time
        fraction = min(fraction, seconds / took)
    return fraction, float(np.abs(samples.astype(np.int32)).max()) / 32768.0


def pick_audio(cfg, ffmpeg):
    if cfg.audio_device.lower() == "none":
        return ""
    devices = list_audio_devices(ffmpeg)
    if cfg.audio_device.lower() != "auto":
        if cfg.audio_device in devices:
            return cfg.audio_device
        log.warning("Audio device %r not found. Available: %s", cfg.audio_device, devices)
        return ""
    for dev in devices:
        if any(h in dev.lower() for h in LOOPBACK_HINTS):
            fraction, peak = audio_flow(ffmpeg, dev)
            if fraction >= 0.8 and peak >= 0.002:
                return dev
            log.info("Audio device %r skipped: %s. Recording an audio device adds about 2 s to "
                     "every start, so a silent one is not worth it. Route the game sound to it "
                     "and run --attune, or name a device in config.json.", dev,
                     "it is silent (game sound is not routed to it)" if fraction >= 0.8
                     else "it delivers only %.0f%% of real time" % (fraction * 100))
    return ""


def quality_for(cfg, family):
    return cfg.quality if cfg.quality > 0 else DEFAULT_QUALITY[family]


def attune(cfg, ffmpeg, capture_test=None):
    """Probe encoders (and, through capture_test(plan) -> bool, capture methods).
    Returns the first Plan that works end to end."""
    want = cfg.codec.lower()
    plan = None
    for name, family, kind in ENCODERS:
        if want != "auto" and family != want:
            continue
        if want == "auto" and name == "libx265":
            continue                      # too slow to be a sensible automatic choice
        variants = encoder_variants(kind, family, quality_for(cfg, family), 8_000_000, 60)
        for idx, opts in enumerate(variants):
            if not probe_encoder(ffmpeg, name, opts):
                continue
            log.info("Encoder %s works (option set %d)", name, idx)
            plan = Plan(ffmpeg=ffmpeg, encoder=name, family=family, kind=kind, variant=idx)
            if capture_test is None:
                return plan
            for mode in CAPTURE_MODES:
                if mode.startswith("dda_gpu") and kind not in ("nvenc", "amf"):
                    continue
                plan.capture = mode
                if capture_test(plan):
                    log.info("Screen capture method %s works with %s", mode, name)
                    return plan
            log.info("%s encodes but no capture method worked with it; trying the next encoder", name)
            break
    if plan is None:
        raise RuntimeError("No working video encoder found. Is this a complete FFmpeg build?")
    plan.capture = "gdi"
    return plan


def cache_path():
    return os.path.join(app_dir(), "attune.json")


def load_cached(cfg, ffmpeg):
    try:
        with open(cache_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("_key") != _key(cfg, ffmpeg):
            return None
        data.pop("_key")
        return Plan(**data)
    except Exception:
        return None


def save_cached(cfg, plan):
    data = asdict(plan)
    data["_key"] = _key(cfg, plan.ffmpeg)
    try:
        with open(cache_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def _key(cfg, ffmpeg):
    try:
        stamp = int(os.path.getmtime(ffmpeg))
    except OSError:
        stamp = 0
    return "v2|%s|%s|%s|%s" % (ffmpeg, stamp, cfg.codec, cfg.audio_device)
