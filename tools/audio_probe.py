# Lists the Windows audio capture devices and whether each delivers sound in
# real time. Run from the recorder folder:  python ..\tools\audio_probe.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
from wrc_recorder import attune, config  # noqa: E402

cfg = config.Config()
ffmpeg = attune.find_ffmpeg(cfg) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "release", "ffmpeg.exe")
for dev in attune.list_audio_devices(ffmpeg):
    fraction, peak = attune.audio_flow(ffmpeg, dev)
    print("%-60s flow %3.0f%%  peak %.3f" % (dev, fraction * 100, peak))
