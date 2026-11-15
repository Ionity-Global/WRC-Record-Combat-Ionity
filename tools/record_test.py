# Records the primary monitor for a few seconds with the attuned settings and
# reports the result. Run from the recorder folder:  python ..\tools\record_test.py
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
from wrc_recorder import attune, config, winutil  # noqa: E402
from wrc_recorder.app import App  # noqa: E402

winutil.set_dpi_aware()
cfg = config.Config()
app = App(cfg)
ffmpeg = attune.find_ffmpeg(cfg) or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "release", "ffmpeg.exe")
cfg.ffmpeg_path = ffmpeg
app.prepare()
if os.environ.get("WRC_TEST_AUDIO"):
    want = os.environ["WRC_TEST_AUDIO"].lower()          # force an audio device for this test only
    app.plan.audio = next(d for d in attune.list_audio_devices(ffmpeg) if want in d.lower())
print("audio:", app.plan.audio or "none")
geom = app._primary_geometry()
app.recorder.start(geom, "Test")
time.sleep(8)
path, seconds = app.recorder.stop()
if not path:
    print("FAILED - see", os.path.join(cfg.output_dir, "ffmpeg-last.log"))
    sys.exit(1)
size = os.path.getsize(path)
print("OK %s  %dx%d  %.1fs  %.2f MB  %.1f Mbit/s" % (path, geom.width, geom.height, seconds, size / 1e6, size * 8 / seconds / 1e6))
code, _, err = winutil.run([ffmpeg, "-v", "error", "-i", path, "-f", "null", "-"], 60)
print("decode check:", "clean" if code == 0 and not err.strip() else err.strip()[-400:])
import re
code, _, err = winutil.run([ffmpeg, "-hide_banner", "-i", path, "-map", "0:v", "-c", "copy", "-f", "null", "-"], 60)
frames = re.findall(r"frame=\s*(\d+)", err)
print("video frames:", frames[-1] if frames else "?", "(60 fps x seconds recorded expected)")
print("\n".join(l.strip() for l in err.splitlines() if "Stream #" in l or "Duration" in l))
