# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Small Windows helpers (ctypes only). Every function is safe to call on
other platforms, where it returns a neutral value."""
import ctypes
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0   # CREATE_NO_WINDOW for child processes


def set_dpi_aware():
    """Make screen coordinates physical pixels, whatever the Windows scaling is."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def refresh_rate():
    """Refresh rate of the primary monitor in Hz (60 when unknown)."""
    if not IS_WINDOWS:
        return 60
    try:
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        hz = gdi32.GetDeviceCaps(hdc, 116)   # VREFRESH
        user32.ReleaseDC(0, hdc)
        return hz if hz and hz > 1 else 60
    except Exception:
        return 60


def find_wow_window():
    """Client area of the WoW window as (left, top, width, height) in screen
    pixels, or None when WoW is not running or is minimised."""
    if not IS_WINDOWS:
        return None
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        title = ctypes.create_unicode_buffer(256)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value == "GxWindowClass" or title.value.startswith("World of Warcraft"):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(each, 0)
    if not found:
        return None
    rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
    user32.GetClientRect(found[0], ctypes.byref(rect))
    user32.ClientToScreen(found[0], ctypes.byref(origin))
    if rect.right <= 0 or rect.bottom <= 0:
        return None
    return origin.x, origin.y, rect.right, rect.bottom


def find_addon_dirs(extra=()):
    """Every installed copy of the WRC addon: <WoW>\\_<client>_\\Interface\\AddOns\\WRC.
    WoW's install folder comes from the registry and Battle.net's install list
    (plus any folders given in extra). The game process itself is never opened or queried."""
    import glob
    import os
    roots = [r for r in extra if r]
    if IS_WINDOWS:
        import winreg
        for key in (r"SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft",
                    r"SOFTWARE\Blizzard Entertainment\World of Warcraft"):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        roots.append(winreg.QueryValueEx(k, "InstallPath")[0])
                except OSError:
                    pass
        # Battle.net keeps its install list here; the paths are stored as plain text.
        try:
            import re
            db = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Battle.net", "Agent", "product.db")
            with open(db, "rb") as fh:
                data = fh.read()
            for m in re.findall(rb"[A-Za-z]:[\\/][^\x00-\x1f\"<>|?*]{0,200}?World of Warcraft", data):
                roots.append(m.decode("utf-8", "replace").replace("/", "\\"))
        except OSError:
            pass
    found = []
    for root in roots:
        root = root.rstrip("\\/")
        for base in (root, os.path.dirname(root)):          # InstallPath may point at one client folder
            for toc in glob.glob(os.path.join(base, "_*_", "Interface", "AddOns", "WRC", "WRC.toc")):
                d = os.path.dirname(toc)
                if d not in found:
                    found.append(d)
    return found


def run(cmd, timeout=30):
    """Run a command quietly. Returns (returncode, stdout bytes, stderr text)."""
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
        return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return -1, b"", "timed out"
    except OSError as exc:
        return -2, b"", str(exc)


# --- global quick-record key -------------------------------------------------
_MODS = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}


def parse_hotkey(text):
    """'ctrl+alt+r' or 'f9' -> (modifier flags, virtual key code), or None if not understood."""
    mods, vk = 0, None
    for part in [p.strip().lower() for p in (text or "").split("+") if p.strip()]:
        if part in _MODS:
            mods |= _MODS[part]
        elif len(part) == 1 and (part.isalpha() or part.isdigit()):
            vk = ord(part.upper())
        elif part[0] == "f" and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            vk = 0x70 + int(part[1:]) - 1
        else:
            return None
    return (mods, vk) if vk else None


def start_hotkey(text, callback):
    """Register a system-wide hotkey and call callback() on each press.
    Returns True when it is registered. The key is handled by the recorder
    only; nothing is ever sent to the game."""
    parsed = parse_hotkey(text)
    if not IS_WINDOWS or not parsed:
        return False
    import threading
    from ctypes import wintypes
    mods, vk = parsed
    ready, ok = threading.Event(), []

    def pump():
        user32 = ctypes.windll.user32
        ok.append(bool(user32.RegisterHotKey(None, 1, mods | 0x4000, vk)))    # 0x4000 = no auto-repeat
        ready.set()
        if not ok[0]:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:                                         # WM_HOTKEY
                try:
                    callback()
                except Exception:
                    pass

    threading.Thread(target=pump, daemon=True).start()
    ready.wait(3)
    return bool(ok and ok[0])


# --- showing a window over the game ---------------------------------------------
def raise_window(title_part, timeout=4.0, classes=None):
    """Find a visible top-level window whose title contains title_part and put it
    on top of everything, centred on the monitor WoW is on, without activating it.
    Windows will not let a background program take focus from a game, and WRC
    never fakes input to force it; raising the window is the honest alternative.
    Returns True when a window was raised."""
    if not IS_WINDOWS:
        return False
    import time
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    want = title_part.lower()
    deadline = time.time() + timeout
    while True:
        hits = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def each(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            title = ctypes.create_unicode_buffer(512)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 512)
            user32.GetClassNameW(hwnd, cls, 256)
            if cls.value == "GxWindowClass" or (classes and cls.value not in classes):
                return True
            if want in title.value.lower():
                hits.append(hwnd)
            return True

        user32.EnumWindows(each, 0)
        if hits:
            break
        if time.time() >= deadline:
            return False
        time.sleep(0.25)

    hwnd = hits[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 4)                      # SW_SHOWNOACTIVATE: un-minimise
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    game = find_wow_window()
    flags = 0x0001 | 0x0010 | 0x0040                    # SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    if game:
        gx, gy, gw, gh = game
        x, y = gx + max(0, (gw - w) // 2), gy + max(0, (gh - h) // 2)
    else:
        x, y, flags = 0, 0, flags | 0x0002              # SWP_NOMOVE: leave it where it is
    set_pos = user32.SetWindowPos
    set_pos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                        ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    set_pos.restype = wintypes.BOOL
    ok = set_pos(hwnd, wintypes.HWND(-1), x, y, 0, 0, flags)               # HWND_TOPMOST: above the game
    set_pos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_NOTOPMOST: in front, not pinned
    return bool(ok)
