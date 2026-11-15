# Saves a picture of the WRC Recorder window (to check how it looks).
import ctypes, os, sys
from ctypes import wintypes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
import mss, numpy as np
from PIL import Image
from wrc_recorder import winutil
from wrc_recorder.app import to_rgb
winutil.set_dpi_aware()
u = ctypes.windll.user32
title = sys.argv[1] if len(sys.argv) > 1 else "WRC Recorder - Ionity"
hwnd = u.FindWindowW(None, title)
if not hwnd:
    sys.exit("window not found: " + title)
r = wintypes.RECT(); u.GetWindowRect(hwnd, ctypes.byref(r))
print("window", r.left, r.top, r.right - r.left, r.bottom - r.top)
with mss.MSS() if hasattr(mss, "MSS") else mss.mss() as s:
    img = to_rgb(s.grab({"left": r.left, "top": r.top, "width": r.right - r.left, "height": r.bottom - r.top}))
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_debug_window.png")
Image.fromarray(np.ascontiguousarray(img)).save(out); print(out)
