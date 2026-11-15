# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
# (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | https://www.ionity.today
"""WRC Recorder: watches the screen for the WRC addon beacon and records WoW
while an opposite-faction player is around. It only reads screen pixels; it
never touches the game process, its memory or its files."""
import argparse
import logging
import os
import sys
import threading
import time

import numpy as np

from . import __version__, attune, beacon, clips, config, winutil
from . import recorder
from .recorder import Geometry, Recorder, build_command, enforce_storage
from .trigger import SPLIT, START, STOP, Trigger, wanted

log = logging.getLogger("wrc")
RESCAN_SECONDS = 1.5        # how often to search whole screens while the beacon is not locked
STALE_SECONDS = 5.0         # a beacon whose heartbeat stops is a frozen picture, not a live game


def to_rgb(shot):
    """mss screenshot (BGRA bytes) -> HxWx3 RGB array."""
    return np.frombuffer(shot.raw, dtype=np.uint8).reshape(shot.height, shot.width, 4)[..., 2::-1]


class BeaconTracker:
    """Finds the beacon on any monitor, then follows it by grabbing only its own
    small rectangle, so watching costs almost nothing."""

    def __init__(self, sct):
        self.sct = sct
        self.lock = None            # (monitor dict, region dict) once found
        self._misses = 0
        self._next_scan = 0.0
        self._beat = None
        self._beat_changed = 0.0

    def read(self, now):
        found = self._read_locked() if self.lock else None
        if found is None and not self.lock and now >= self._next_scan:
            self._next_scan = now + RESCAN_SECONDS
            found = self._scan_all()
            if found is not None:
                self._beat, self._beat_changed = found.heartbeat, now
        if found is None:
            return None
        if found.heartbeat != self._beat:
            self._beat, self._beat_changed = found.heartbeat, now
        if now - self._beat_changed > STALE_SECONDS:
            return None
        return found

    def _read_locked(self):
        mon, region = self.lock
        try:
            found = beacon.locate(to_rgb(self.sct.grab(region)))
        except Exception:
            found = None
        if found is None:
            self._misses += 1
            if self._misses >= 3:
                self.lock = None
            return None
        self._misses = 0
        self._set_lock(mon, region["left"] + found.x, region["top"] + found.y, found)
        return found

    def _scan_all(self):
        for mon in self.sct.monitors[1:]:
            try:
                found = beacon.locate(to_rgb(self.sct.grab(mon)))
            except Exception:
                continue
            if found is not None:
                self._misses = 0
                self._set_lock(mon, mon["left"] + found.x, mon["top"] + found.y, found)
                log.info("Beacon locked on monitor %dx%d at (%d, %d), cell %.1f px",
                         mon["width"], mon["height"], self.abs_x - mon["left"],
                         self.abs_y - mon["top"], found.cell_w)
                return found
        return None

    def _set_lock(self, mon, abs_x, abs_y, found):
        self.abs_x, self.abs_y = abs_x, abs_y
        pad = int(found.cell_w * 3) + 2
        left = max(mon["left"], int(abs_x) - pad)
        top = max(mon["top"], int(abs_y) - pad)
        right = min(mon["left"] + mon["width"], int(abs_x + found.width) + pad)
        bottom = min(mon["top"] + mon["height"], int(abs_y + found.height) + pad)
        self.lock = (mon, {"left": left, "top": top, "width": right - left, "height": bottom - top})


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.plan = None
        self.recorder = None
        self.stop_event = threading.Event()
        self.manual = False         # Record button in the window
        self.beacon_seen = False
        self.detail = ""
        self.hotkey = ""            # shown in the window once registered
        self.status = "starting"
        self._output_idx = {}
        self._fps = 60

    # --- attune ----------------------------------------------------------
    def prepare(self, force=False):
        ffmpeg = attune.find_ffmpeg(self.cfg) or attune.download_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required. Put ffmpeg.exe next to WRC-Recorder.exe.")
        hz = winutil.refresh_rate()
        self._fps = self.cfg.fps if self.cfg.fps > 0 else max(24, min(60, hz))
        plan = None if force else attune.load_cached(self.cfg, ffmpeg)
        if plan is None:
            log.info("Auto-attuning to this PC (first run only, takes a few seconds) ...")
            test = self._capture_test if winutil.IS_WINDOWS else None
            plan = attune.attune(self.cfg, ffmpeg, test)
            plan.audio = attune.pick_audio(self.cfg, ffmpeg)
            if plan.audio and winutil.IS_WINDOWS and not self._capture_test(plan):
                log.warning("Audio device %r failed its test; recording video only.", plan.audio)
                plan.audio = ""
            attune.save_cached(self.cfg, plan)
        self.plan = plan
        self.recorder = Recorder(plan, self.cfg)
        log.info("Attuned: %s via %s, %d fps, audio: %s", plan.encoder, plan.capture, self._fps,
                 plan.audio or "none (no loopback device found)")
        self.detail = "%s, %d fps, audio: %s" % (plan.encoder, self._fps, plan.audio or "none")

    def _primary_geometry(self):
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors[1:]
            mon = next((m for m in monitors if m.get("is_primary")), monitors[0])
        return Geometry(mon["left"], mon["top"], mon["width"], mon["height"], 0, fps=self._fps)

    def _capture_test(self, plan):
        cmd = build_command(plan, self.cfg, self._primary_geometry(), None, duration=1)
        code, _, err = winutil.run(cmd, timeout=25)
        if code != 0:
            log.debug("capture test failed (%s): %s", plan.capture, err.strip()[-300:])
        return code == 0

    # --- geometry --------------------------------------------------------
    def _find_output_idx(self, sct, mon):
        """Which DXGI output (FFmpeg's numbering) is this monitor? Windows and DXGI
        number screens independently, so each output is grabbed once through FFmpeg
        and matched to the monitor by size, then by what is on it."""
        key = (mon["left"], mon["top"], mon["width"], mon["height"])
        if key in self._output_idx:
            return self._output_idx[key]
        monitors = sct.monitors[1:]
        idx = monitors.index(mon) if mon in monitors else 0
        if len(monitors) > 1 and self.plan.capture != "gdi":
            scores = {}
            for cand in range(len(monitors)):
                cmd = [self.plan.ffmpeg, "-hide_banner", "-loglevel", "error", "-filter_complex",
                       "ddagrab=output_idx=%d,hwdownload,format=bgra" % cand, "-frames:v", "1",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
                code, raw, _ = winutil.run(cmd, timeout=10)
                if code != 0 or len(raw) != mon["width"] * mon["height"] * 3:
                    continue                                   # different size: not this monitor
                theirs = np.frombuffer(raw, dtype=np.uint8).reshape(mon["height"], mon["width"], 3)
                ours = to_rgb(sct.grab(mon))
                scores[cand] = float(np.abs(theirs[::8, ::8].astype(np.int16)
                                            - ours[::8, ::8].astype(np.int16)).mean())
            if scores:
                idx = min(scores, key=scores.get)
            log.info("Monitor %dx%d is capture output %d", mon["width"], mon["height"], idx)
        self._output_idx[key] = idx
        return idx

    def _geometry(self, sct, tracker):
        win = winutil.find_wow_window()
        monitors = sct.monitors[1:]
        if tracker.lock:
            mon = tracker.lock[0]
            idx = self._find_output_idx(sct, mon)
        else:
            # Manual recording with no beacon on screen: the monitor showing WoW, else the primary.
            mon = monitors[0]
            if win:
                cx, cy = win[0] + win[2] // 2, win[1] + win[3] // 2
                for m in monitors:
                    if m["left"] <= cx < m["left"] + m["width"] and m["top"] <= cy < m["top"] + m["height"]:
                        mon = m
                        break
            idx = self._find_output_idx(sct, mon)
        geom = Geometry(mon["left"], mon["top"], mon["width"], mon["height"], idx, fps=self._fps)
        if win:
            x, y, w, h = win
            x0, y0 = max(x, mon["left"]), max(y, mon["top"])
            x1 = min(x + w, mon["left"] + mon["width"])
            y1 = min(y + h, mon["top"] + mon["height"])
            if x1 - x0 >= 320 and y1 - y0 >= 240:      # windowed WoW: record just the window
                geom.crop_x, geom.crop_y = x0 - mon["left"], y0 - mon["top"]
                geom.crop_w, geom.crop_h = x1 - x0, y1 - y0
        return geom

    # --- main loop -------------------------------------------------------
    def run(self):
        import mss
        cfg = self.cfg
        trig = Trigger(cfg.start_confirm, cfg.linger_seconds, cfg.max_clip_minutes * 60)
        interval = 1.0 / max(1.0, cfg.scan_hz)
        rec = self.recorder
        was_manual, folder_shown, play_shown, was_dead = False, False, None, False
        next_addon_check, addon_dirs = 0.0, set()
        character = ""              # last character name read off the beacon
        # What is being recorded: None, "real" (a clip that will be kept) or "standby"
        # (the death cam: every fight is recorded, and kept only if you die in it).
        st = {"kind": None, "label": "", "manual": False, "death_at": None, "died": False, "calm": None}
        clips.publish(cfg)
        self.status = "watching"
        log.info("Watching for the WRC beacon. Clips go to %s", cfg.output_dir)

        def begin(sct, tracker, label, kind):
            rec.start(self._geometry(sct, tracker), label, character)
            st.update(kind=kind, label=label, manual=(label == "Manual"), death_at=None, died=False, calm=None)
            self.status = "recording" if kind == "real" else "standby"

        def finish(discard=False, label=None, trim=None):
            label = label or st["label"]
            path, secs = rec.stop(keep_short=st["manual"] or label.endswith("Death"), discard=discard,
                                  final_label=label)
            if path and trim and recorder.trim_tail(self.plan.ffmpeg, path, trim):
                secs = min(secs, trim)
            if path:
                self.detail = "Last clip: %s  (%.1f MB)" % (os.path.basename(path), os.path.getsize(path) / 1e6)
                clips.publish(cfg, addon_dirs, {os.path.basename(path): secs})
            enforce_storage(cfg)
            st.update(kind=None, death_at=None, died=False, calm=None)
            self.status = "watching"

        with mss.mss() as sct:
            tracker = BeaconTracker(sct)
            while not self.stop_event.is_set():
                now = time.time()
                found = tracker.read(now)
                self.beacon_seen = found is not None
                trusted = found is not None and found.trusted
                if found is not None and found.name:
                    character = found.name.title()
                afk = bool(trusted and cfg.afk_record and found.afk)
                auto = wanted(found, cfg.trigger_mode) or afk
                is_manual = self.manual or bool(trusted and found.manual)
                combat = bool(trusted and (found.combat or found.pvp_combat))
                dead = bool(found is not None and found.dead)
                died, was_dead = dead and not was_dead, dead

                trig.linger = float(cfg.linger_seconds)       # settings apply live
                action = trig.update(auto or self.manual, now)
                if was_manual and not is_manual and not auto:
                    action = trig.force_stop() or action      # Stop pressed: end now, no linger
                was_manual = is_manual

                if found is not None and found.folder and not folder_shown:
                    open_folder(cfg)                          # in-game Folder button
                folder_shown = bool(found is not None and found.folder)
                play_id = found.play_id if found is not None else None
                if play_id and play_id != play_shown:
                    play_clip(cfg, play_id)                   # in-game Play button
                play_shown = play_id

                if now >= next_addon_check:                   # learn where the addon lives
                    next_addon_check = now + 60
                    for d in winutil.find_addon_dirs([cfg.wow_path]):
                        if d not in addon_dirs:
                            addon_dirs.add(d)
                            clips.publish(cfg, addon_dirs)
                            log.info("In-game clip list goes to %s", d)

                if rec.proc is not None and not rec.active:
                    log.warning("The encoder stopped by itself. See ffmpeg-last.log in the clips folder.")
                    rec.stop()
                    trig.reset()
                    st.update(kind=None, death_at=None, died=False, calm=None)
                    self.status = "watching"
                    action = None

                # --- clips that are kept: enemy, AFK attack, manual -----------
                if action == START:
                    enemy_here = bool(trusted and (found.enemy or found.pvp_combat))
                    label = (found.enemy_faction if enemy_here else
                             "Manual" if is_manual else "AFK" if afk else "Enemy")
                    if st["kind"] == "standby":               # already rolling: keep that footage
                        st.update(kind="real", label=label, manual=(label == "Manual"))
                        self.status = "recording"
                        log.info("REC  keeping the standby recording as %s", label)
                    else:
                        try:
                            begin(sct, tracker, label, "real")
                        except Exception as exc:
                            log.error("Could not start recording: %s", exc)
                            trig.reset()
                elif action in (STOP, SPLIT) and st["kind"] == "real":
                    label = st["label"]
                    finish(label=label + "Death" if st["died"] else label)
                    if action == SPLIT:
                        begin(sct, tracker, label, "real")
                if st["kind"] == "real" and died:
                    st["died"] = True

                # --- death cam: record fights on standby, keep only a death ----
                if cfg.deathcam:
                    if st["kind"] is None and combat and not dead and not trig.recording:
                        try:
                            begin(sct, tracker, "Combat", "standby")
                        except Exception as exc:
                            log.error("Could not start the standby recording: %s", exc)
                    elif st["kind"] == "standby":
                        if died and st["death_at"] is None:
                            st["death_at"] = now
                            log.info("Death seen: keeping the last %.0f s", cfg.deathcam_seconds)
                        if st["death_at"] is not None:
                            if now - st["death_at"] >= cfg.deathcam_after:
                                finish(label="Death", trim=cfg.deathcam_seconds + cfg.deathcam_after)
                        elif not combat:
                            st["calm"] = st["calm"] or now
                            if now - st["calm"] >= 3:         # fight over, nobody died
                                finish(discard=True)
                        else:
                            st["calm"] = None
                            if now - rec.started >= 300:      # long fight: start a fresh file
                                finish(discard=True)
                self.stop_event.wait(interval)
        if rec.proc is not None:
            if st["kind"] == "standby":
                rec.stop(discard=True)
            else:
                finish(label=st["label"] + "Death" if st["died"] else None)
        self.status = "stopped"


# --- command line ---------------------------------------------------------
def selftest():
    """Draw beacons the way the addon does and check the reader gets them right."""
    rng = np.random.default_rng(986)
    ok = 0
    cases = [("ALLIANCE", dict(enemy=True, pvp=True, combat=True)),
             ("HORDE", dict(enemy=True, horde=True, beat=True)),
             ("IDLE", dict()), ("COMBAT", dict(combat=True)), ("REC", dict(manual=True))]
    for cell in (2, 3, 4, 6):
        for word, flags in cases:
            screen = rng.integers(0, 256, size=(400, 900, 3), dtype=np.uint8)
            img = beacon.render(beacon.make_bits(**flags), word, cell)
            screen[40:40 + img.shape[0], 70:70 + img.shape[1]] = img
            hit = beacon.locate(screen)
            good = bool(hit and hit.checksum_ok and hit.word == word
                        and hit.enemy == flags.get("enemy", False))
            ok += good
            print("cell %d  %-8s -> %s" % (cell, word, "ok" if good else "FAILED (%r)" % (hit,)))
    total = 4 * len(cases)
    print("%d / %d beacon readings correct" % (ok, total))
    return 0 if ok == total else 1


def snapshot(cfg):
    """Save what WRC sees and say what it read. For troubleshooting."""
    import mss
    from PIL import Image
    with mss.mss() as sct:
        for i, mon in enumerate(sct.monitors[1:], 1):
            img = np.ascontiguousarray(to_rgb(sct.grab(mon)))
            hit = beacon.locate(img)
            path = os.path.join(config.app_dir(), "wrc-snapshot-%d.png" % i)
            Image.fromarray(img).save(path)
            print("monitor %d: %s  (saved %s)" % (i, hit if hit else "no beacon found", path))
    return 0


def open_folder(cfg):
    os.makedirs(cfg.output_dir, exist_ok=True)
    log.info("Opening the clips folder: %s", cfg.output_dir)
    try:
        os.startfile(cfg.output_dir)
    except AttributeError:          # not Windows
        return
    title = os.path.basename(cfg.output_dir.rstrip("\\/"))
    threading.Thread(target=lambda: log.info("Folder window %s", "brought in front of the game"
                     if winutil.raise_window(title, classes=("CabinetWClass", "ExploreWClass"))
                     else "opened, but WRC could not find it to bring it forward"), daemon=True).start()


def play_clip(cfg, clip_id):
    path = clips.find_by_id(cfg, clip_id)
    if not path:
        log.info("Play %s: that clip is no longer in the folder", clip_id)
        return
    log.info("Playing %s", os.path.basename(path))
    try:
        os.startfile(path)
    except AttributeError:          # not Windows
        return
    stem = os.path.splitext(os.path.basename(path))[0]      # most players put the file name in the title
    threading.Thread(target=lambda: log.info("Player window %s", "brought in front of the game"
                     if winutil.raise_window(stem, timeout=6) else
                     "opened; WRC could not find it to bring it forward (look on another monitor)"),
                     daemon=True).start()


TRIGGER_CHOICES = [("enemy", "Opposite faction on screen or fighting you"),
                   ("pvp_combat", "Only when in combat with them"),
                   ("any_combat", "Every fight")]


def window(app, auto_close=None):
    """The recorder window: status, Record/Stop, Open folder and Settings.
    Shapes are drawn anti-aliased with Pillow so every edge is smooth.
    Returns False when no window can be shown (then the console loop is used)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        from PIL import Image, ImageDraw, ImageTk
    except Exception:
        return False
    dark, panel, blue, red, text, muted = "#0d1b2a", "#152b41", "#00c6ff", "#e6283c", "#e8f4f8", "#8fa8b8"
    res = getattr(sys, "_MEIPASS", config.app_dir())
    cfg = app.cfg
    root = tk.Tk()
    root.title("WRC Recorder - Ionity")
    root.configure(bg=dark)
    root.resizable(False, False)
    try:
        root.iconbitmap(os.path.join(res, "wrc.ico"))
    except Exception:
        pass
    keep = []                                                   # Tk images must stay referenced

    def shape(w, h, radius, fill):
        """Anti-aliased rounded rectangle as a Tk image (drawn 4x and scaled down)."""
        big = Image.new("RGBA", (w * 4, h * 4), (0, 0, 0, 0))
        ImageDraw.Draw(big).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=radius * 4, fill=fill)
        img = ImageTk.PhotoImage(big.resize((w, h), Image.LANCZOS))
        keep.append(img)
        return img

    def lighter(hex_colour, amount=0.18):
        r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(int(c + (255 - c) * amount) for c in (r, g, b))

    def button(parent, label, width, fill, fg, command, bg=dark):
        normal, hover = shape(width, 38, 19, fill), shape(width, 38, 19, lighter(fill))
        b = tk.Label(parent, image=normal, text=label, compound="center", fg=fg, bg=bg,
                     font=("Segoe UI", 10, "bold"), cursor="hand2", bd=0)
        b.images = [normal, hover]
        b.bind("<Enter>", lambda e: b.config(image=b.images[1]))
        b.bind("<Leave>", lambda e: b.config(image=b.images[0]))
        b.bind("<Button-1>", lambda e: command())
        return b

    # --- header ---------------------------------------------------------
    tk.Frame(root, bg=blue, height=3).pack(fill="x")                 # Ionity accent line
    head = tk.Frame(root, bg=dark)
    head.pack(fill="x", padx=18, pady=(14, 0))
    try:
        logo = tk.PhotoImage(file=os.path.join(res, "ionity_logo.png"))
        keep.append(logo)
        tk.Label(head, image=logo, bg=dark).pack(side="left")
    except Exception:
        tk.Label(head, text="IONITY", bg=dark, fg=text, font=("Segoe UI", 14, "bold")).pack(side="left")
    title = tk.Frame(head, bg=dark)
    title.pack(side="right")
    tk.Label(title, text="WRC Recorder", bg=dark, fg=blue, font=("Segoe UI", 13, "bold")).pack(anchor="e")
    tk.Label(title, text="WoW Record Combat", bg=dark, fg=muted, font=("Segoe UI", 9)).pack(anchor="e")

    # --- status card ----------------------------------------------------
    cw, ch = 400, 84
    card = tk.Canvas(root, width=cw, height=ch, bg=dark, highlightthickness=0)
    card.pack(padx=18, pady=(12, 12))
    card.create_image(0, 0, anchor="nw", image=shape(cw, ch, 16, panel))
    dot = card.create_oval(22, 24, 36, 38, fill=blue, outline="")
    status = card.create_text(48, 31, anchor="w", text="starting", fill=text, font=("Segoe UI", 13, "bold"))
    detail = card.create_text(22, 60, anchor="w", text="", fill=muted, font=("Segoe UI", 9))

    # --- buttons --------------------------------------------------------
    row = tk.Frame(root, bg=dark)
    row.pack(padx=18, pady=(0, 10))

    def toggle():
        app.manual = not app.manual

    rec = button(row, "Record", 126, red, "white", toggle)
    rec.pack(side="left", padx=(0, 10))
    stop_images = [shape(126, 38, 19, "#3a4a5c"), shape(126, 38, 19, lighter("#3a4a5c"))]
    rec_images = rec.images
    button(row, "Open folder", 126, blue, dark, lambda: open_folder(cfg)).pack(side="left", padx=(0, 10))

    # --- settings window ------------------------------------------------
    def settings():
        win = tk.Toplevel(root)
        win.title("WRC Settings")
        win.configure(bg=dark)
        win.resizable(False, False)
        try:
            win.iconbitmap(os.path.join(res, "wrc.ico"))
        except Exception:
            pass
        tk.Frame(win, bg=blue, height=3).grid(row=0, column=0, columnspan=3, sticky="ew")

        def label(r, caption):
            tk.Label(win, text=caption, bg=dark, fg=text, font=("Segoe UI", 10), anchor="w").grid(
                row=r, column=0, sticky="w", padx=(18, 10), pady=6)

        def entry(r, value, width=30):
            var = tk.StringVar(value=str(value))
            tk.Entry(win, textvariable=var, width=width, bg=panel, fg=text, insertbackground=text,
                     relief="flat", font=("Segoe UI", 10)).grid(row=r, column=1, sticky="w", pady=6, ipady=4)
            return var

        label(1, "Record when")
        names = dict(TRIGGER_CHOICES)
        trig_var = tk.StringVar(value=names.get(cfg.trigger_mode, names["enemy"]))
        menu = tk.OptionMenu(win, trig_var, *[n for _, n in TRIGGER_CHOICES])
        menu.config(bg=panel, fg=text, activebackground=lighter(panel), activeforeground=text,
                    relief="flat", highlightthickness=0, font=("Segoe UI", 10), width=36, anchor="w")
        menu["menu"].config(bg=panel, fg=text)
        menu.grid(row=1, column=1, columnspan=2, sticky="w", pady=6, padx=(0, 18))

        label(2, "Keep recording after they are gone (seconds)")
        linger = entry(2, cfg.linger_seconds, 8)
        label(3, "Quick record key")
        hot = entry(3, cfg.hotkey, 18)
        tk.Label(win, text="e.g. ctrl+alt+r, f9, shift+f10", bg=dark, fg=muted,
                 font=("Segoe UI", 9)).grid(row=3, column=2, sticky="w", padx=(8, 18))
        label(4, "Clips folder")
        folder = entry(4, cfg.output_dir, 38)

        def browse():
            picked = filedialog.askdirectory(parent=win, initialdir=folder.get() or None)
            if picked:
                folder.set(os.path.normpath(picked))
        button(win, "Browse", 84, panel, text, browse).grid(row=4, column=2, sticky="w", padx=(8, 18))
        label(5, "Delete oldest clips beyond (GB, 0 = never)")
        storage = entry(5, cfg.max_storage_gb, 8)
        label(6, "Quality (0 = auto, lower = sharper and bigger)")
        quality = entry(6, cfg.quality, 8)
        def check(r, caption, value):
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(win, text=caption, variable=var, bg=dark, fg=text, selectcolor=panel,
                           activebackground=dark, activeforeground=text, font=("Segoe UI", 10),
                           anchor="w").grid(row=r, column=0, columnspan=3, sticky="w", padx=14, pady=2)
            return var
        deathcam = check(7, "Death cam: record every fight on standby, keep the last %d s if you die"
                         % cfg.deathcam_seconds, cfg.deathcam)
        afk_rec = check(8, "Keep the clip when you are attacked while AFK", cfg.afk_record)
        note = tk.Label(win, text="", bg=dark, fg=muted, font=("Segoe UI", 9))
        note.grid(row=9, column=0, columnspan=3, sticky="w", padx=18)

        def save():
            try:
                new_linger, new_storage, new_quality = float(linger.get()), float(storage.get()), int(float(quality.get()))
            except ValueError:
                note.config(text="Seconds, GB and quality must be numbers.", fg=red)
                return
            new_hot = hot.get().strip().lower()
            if new_hot and not winutil.parse_hotkey(new_hot):
                note.config(text="That key is not understood. Use a form like ctrl+alt+r or f9.", fg=red)
                return
            cfg.trigger_mode = next(k for k, n in TRIGGER_CHOICES if n == trig_var.get())
            cfg.linger_seconds, cfg.max_storage_gb, cfg.quality = max(0.0, new_linger), max(0.0, new_storage), max(0, new_quality)
            cfg.output_dir = folder.get().strip() or cfg.output_dir
            cfg.deathcam, cfg.afk_record = bool(deathcam.get()), bool(afk_rec.get())
            key_changed = new_hot != cfg.hotkey
            cfg.hotkey = new_hot
            config.save(cfg)
            log.info("Settings saved")
            if key_changed:
                note.config(text="Saved. The new quick record key works after you restart WRC Recorder.", fg=text)
            else:
                win.destroy()

        button(win, "Save", 110, blue, dark, save).grid(row=10, column=1, sticky="w", pady=(8, 16))
        win.transient(root)

    button(row, "Settings", 126, panel, text, settings).pack(side="left")

    key = tk.Label(root, text="", bg=dark, fg=text, font=("Segoe UI", 9))
    key.pack(pady=(0, 6))
    tk.Label(root, text="Ionity (Pty) Ltd  -  www.ionity.today  -  Building Tomorrow, Today.",
             bg=dark, fg=muted, font=("Segoe UI", 8)).pack(padx=18, pady=(0, 12))

    worker = threading.Thread(target=app.run, daemon=True)
    worker.start()

    def refresh():
        key.config(text=("Quick record key:  %s" % app.hotkey) if app.hotkey else "")
        if app.status == "recording":
            secs = int(time.time() - app.recorder.started)
            card.itemconfig(status, text="RECORDING  %d:%02d" % divmod(secs, 60), fill=red)
            card.itemconfig(dot, fill=red if int(time.time() * 2) % 2 else "#7a1420")     # pulse
        elif app.status == "standby":
            card.itemconfig(status, text="Standby  -  death cam rolling", fill=text)
            card.itemconfig(dot, fill="#f5a623")
        elif app.status == "watching":
            card.itemconfig(status, fill=text, text="Watching  -  " + (
                "WoW found" if app.beacon_seen else "waiting for WoW"))
            card.itemconfig(dot, fill=blue if app.beacon_seen else muted)
        else:
            card.itemconfig(status, text=app.status, fill=text)
        card.itemconfig(detail, text=app.detail)
        want = stop_images if app.manual else rec_images
        if rec.images is not want:
            rec.images = want
            rec.config(image=want[0], text="Stop" if app.manual else "Record")
        if not worker.is_alive():
            root.destroy()
            return
        root.after(300, refresh)

    def close():
        card.itemconfig(status, text="closing ...")
        app.stop_event.set()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, refresh)
    if auto_close:
        root.after(int(auto_close * 1000), close)
    root.mainloop()
    app.stop_event.set()
    worker.join(timeout=25)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="WRC-Recorder", description="WRC - WoW Record Combat recorder (Ionity)")
    ap.add_argument("--selftest", action="store_true", help="check the beacon reader and exit")
    ap.add_argument("--attune", action="store_true", help="re-run the hardware auto-attune")
    ap.add_argument("--snapshot", action="store_true", help="save what WRC sees and what it read")
    ap.add_argument("--write-config", action="store_true", help="write config.json with all defaults")
    ap.add_argument("--no-gui", action="store_true", help="run without the window")
    ap.add_argument("--gui-test", action="store_true", help="open the window for 6 seconds and exit")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    winutil.set_dpi_aware()
    if sys.stdout is None:                      # built as a windowed app: no console attached
        sys.stdout = open(os.devnull, "w")
        handlers = []
    else:
        handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(os.path.join(config.app_dir(), "wrc.log"), encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s  %(message)s", datefmt="%H:%M:%S", handlers=handlers)

    if args.selftest:
        return selftest()
    cfg = config.load()
    if args.write_config:
        print("wrote", config.save(cfg))
        return 0
    if args.snapshot:
        return snapshot(cfg)

    log.info("WRC Recorder %s - Ionity (Pty) Ltd - Building Tomorrow, Today.", __version__)
    app = App(cfg)
    try:
        app.prepare(force=args.attune)
    except Exception as exc:
        log.error("%s", exc)
        return 1
    if args.attune:
        return 0

    def toggle_manual():
        app.manual = not app.manual
        log.info("Quick record key: %s", "start" if app.manual else "stop")

    if cfg.hotkey:
        if winutil.start_hotkey(cfg.hotkey, toggle_manual):
            app.hotkey = cfg.hotkey.upper().replace("+", " + ")
            log.info("Quick record key registered: %s", app.hotkey)
        else:
            log.warning("Quick record key %r could not be registered (in use by another program, "
                        "or not understood). Change \"hotkey\" in config.json.", cfg.hotkey)
    try:
        if args.no_gui or not window(app, auto_close=6 if args.gui_test else None):
            app.run()
    except KeyboardInterrupt:
        app.stop_event.set()
        if app.recorder and app.recorder.proc is not None:
            app.recorder.stop()
    return 0
