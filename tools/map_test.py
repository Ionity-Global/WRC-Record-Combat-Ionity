# Shows how Windows monitors map to FFmpeg capture outputs and where WoW is.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
import mss
from wrc_recorder import attune, config, winutil
from wrc_recorder.app import App
winutil.set_dpi_aware()
cfg = config.Config()
cfg.ffmpeg_path = attune.find_ffmpeg(cfg) or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "release", "ffmpeg.exe")
app = App(cfg); app.prepare()
print("WoW window:", winutil.find_wow_window())
with mss.mss() as sct:
    for m in sct.monitors[1:]:
        print(m, "-> output", app._find_output_idx(sct, m))
    class T: lock = None
    g = app._geometry(sct, T())
    print("manual recording would capture:", g, "size", g.width, g.height)
