# Shows where WRC Recorder finds the WRC addon (for the in-game clip list).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
from wrc_recorder import config, winutil
print(winutil.find_addon_dirs([config.load().wow_path]) or "none found - set wow_path in config.json")
