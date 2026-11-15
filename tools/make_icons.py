# Draws the WRC icon set (war shield, crossed swords, record dot) with plain
# geometry (no AI imagery) and the Ionity
# wordmark from the Ionity assets repo (icons/brand/ionity-wordmark-white.png).
#   python tools/make_icons.py
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "icons")
NAVY_TOP, NAVY_BOTTOM = (20, 44, 68), (8, 17, 28)
CYAN, RED, WHITE = (0, 198, 255), (230, 40, 60), (232, 244, 248)
WORDMARK = Image.open(os.path.join(OUT, "brand", "ionity-wordmark-white.png")).convert("RGBA")


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def glow(layer, radius, strength=1.0):
    """A blurred copy of a layer, to sit underneath it."""
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        g.putalpha(g.getchannel("A").point(lambda v: int(min(255, v * strength))))
    return g


def _bezier(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def shield_points(cx, top, w, h):
    """Outline of a heater (war) shield: peaked top edge, straight shoulders, curved sides to a point."""
    l, r, bottom = cx - w / 2, cx + w / 2, top + h
    shoulder = top + h * 0.40
    pts = _bezier((l, top + h * 0.07), (cx - w * 0.25, top + h * 0.06), (cx, top))            # top, left half
    pts += _bezier((cx, top), (cx + w * 0.25, top + h * 0.06), (r, top + h * 0.07))[1:]       # top, right half
    pts += [(r, shoulder)]
    pts += _bezier((r, shoulder), (r - w * 0.02, top + h * 0.78), (cx, bottom))[1:]           # right side
    pts += _bezier((cx, bottom), (l + w * 0.02, top + h * 0.78), (l, shoulder))[1:]           # left side
    return pts


def sword(d, s, x0, y0, x1, y1, width):
    """A sword from the pommel (x0, y0) to the tip (x1, y1)."""
    import math
    ang = math.atan2(y1 - y0, x1 - x0)
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux
    length = math.hypot(x1 - x0, y1 - y0)
    gx, gy = x0 + ux * length * 0.20, y0 + uy * length * 0.20                 # crossguard position
    steel, grip = (214, 228, 238, 255), (0, 150, 200, 255)
    d.line((x0, y0, gx, gy), fill=grip, width=int(width * 1.1))                             # grip
    d.line((gx, gy, x1 - ux * width, y1 - uy * width), fill=steel, width=width)              # blade
    d.polygon([(x1, y1), (x1 - ux * width * 1.6 + px * width / 2, y1 - uy * width * 1.6 + py * width / 2),
               (x1 - ux * width * 1.6 - px * width / 2, y1 - uy * width * 1.6 - py * width / 2)], fill=steel)  # tip
    g = width * 2.6
    d.line((gx - px * g, gy - py * g, gx + px * g, gy + py * g), fill=CYAN + (255,), width=int(width * 0.9))    # guard
    r = int(width * 0.9)
    d.ellipse((x0 - r, y0 - r, x0 + r, y0 + r), fill=CYAN + (255,))                           # pommel


def emblem(img, s, cx, top, w, h, dot):
    """Crossed swords, a war shield over them, and the record dot on the shield."""
    swords = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(swords)
    sw = int(w * 0.060)
    mid = top + h * 0.47
    reach_x, reach_y = w * 0.70, h * 0.50
    sword(d, s, cx - reach_x, mid + reach_y, cx + reach_x, mid - reach_y, sw)
    sword(d, s, cx + reach_x, mid + reach_y, cx - reach_x, mid - reach_y, sw)
    img.alpha_composite(glow(swords, s * 0.012, 0.6))
    img.alpha_composite(swords)

    pts = shield_points(cx, top, w, h)
    rim = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(rim).polygon(pts, fill=CYAN + (255,))
    img.alpha_composite(glow(rim, s * 0.022, 0.85))
    img.alpha_composite(rim)
    # shield face: navy, lighter at the top, inset from the cyan rim
    inset = w * 0.075
    face_pts = shield_points(cx, top + inset * 1.05, w - inset * 2, h - inset * 2.3)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(face_pts, fill=255)
    face = Image.new("RGBA", (1, s))
    for y in range(s):
        t = min(1.0, max(0.0, (y - top) / h))
        face.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip((30, 62, 94), (9, 20, 33))) + (255,))
    img.paste(face.resize((s, s)), (0, 0), mask)
    # centre ridge, as on a real shield
    ridge = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(ridge).line((cx, top + h * 0.10, cx, top + h * 0.88), fill=(255, 255, 255, 26), width=max(1, int(w * 0.012)))
    img.alpha_composite(ridge)

    # record dot on the shield
    cy, rad = top + h * 0.40, w * 0.215
    halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((cx - rad * 1.7, cy - rad * 1.7, cx + rad * 1.7, cy + rad * 1.7), fill=dot + (80,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(s * 0.03)))
    dotl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(dotl)
    ring = rad * 1.30
    d.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=WHITE, width=max(2, int(w * 0.035)))
    d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=dot)
    img.alpha_composite(glow(dotl, s * 0.02, 0.6))
    img.alpha_composite(dotl)
    shine = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hr = rad * 0.5
    ImageDraw.Draw(shine).ellipse((cx - hr - rad / 4, cy - hr - rad / 3, cx + hr - rad / 4, cy + hr - rad / 3),
                                  fill=(255, 255, 255, 75))
    img.alpha_composite(shine.filter(ImageFilter.GaussianBlur(s * 0.02)))


def draw(size=1024, dot=RED, text=True, rounded=True):
    s = size * 2                                   # supersample for smooth edges
    grad = Image.new("RGBA", (1, s))
    for y in range(s):
        t = y / (s - 1)
        grad.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM)) + (255,))
    img = grad.resize((s, s))
    if text:
        emblem(img, s, s * 0.5, s * 0.085, s * 0.46, s * 0.56, dot)
        d = ImageDraw.Draw(img)
        f = font(int(s * 0.125))
        box = d.textbbox((0, 0), "WRC", font=f)
        d.text(((s - (box[2] - box[0])) // 2 - box[0], int(s * 0.685) - box[1]), "WRC", font=f, fill=WHITE)
        ww = int(s * 0.30)
        wm = WORDMARK.resize((ww, int(ww * WORDMARK.height / WORDMARK.width)), Image.LANCZOS)
        img.alpha_composite(wm, ((s - ww) // 2, int(s * 0.885) - wm.height // 2))
    else:
        emblem(img, s, s * 0.5, s * 0.12, s * 0.60, s * 0.74, dot)
    if rounded:
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.18), fill=255)
        img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
    return img.resize((size, size), Image.LANCZOS)


os.makedirs(OUT, exist_ok=True)
master = draw(1024)
master.save(os.path.join(OUT, "wrc-icon-1024.png"))
master.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "wrc-icon-512.png"))
master.resize((400, 400), Image.LANCZOS).save(os.path.join(OUT, "wrc-curseforge-avatar-400.png"))
draw(1024, dot=CYAN).resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "wrc-icon-idle-512.png"))
small = draw(1024, text=False)                     # no text below 64 px: it would be unreadable
small.save(os.path.join(OUT, "wrc.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
small.save(os.path.join(ROOT, "recorder", "wrc.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
# WoW addon-list icon: square, power-of-two, 32-bit TGA, no rounded corners.
draw(1024, text=False, rounded=False).resize((64, 64), Image.LANCZOS).save(os.path.join(ROOT, "addon", "WRC", "icon.tga"))


def round_icon(dot, size=128):
    """Round in-game button: navy disc, glowing cyan ring, war shield with the record dot.
    Transparent outside the circle."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    disc = Image.new("RGBA", (1, s))
    for y in range(s):
        t = y / (s - 1)
        disc.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM)) + (255,))
    disc = disc.resize((s, s))
    mask = Image.new("L", (s, s), 0)
    pad = int(s * 0.06)
    ImageDraw.Draw(mask).ellipse((pad, pad, s - pad, s - pad), fill=255)
    img.paste(disc, (0, 0), mask)
    inner = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    emblem(inner, s, s * 0.5, s * 0.20, s * 0.46, s * 0.60, dot)
    inner.putalpha(ImageChops.multiply(inner.getchannel("A"), mask))       # swords stay inside the disc
    img.alpha_composite(inner)
    ringl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(ringl).ellipse((pad, pad, s - pad, s - pad), outline=CYAN, width=int(s * 0.05))
    img.alpha_composite(glow(ringl, s * 0.02, 0.9))
    img.alpha_composite(ringl)
    return img.resize((size, size), Image.LANCZOS)


# White rounded square for the addon's nine-slice skin (8 px corners, anti-aliased).
_s = 32 * 8
_r = Image.new("L", (_s, _s), 0)
ImageDraw.Draw(_r).rounded_rectangle((0, 0, _s - 1, _s - 1), radius=8 * 8, fill=255)
_w = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
_w.putalpha(_r.resize((32, 32), Image.LANCZOS))
_w.save(os.path.join(ROOT, "addon", "WRC", "rounded.tga"))

round_icon(CYAN).save(os.path.join(ROOT, "addon", "WRC", "round_idle.tga"))
round_icon(RED).save(os.path.join(ROOT, "addon", "WRC", "round_rec.tga"))
round_icon(CYAN, 256).save(os.path.join(OUT, "wrc-round-idle-256.png"))
round_icon(RED, 256).save(os.path.join(OUT, "wrc-round-rec-256.png"))
# Header strip for the recorder window.
ww = 150
WORDMARK.resize((ww, int(ww * WORDMARK.height / WORDMARK.width)), Image.LANCZOS).save(
    os.path.join(ROOT, "recorder", "ionity_logo.png"))
print("\n".join(sorted(f for f in os.listdir(OUT) if "." in f)))
