# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Builds the FFmpeg command line and runs one recording at a time."""
import logging
import os
import subprocess
import time
from dataclasses import dataclass

from . import winutil
from .attune import encoder_variants, quality_for

log = logging.getLogger("wrc")


@dataclass
class Geometry:
    """What to capture. Monitor values are screen pixels; the crop is relative to the monitor."""
    mon_left: int
    mon_top: int
    mon_width: int
    mon_height: int
    output_idx: int = 0
    crop_x: int = 0
    crop_y: int = 0
    crop_w: int = 0          # 0 = whole monitor
    crop_h: int = 0
    fps: int = 60

    @property
    def cropped(self):
        return self.crop_w > 0 and (self.crop_w, self.crop_h) != (self.mon_width, self.mon_height)

    @property
    def width(self):
        return (self.crop_w or self.mon_width) // 2 * 2      # encoders need even sizes

    @property
    def height(self):
        return (self.crop_h or self.mon_height) // 2 * 2


def build_command(plan, cfg, geom, out_path=None, duration=None):
    """FFmpeg arguments for one recording. out_path=None encodes to nowhere (used for tests)."""
    w, h, fps = geom.width, geom.height, int(geom.fps)
    cpu_encoder = plan.kind == "cpu"
    pix = "yuv420p" if cpu_encoder else "nv12"
    scale = bool(cfg.max_height) and h > cfg.max_height
    out_w, out_h = (int(w * cfg.max_height / h) // 2 * 2, cfg.max_height) if scale else (w, h)

    mode = plan.capture
    if scale and mode.startswith("dda_gpu"):
        mode = "dda_cpu"                 # scaling is done on downloaded frames

    cmd = [plan.ffmpeg, "-hide_banner", "-loglevel", "warning", "-y"]
    audio_in = (["-f", "dshow", "-i", "audio=" + plan.audio]
                if plan.audio else [])
    scale_f = "scale=-2:%d:flags=bicubic" % cfg.max_height

    if mode in ("dda_gpu_init", "dda_gpu", "dda_cpu"):
        src = "ddagrab=output_idx=%d:framerate=%d" % (geom.output_idx, fps)
        if geom.cropped or (w, h) != (geom.mon_width, geom.mon_height):
            src += ":video_size=%dx%d:offset_x=%d:offset_y=%d" % (w, h, geom.crop_x, geom.crop_y)
        if mode == "dda_cpu":
            src += ",hwdownload,format=bgra"
            if scale:
                src += "," + scale_f
            src += ",format=" + pix
        if mode == "dda_gpu_init":
            cmd += ["-init_hw_device", "d3d11va"]
        cmd += audio_in + ["-filter_complex", src + "[v]", "-map", "[v]"]
        if plan.audio:
            cmd += ["-map", "0:a"]
    else:  # gdi
        cmd += ["-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1",
                "-offset_x", str(geom.mon_left + geom.crop_x), "-offset_y", str(geom.mon_top + geom.crop_y),
                "-video_size", "%dx%d" % (w, h), "-i", "desktop"]
        cmd += audio_in
        cmd += ["-vf", (scale_f + "," if scale else "") + "format=" + pix, "-map", "0:v"]
        if plan.audio:
            cmd += ["-map", "1:a"]

    maxrate = cfg.max_bitrate(out_w, out_h, fps)
    variants = encoder_variants(plan.kind, plan.family, quality_for(cfg, plan.family), maxrate, fps)
    cmd += ["-c:v", plan.encoder] + variants[min(plan.variant, len(variants) - 1)]
    # Constant frame rate. Measured on real hardware: with an audio input and the
    # default variable rate, FFmpeg kept as few as 1 frame in 6; with this, all of them.
    cmd += ["-fps_mode", "cfr", "-r", str(fps)]
    if plan.audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    if duration:
        cmd += ["-t", str(duration)]

    if out_path is None:
        return cmd + ["-f", "null", "-"]
    if out_path.lower().endswith(".mp4"):
        if plan.family == "hevc":
            cmd += ["-tag:v", "hvc1"]
        cmd += ["-movflags", "+faststart"]
    return cmd + [out_path]


class Recorder:
    def __init__(self, plan, cfg):
        self.plan, self.cfg = plan, cfg
        self.proc = None
        self.path = None
        self.label = ""
        self.started = 0.0
        self._errlog = None

    @property
    def active(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, geom, label, character=""):
        """label: Alliance / Horde / Manual. character: who was played, added to the file name."""
        os.makedirs(self.cfg.output_dir, exist_ok=True)
        who = "".join(c for c in character if c.isalpha())[:12]
        name = "WRC_%s_%s%s.%s" % (label, who + "_" if who else "", time.strftime("%Y%m%d_%H%M%S"),
                                   self.cfg.container)
        self.path = os.path.join(self.cfg.output_dir, name)
        self.label = label
        cmd = build_command(self.plan, self.cfg, geom, self.path)
        log.debug("ffmpeg: %s", " ".join(cmd))
        self._errlog = open(os.path.join(self.cfg.output_dir, "ffmpeg-last.log"), "wb")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                     stderr=self._errlog, creationflags=winutil.NO_WINDOW)
        self.started = time.time()
        log.info("REC  start -> %s", name)

    def stop(self, keep_short=False, discard=False, final_label=None):
        """Finish the file cleanly. Returns (path, seconds) or (None, 0) when nothing was kept.
        keep_short : keep the clip however short it is (recordings you started by hand)
        discard    : throw the clip away (a standby recording that turned out not to matter)
        final_label: rename the clip to carry this label instead of the one it started with"""
        if self.proc is None:
            return None, 0.0
        seconds = time.time() - self.started
        crashed = self.proc.poll() is not None
        if not crashed:
            try:
                self.proc.stdin.write(b"q")       # FFmpeg's own "finish and close the file"
                self.proc.stdin.flush()
            except OSError:
                pass
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        if self._errlog:
            self._errlog.close()
        path, self.proc = self.path, None
        ok = path and os.path.exists(path) and os.path.getsize(path) > 0 and not crashed
        if discard or not ok or (seconds < self.cfg.min_clip_seconds and not keep_short):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            if discard and ok:
                log.debug("standby recording dropped (%.0fs)", seconds)
            else:
                log.info("REC  discarded (%s)", "encoder stopped early, see ffmpeg-last.log" if crashed
                         else "shorter than %.0fs" % self.cfg.min_clip_seconds)
            return None, 0.0
        if final_label and final_label != self.label:
            renamed = os.path.join(os.path.dirname(path), os.path.basename(path).replace(
                "WRC_%s_" % self.label, "WRC_%s_" % final_label, 1))
            try:
                os.replace(path, renamed)
                path = renamed
            except OSError:
                pass
        log.info("REC  saved %s  %.0fs  %.1f MB", os.path.basename(path), seconds,
                 os.path.getsize(path) / 1e6)
        return path, seconds


def trim_tail(ffmpeg, path, seconds):
    """Cut a clip down to its last `seconds` (no re-encode, so it is instant and
    lossless; the cut lands on the nearest keyframe, at most 2 s early).
    Returns True when the clip was trimmed."""
    tmp = path + ".trim" + os.path.splitext(path)[1]
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-sseof", "-%s" % seconds, "-i", path,
           "-c", "copy", "-movflags", "+faststart", tmp]
    code, _, _ = winutil.run(cmd, timeout=60)
    if code == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        os.replace(tmp, path)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def enforce_storage(cfg):
    """Delete the oldest WRC clips once the folder is over the size limit."""
    if cfg.max_storage_gb <= 0 or not os.path.isdir(cfg.output_dir):
        return
    clips = [os.path.join(cfg.output_dir, f) for f in os.listdir(cfg.output_dir)
             if f.startswith("WRC_") and f.lower().endswith((".mp4", ".mkv"))]
    clips.sort(key=os.path.getmtime)
    total = sum(os.path.getsize(c) for c in clips)
    limit = cfg.max_storage_gb * 1e9
    while clips and total > limit and len(clips) > 1:
        oldest = clips.pop(0)
        total -= os.path.getsize(oldest)
        try:
            os.remove(oldest)
            log.info("Storage limit: removed oldest clip %s", os.path.basename(oldest))
        except OSError:
            pass
