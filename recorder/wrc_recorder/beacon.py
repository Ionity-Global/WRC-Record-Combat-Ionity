# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Find and read the WRC addon beacon in a screen image.

The beacon layout is documented in addon/WRC/Beacon.lua. Finding it is
self-calibrating: the finder bars give position and cell size, so the reader
works at any resolution, beacon size or screen corner without configuration.
"""
from dataclasses import dataclass, field

import numpy as np

from .font import GLYPH_H, GLYPH_W, match_glyph

COLS, ROWS = 66, 9            # the main strip
NAME_COLS = 130               # strip plus the character name to its right (addon 1.4+)
STATE_COL, TEXT_COL, CHARS = 5, 14, 8
NAME_MARK_COL, NAME_COL, NAME_CHARS = 66, 70, 10
RIGHT_MAGENTA_COL = 63
MIN_BAR_HEIGHT = 12          # 7 cells tall, so cells under ~1.7 px are not readable
LUMA_ON = 110                # a cell brighter than this is "white"
MAX_GLYPH_ERRORS = 3
MAX_CANDIDATES = 4000


@dataclass
class Beacon:
    x: float                 # top-left of the whole beacon (quiet zone included), image pixels
    y: float
    cell_w: float
    cell_h: float
    bits: list = field(default_factory=list)   # 8 booleans
    word: str = ""
    checksum_ok: bool = False
    word_ok: bool = False
    name: str = ""           # character name from the right-hand field, "" when absent or unreadable
    cols: int = COLS

    @property
    def width(self):
        return self.cols * self.cell_w

    @property
    def height(self):
        return ROWS * self.cell_h

    # --- decoded meaning -------------------------------------------------
    @property
    def trusted(self):
        return self.checksum_ok or (self.word_ok and self.word in WORDS)

    @property
    def enemy(self):
        if self.checksum_ok:
            return self.bits[0]
        return self.word in ("ALLIANCE", "HORDE", "ENEMY")

    @property
    def pvp_combat(self):
        return self.checksum_ok and self.bits[1]

    @property
    def combat(self):
        if self.checksum_ok:
            return self.bits[2]
        return self.word == "COMBAT"

    @property
    def manual(self):
        if self.checksum_ok:
            return self.bits[3]
        return self.word == "REC"

    @property
    def folder(self):
        """The in-game Folder button was pressed: open the clips folder."""
        return self.word_ok and self.word == "FOLDER"

    @property
    def dead(self):
        """Your character is dead (or a ghost)."""
        return self.word_ok and self.word == "DEAD"

    @property
    def afk(self):
        """You are flagged AFK and something is attacking you."""
        return self.word_ok and self.word == "AFK"

    @property
    def play_id(self):
        """Two-letter id of the clip the in-game Play button asked for, or None."""
        if self.word_ok and len(self.word) == 7 and self.word.startswith("PLAY ") and self.word[5:].isalpha():
            return self.word[5:]
        return None

    @property
    def heartbeat(self):
        return bool(self.bits[5]) if self.bits else False

    @property
    def enemy_faction(self):
        if self.word in ("ALLIANCE", "HORDE"):
            return self.word.title()
        if self.checksum_ok:
            return "Horde" if self.bits[4] else "Alliance"
        return "Enemy"


WORDS = ("ALLIANCE", "HORDE", "ENEMY", "COMBAT", "IDLE", "REC", "FOLDER", "DEAD", "AFK")


def _masks(img):
    r = img[..., 0].astype(np.int16)
    g = img[..., 1].astype(np.int16)
    b = img[..., 2].astype(np.int16)
    magenta = (r > 140) & (b > 140) & (g < 110) & (r - g > 70) & (b - g > 70)
    cyan = (g > 140) & (b > 140) & (r < 110) & (g - r > 70) & (b - r > 70)
    return magenta, cyan


def _run(line):
    """Length of the run of True values at the start of a 1-D boolean array."""
    if line.size == 0 or not line[0]:
        return 0
    stop = np.flatnonzero(~line)
    return int(stop[0]) if stop.size else int(line.size)


def _patch(arr, cx, cy, cw, ch):
    """Mean of a small patch centred on (cx, cy); None when off the image."""
    h, w = arr.shape[:2]
    rx, ry = max(0, int(cw * 0.2)), max(0, int(ch * 0.2))
    x0, x1 = int(cx) - rx, int(cx) + rx + 1
    y0, y1 = int(cy) - ry, int(cy) + ry + 1
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return None
    return arr[y0:y1, x0:x1].mean()


def _try_candidate(img, magenta, cyan, luma, edge, x, y):
    """(x, y) is the top of a magenta-then-cyan edge: the right-hand column of the
    left finder's first bar. The bar must be tall and thin (1 x 7 cells)."""
    h_img, w_img = magenta.shape
    bar_h = _run(edge[y:, x])
    if bar_h < MIN_BAR_HEIGHT:
        return None
    ym = y + bar_h // 2
    left = x - _run(magenta[ym, x::-1]) + 1
    bar_w = x - left + 1
    if bar_w < 1 or not (4.0 <= bar_h / bar_w <= 11.0):
        return None
    cell_h = bar_h / 7.0

    # The magenta bar of the right finder sits exactly 62 cells further along.
    # Measuring that distance gives an accurate horizontal cell size.
    lo = int(left + 55 * cell_h)
    hi = min(w_img, int(left + 70 * cell_h) + 1)
    if lo >= w_img:
        return None
    hits = np.flatnonzero(magenta[ym, lo:hi])
    if hits.size == 0:
        return None
    cell_w = (lo + int(hits[0]) - left) / float(RIGHT_MAGENTA_COL - 1)
    if not (0.75 <= cell_w / cell_h <= 1.33):
        return None

    def centre(col, row):
        return left + (col - 1 + 0.5) * cell_w, y + (row - 1 + 0.5) * cell_h

    def is_set(mask, col, row=4):
        v = _patch(mask, *centre(col, row), cell_w, cell_h)
        return v is not None and v > 0.6

    def lum(col, row):
        v = _patch(luma, *centre(col, row), cell_w, cell_h)
        return -1 if v is None else v

    if not (is_set(magenta, 1) and is_set(cyan, 2) and is_set(magenta, 3)
            and is_set(cyan, 62) and is_set(magenta, 63) and is_set(cyan, 64)):
        return None
    if not (0 <= lum(4, 4) < 90 and 0 <= lum(13, 4) < 90 and 0 <= lum(61, 4) < 90):
        return None

    bits = []
    for i in range(8):
        votes = sum(lum(STATE_COL + i, row) > LUMA_ON for row in (2, 4, 6))
        bits.append(votes >= 2)
    count = 1 + sum(bits[:6])
    checksum_ok = (bits[6] == bool(count & 1)) and (bits[7] == bool(count & 2))

    chars, word_ok = [], True
    for ch in range(CHARS):
        cells = [
            lum(TEXT_COL + ch * 6 + px, 1 + py) > LUMA_ON
            for py in range(GLYPH_H) for px in range(GLYPH_W)
        ]
        letter, errors = match_glyph(cells)
        if errors > MAX_GLYPH_ERRORS:
            letter, word_ok = "?", False
        chars.append(letter)
    word = "".join(chars).strip()

    # Right-hand field (addon 1.4+): a cyan-magenta-cyan marker, then the character name.
    name, cols = "", COLS
    if (is_set(cyan, NAME_MARK_COL) and is_set(magenta, NAME_MARK_COL + 1)
            and is_set(cyan, NAME_MARK_COL + 2)):
        cols = NAME_COLS
        letters = []
        for ch in range(NAME_CHARS):
            cells = [
                lum(NAME_COL + ch * 6 + px, 1 + py) > LUMA_ON
                for py in range(GLYPH_H) for px in range(GLYPH_W)
            ]
            letter, errors = match_glyph(cells)
            if errors > MAX_GLYPH_ERRORS:
                letters = []
                break
            letters.append(letter)
        name = "".join(letters).strip()
        if not name.isalpha():
            name = ""

    return Beacon(
        x=left - cell_w, y=y - cell_h, cell_w=cell_w, cell_h=cell_h,
        bits=bits, word=word, checksum_ok=checksum_ok, word_ok=word_ok and bool(word),
        name=name, cols=cols,
    )


def locate(img):
    """Find the beacon in an HxWx3 uint8 RGB image. Returns a Beacon or None."""
    if img.ndim != 3 or img.shape[0] < MIN_BAR_HEIGHT or img.shape[1] < 60:
        return None
    img = img[..., :3]
    magenta, cyan = _masks(img)
    if not magenta.any():
        return None

    # The finder's signature is a magenta bar with a cyan bar directly to its
    # right. "edge" marks the last magenta pixel before cyan (up to 3 blended
    # pixels between them are allowed, for scaled or blurred screens). Looking for
    # this edge, not for a bare magenta corner, keeps the reader working when
    # another overlay touches or covers the top of the beacon.
    edge = np.zeros_like(magenta)
    near_cyan = cyan[:, 1:].copy()
    near_cyan[:, :-1] |= cyan[:, 2:]
    near_cyan[:, :-2] |= cyan[:, 3:]
    edge[:, :-1] = magenta[:, :-1] & ~magenta[:, 1:] & near_cyan
    # Candidate = top pixel of an edge column at least MIN_BAR_HEIGHT tall. This
    # throws out nearly everything in a busy scene before the per-candidate work.
    corner = edge.copy()
    corner[1:, :] &= ~edge[:-1, :]
    n = MIN_BAR_HEIGHT
    csum = np.cumsum(edge, axis=0, dtype=np.int32)
    tall = np.zeros_like(edge)
    tall[:-n + 1 or None, :] = (csum[n - 1:, :] - np.vstack(
        [np.zeros((1, edge.shape[1]), np.int32), csum[:-n, :]])) == n
    corner &= tall
    ys, xs = np.nonzero(corner)
    if ys.size == 0:
        return None

    luma = (0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]).astype(np.float32)
    fallback = None
    for y, x in list(zip(ys.tolist(), xs.tolist()))[:MAX_CANDIDATES]:
        found = _try_candidate(img, magenta, cyan, luma, edge, x, y)
        if found is None:
            continue
        if found.trusted:
            return found
        fallback = fallback or found
    return fallback


# ---------------------------------------------------------------------------
# Synthetic beacon, used by the self-test and the unit tests.
# ---------------------------------------------------------------------------
def make_bits(enemy=False, pvp=False, combat=False, manual=False, horde=False, beat=False):
    bits = [enemy, pvp, combat, manual, horde, beat]
    count = 1 + sum(bits)
    return bits + [bool(count & 1), bool(count & 2)]


def render(bits, word, cell=3, name=None):
    """Draw a beacon exactly as the addon does. Returns an HxWx3 uint8 RGB image.
    name=None draws the one-line beacon of addon versions before 1.4."""
    from .font import GLYPHS
    grid = np.zeros((ROWS, COLS if name is None else NAME_COLS, 3), dtype=np.uint8)
    magenta, cyan, white = (255, 0, 255), (0, 255, 255), (255, 255, 255)
    for col, colour in ((1, magenta), (2, cyan), (3, magenta), (62, cyan), (63, magenta), (64, cyan)):
        grid[1:8, col] = colour
    for i, on in enumerate(bits):
        if on:
            grid[1:8, STATE_COL + i] = white
    for ch, letter in enumerate(word.upper()[:CHARS]):
        glyph = GLYPHS.get(letter, GLYPHS[" "])
        for i, on in enumerate(glyph):
            if on:
                grid[1 + i // GLYPH_W, TEXT_COL + ch * 6 + i % GLYPH_W] = white
    if name is not None:
        for i, colour in enumerate((cyan, magenta, cyan)):
            grid[2:7, NAME_MARK_COL + i] = colour
        for ch, letter in enumerate(name.upper()[:NAME_CHARS]):
            glyph = GLYPHS.get(letter, GLYPHS[" "])
            for i, on in enumerate(glyph):
                if on:
                    grid[1 + i // GLYPH_W, NAME_COL + ch * 6 + i % GLYPH_W] = white
    return np.repeat(np.repeat(grid, cell, axis=0), cell, axis=1)
