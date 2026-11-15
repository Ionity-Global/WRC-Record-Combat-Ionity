# Looks at every monitor a few times and says what the WRC beacon shows.
# Run from the recorder folder:  python ..\tools\beacon_check.py
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recorder"))
import mss
from wrc_recorder import beacon, winutil
from wrc_recorder.app import to_rgb
winutil.set_dpi_aware()
print("WoW window:", winutil.find_wow_window())
with mss.MSS() if hasattr(mss, "MSS") else mss.mss() as sct:
    for n in range(4):
        for i, mon in enumerate(sct.monitors[1:], 1):
            hit = beacon.locate(to_rgb(sct.grab(mon)))
            if hit:
                print("read %d: monitor %d %dx%d  word=%-8s checksum=%s cell=%.2f at (%d,%d) beat=%s"
                      % (n, i, mon["width"], mon["height"], hit.word, hit.checksum_ok, hit.cell_w, hit.x, hit.y, hit.heartbeat))
                break
        else:
            print("read %d: no beacon on any monitor" % n)
        time.sleep(0.7)
