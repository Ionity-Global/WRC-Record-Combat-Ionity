# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Clip index. Keeps a stable two-letter id for every clip and writes the list
into the addon folder (Clips.lua) so the game can show it. WoW reads that file
when the UI loads, so the in-game list refreshes on /reload."""
import json
import logging
import os
import time

log = logging.getLogger("wrc")
META = "wrc-clips.json"
MAX_LISTED = 12


def _meta_path(cfg):
    return os.path.join(cfg.output_dir, META)


def load_meta(cfg):
    try:
        with open(_meta_path(cfg), "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception:
        meta = {}
    meta.setdefault("next", 0)
    meta.setdefault("clips", {})
    meta.setdefault("addon_dirs", [])
    return meta


def save_meta(cfg, meta):
    try:
        os.makedirs(cfg.output_dir, exist_ok=True)
        with open(_meta_path(cfg), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=1)
    except OSError:
        pass


def _new_id(meta):
    n = meta["next"] % 676
    meta["next"] = n + 1
    return chr(65 + n // 26) + chr(65 + n % 26)


def clip_files(cfg):
    if not os.path.isdir(cfg.output_dir):
        return []
    files = [f for f in os.listdir(cfg.output_dir)
             if f.startswith("WRC_") and f.lower().endswith((".mp4", ".mkv"))]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(cfg.output_dir, f)), reverse=True)
    return files


def index(cfg, meta=None, seconds=None):
    """Newest-first list of clips, each with a stable id. seconds: {name: length} for new clips."""
    own = meta is None
    meta = meta or load_meta(cfg)
    files = clip_files(cfg)
    known = meta["clips"]
    for name in list(known):
        if name not in files:
            del known[name]
    out = []
    for name in files:
        entry = known.setdefault(name, {})
        if "id" not in entry:
            entry["id"] = _new_id(meta)
        if seconds and name in seconds:
            entry["secs"] = round(seconds[name], 1)
        path = os.path.join(cfg.output_dir, name)
        out.append({"id": entry["id"], "name": name, "secs": entry.get("secs", 0),
                    "mb": round(os.path.getsize(path) / 1e6, 1),
                    "when": time.strftime("%d %b %H:%M", time.localtime(os.path.getmtime(path)))})
    if own:
        save_meta(cfg, meta)
    return out


def find_by_id(cfg, clip_id):
    for name, entry in load_meta(cfg)["clips"].items():
        if entry.get("id") == clip_id:
            path = os.path.join(cfg.output_dir, name)
            return path if os.path.exists(path) else None
    return None


def _lua(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_lua(cfg, clips):
    lines = ["-- Written by WRC Recorder. Regenerated automatically; do not edit.",
             "WRC_CLIPS = {",
             "    folder = %s," % _lua(cfg.output_dir),
             "    updated = %s," % _lua(time.strftime("%d %b %Y %H:%M")),
             "    total = %d," % len(clips)]
    for c in clips[:MAX_LISTED]:
        lines.append("    { id = %s, name = %s, when = %s, secs = %s, mb = %s }," % (
            _lua(c["id"]), _lua(c["name"]), _lua(c["when"]), c["secs"], c["mb"]))
    lines.append("}")
    return "\n".join(lines) + "\n"


def publish(cfg, addon_dirs=(), seconds=None):
    """Refresh the index and write Clips.lua into every known WRC addon folder."""
    meta = load_meta(cfg)
    for d in addon_dirs:
        if d and d not in meta["addon_dirs"]:
            meta["addon_dirs"].append(d)
    clips = index(cfg, meta, seconds)
    save_meta(cfg, meta)
    text = render_lua(cfg, clips)
    for d in meta["addon_dirs"]:
        if os.path.isfile(os.path.join(d, "WRC.toc")):
            try:
                with open(os.path.join(d, "Clips.lua"), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
            except OSError as exc:
                log.debug("could not write Clips.lua in %s: %s", d, exc)
    return clips
