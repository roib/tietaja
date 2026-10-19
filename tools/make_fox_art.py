#!/usr/bin/env python3
"""Paints the art for the third tale, The Fire Fox: Lapland in the polar night, in the
manner of the other tales (Werner Holmberg's spruces, rocks and hazy distances, repainted
in oil brushwork), but under the stars, deep in snow, with snow-laden spruces, a frozen
lake and the fells. Light is laid on after the brushwork (firelight, the fox's fire, the
northern lights), so it stays luminous instead of being smeared into paint.

Shares its painters and conventions with make_art.py: room units, 320x144 rooms painted at
SCALE times that, sprites the size of their hotspot rectangles in assets/fox.txt.

Usage: python3 tools/make_fox_art.py [part ...]
"""
import math
import random
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_art as A  # noqa: E402
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter  # noqa: E402

s = A.s
W = A.W

# Night colours for make_art's painters: spruces almost black-green, lit at the edges by
# the snow and the sky, fading into blue haze with distance.
A.SPRUCE_DARK = (8, 16, 22)
A.SPRUCE_MID = (16, 30, 36)
A.SPRUCE_LIGHT = (70, 112, 112)
A.SKY_HAZE = (58, 78, 122)
A.BARK = (22, 20, 24)

NIGHT_TOP = (4, 6, 22)
NIGHT_MID = (14, 26, 62)
NIGHT_LOW = (34, 64, 100)
GREEN = (110, 255, 160)
PINK = (255, 90, 170)
VIOLET = (150, 80, 230)
SNOW_HI = (206, 226, 238)
SNOW_MID = (120, 144, 186)
SNOW_LO = (40, 52, 98)
NIGHT_GLAZE = (110, 140, 230)
FIRELIGHT = (255, 150, 70)
FLAME_CORE = (255, 246, 214)
FLAME = (255, 168, 64)
FLAME_EDGE = (226, 72, 40)
SPIRIT_GREEN = (120, 255, 190)
EMBER = (255, 170, 70)

INTRO_SIZE = (832, 180)  # room units: the intro's panorama, 2.6 frames wide
FOX_SPARK = (586, 171)  # where the fox's last spark glimmers in it; FOX_SPARK in src/levels.rs


@contextmanager
def canvas(width_units, height_units):
    """Paint on a canvas of another size (the intro's panorama), for make_art's painters
    as well as these."""
    global W
    base = W, A.W, A.H
    W = A.W = s(width_units)
    A.H = s(height_units)
    try:
        yield
    finally:
        W, A.W, A.H = base


@contextmanager
def canvas_height(units):
    """Paint on a taller canvas (the intro's), for make_art's painters as well as these."""
    base = A.H
    A.H = s(units)
    try:
        yield A.H
    finally:
        A.H = base


def H():
    return A.H


def black():
    return Image.new("RGBA", (W, H()), (0, 0, 0, 255))


def screen(base, light):
    """Add light the way light adds: brightening, never covering."""
    out = ImageChops.screen(base.convert("RGB"), light.convert("RGB")).convert("RGBA")
    out.putalpha(base.getchannel("A"))
    return out


def smooth(pts, n=200):
    """A Catmull-Rom curve through the points."""
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    per = max(1, n // (len(P) - 3))
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def mask_of(shape_pts):
    m = Image.new("L", (W, H()), 0)
    ImageDraw.Draw(m).polygon(shape_pts, fill=255)
    return m


# ---------------------------------------------------------------- the sky


def night_gradient(img, horizon):
    d = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = min(1.0, y / max(1, horizon))
        col = A.mix(NIGHT_TOP, NIGHT_MID, min(1.0, t / 0.55)) if t < 0.55 else A.mix(NIGHT_MID, NIGHT_LOW, (t - 0.55) / 0.45)
        d.line([(0, y), (w, y)], fill=col + (255,))


def star_layer(rng, w, h, count, bottom, glints=True):
    """Stars, crisp: they go on after the brushwork, which would smear them."""
    lay = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        x, y = rng.uniform(0, w), rng.uniform(0, bottom) ** 1.05 * bottom ** -0.05
        b = rng.random() ** 3
        c = A.mix((170, 190, 255), (255, 240, 220), rng.random())
        r = 0.6 + b * 2.0
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (int(110 + 145 * b),))
        if glints and b > 0.93:
            L = s(1.5 + 3 * b)
            d.line([(x - L, y), (x + L, y)], fill=c + (80,), width=1)
            d.line([(x, y - L), (x, y + L)], fill=c + (80,), width=1)
    return lay


def milky_way(img, rng, y0, y1):
    w, h = img.size
    band = Image.new("RGBA", (w, h))
    bd = ImageDraw.Draw(band)
    for _ in range(int(w * 3)):
        u = rng.random()
        x = u * w
        y = y0 + (y1 - y0) * (0.5 + 0.5 * math.sin(u * math.pi * 2 * w / (W * 2))) + rng.gauss(0, s(9))
        bd.point((x, y), fill=(180, 190, 230, rng.randint(40, 130)))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(s(2.5))))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(0.6)))


def curtain(rng, size, pts, height, alpha, sway=0.0):
    """One curtain of the aurora along a curve: dense fine rays with a hot green hem and a
    magenta fringe beneath it, fading upward through green into violet."""
    lay = Image.new("RGBA", size)
    d = ImageDraw.Draw(lay)
    line = smooth(pts, 400)
    seg = []
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0)))
        seg += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    phase = [rng.uniform(0, 6.28) for _ in range(3)]
    for i, (x, y) in enumerate(seg):
        u = i / max(1, len(seg))
        bands = 0.5 + 0.5 * math.sin(u * 31 + phase[0]) * math.sin(u * 7 + phase[1])
        strength = (0.25 + 0.75 * bands ** 1.5) * (0.65 + 0.35 * math.sin(u * 3 + phase[2])) * rng.uniform(0.55, 1.15)
        h = height * (0.45 + 0.8 * strength) * rng.uniform(0.85, 1.1)
        lean = sway * h
        steps = 40
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            if t0 < 0.06:
                col, a = A.mix(PINK, (200, 255, 210), t0 / 0.06), 0.85
            elif t0 < 0.14:
                col, a = A.mix((200, 255, 210), GREEN, (t0 - 0.06) / 0.08), 1.0
            else:
                col, a = A.mix(GREEN, VIOLET, min(1, ((t0 - 0.14) / 0.86) ** 0.9 * 1.15)), (1 - (t0 - 0.14) / 0.86) ** 1.4
            d.line([(x + lean * t0, y - h * t0), (x + lean * t1, y - h * t1)], fill=col + (int(min(255, alpha * strength * a)),), width=1)
    return lay


def aurora_light(rng, size, curtains, glow=1.0):
    """Curtains of the aurora as light on black: crisp rays, their glow, and a wide halo."""
    lay = Image.new("RGBA", size)
    for pts, h, a, sway in curtains:
        lay.alpha_composite(curtain(rng, size, pts, h, a, sway))
    light = Image.new("RGBA", size, (0, 0, 0, 255))
    light.alpha_composite(lay.filter(ImageFilter.GaussianBlur(s(0.35))))
    light.alpha_composite(lay.filter(ImageFilter.GaussianBlur(s(3))))
    halo = lay.filter(ImageFilter.GaussianBlur(s(16)))
    for _ in range(round(2 * glow)):
        light.alpha_composite(halo)
    return light


def as_glow(light, boost=4.0):
    """Light on black to a transparent image of the same light, for the game to lay over
    the scene: the colour brightened, and as opaque as the light is bright."""
    rgb = light.convert("RGB")
    r, g, b = rgb.split()
    peak = ImageChops.lighter(ImageChops.lighter(r, g), b)
    alpha = peak.point(lambda v: min(255, int(v * 1.2)))
    bright = rgb.point(lambda v: min(255, int(v * boost)))  # dim glow stays bright in colour, so it never darkens what's behind
    return Image.merge("RGBA", list(bright.split()) + [alpha])


def night_sky_layer(path, seed, horizon, aurora=0.25):
    """A drifting night sky, twice the room's width: stars and the Milky Way, and the ghost
    of the aurora that should be burning there. Periodic in x, so it tiles as it scrolls."""
    rng = random.Random(seed)
    w, h = W * 2, H()
    img = Image.new("RGBA", (w, h))
    night_gradient(img, int(h * horizon))
    milky_way(img, rng, s(4), s(40))
    base, A.W = A.W, w  # make_art's brushwork paints the whole (double-width) canvas
    try:
        img = A.oil_paint(img, rng)
    finally:
        A.W = base
    if aurora:
        # Draw over three widths and keep the middle, so the curtains and their glow wrap.
        big = (w * 3, h)
        k = 2
        pts = [(x, s(40) + s(10) * math.sin(x / w * 2 * math.pi * k) + s(5) * math.sin(x / w * 2 * math.pi * 5))
               for x in range(-s(20), w * 3 + s(20), s(20))]
        light = aurora_light(rng, big, [(pts, s(42), 255, -0.25)], glow=0.6)
        light = light.crop((w, 0, w * 2, h)).point(lambda v: int(v * aurora))
        img = screen(img, light)
    stars = star_layer(rng, w, h, 1100, int(h * horizon))
    img.alpha_composite(stars.filter(ImageFilter.GaussianBlur(1.0)))
    img.alpha_composite(stars)
    A.save(img.convert("RGB"), path)


# ---------------------------------------------------------------- snow and land


def snow_cap(layer, depth, lit=SNOW_HI, shade=SNOW_MID):
    """Lay snow on everything in a layer: wherever something has open air above it, a
    cushion of snow `depth` deep sits on top."""
    mask = layer.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    cap = ImageChops.subtract(mask, A.shifted(mask, 0, depth))
    cap = cap.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 90 else 0)
    cap = ImageChops.multiply(cap, mask.filter(ImageFilter.MaxFilter(3)))
    snow = Image.new("RGBA", layer.size)
    d = ImageDraw.Draw(snow)
    for y in range(layer.size[1]):
        d.line([(0, y), (layer.size[0], y)], fill=A.mix(lit, shade, (y % 9) / 14) + (255,))
    snow.putalpha(cap)
    layer.alpha_composite(snow)
    return layer


def snowy_spruce(img, rng, cx, base, height, width, fade=0.0, depth=4, shadowed=0.0):
    """A spruce heavy with snow, every bough carrying its cushion."""
    lay = A.new_layer()
    A.spruce(lay, rng, cx, base, height, width, 1.0, 0.6, 0.5, 0.06, fade, shadowed)
    hi, mid = A.mix(SNOW_HI, A.SKY_HAZE, fade * 0.8), A.mix(SNOW_MID, A.SKY_HAZE, fade * 0.8)
    snow_cap(lay, depth, A.mix(hi, (20, 30, 60), shadowed * 0.5), A.mix(mid, (20, 30, 60), shadowed * 0.5))
    img.alpha_composite(lay)


def snowfield(img, rng, top, bottom, pts=None, lit=SNOW_HI, mid=SNOW_MID, low=SNOW_LO, strokes=5000):
    """Rolling snow: broad blue shadows and lit drifts, laid on in long flat strokes."""
    lay = A.new_layer()
    d = ImageDraw.Draw(lay)
    for y in range(int(top), int(bottom)):
        t = (y - top) / max(1, bottom - top)
        d.line([(0, y), (W, y)], fill=A.mix(mid, low, t * 0.6) + (255,))
    cv = A.Canvas(lay)
    for _ in range(strokes):
        x, y = rng.uniform(0, W), rng.uniform(top, bottom)
        u = x / W
        drift = 0.5 + 0.5 * math.sin(u * 7 + y * 0.02) * math.sin(u * 2.3 + y * 0.011)
        col = A.mix(low, lit, drift * rng.uniform(0.6, 1.1))
        t = (y - top) / max(1, bottom - top)
        A.dab(cv, x, y, s(rng.uniform(2, 7)) * (0.5 + t), s(rng.uniform(0.3, 0.6)) * (0.5 + t), col + (150,), rng.uniform(-0.08, 0.08), 6)
    cv.flush()
    if pts:
        lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask_of(pts)))
    A.paint(img, lay, 0.6)


def ridge(rng, base, height, x0=0, x1=None, k=(3.4, 8, 23)):
    x1 = W if x1 is None else x1
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    pts = [(x0, H())]
    for x in range(int(x0), int(x1) + 8, 8):
        u = x / W
        pts.append((x, base - height * (0.5 + 0.3 * math.sin(u * k[0] + ph[0]) + 0.15 * math.sin(u * k[1] + ph[1]) + 0.05 * math.sin(u * k[2] + ph[2]))))
    pts.append((x1, H()))
    return pts


def far_fells(img, rng, base, layers=((26, (64, 84, 132), (120, 170, 176)), (14, (46, 62, 108), (90, 130, 146))), freq=(3.4, 8, 23)):
    """Fells on the horizon, hazy blue with distance: snowfields catching the starlight on
    the slopes that face the sky, gullies running down them in shadow."""
    for i, (height, col, crown) in enumerate(layers):
        pts = ridge(rng, base + s(6) * i, s(height), k=freq)
        lay = A.new_layer()
        d = ImageDraw.Draw(lay)
        d.polygon(pts, fill=col + (255,))
        cv = A.Canvas(lay)
        crest = pts[1:-1]
        for j in range(1, len(crest) - 1):
            x, y = crest[j]
            slope = crest[j + 1][1] - crest[j - 1][1]  # rising to the right: the face is lit
            lit = slope > 0
            for _ in range(3):
                A.dab(cv, x + rng.uniform(-6, 6), y + rng.uniform(0, s(4)), rng.uniform(6, 14), rng.uniform(2, 4),
                      A.mix(crown, col, rng.random() * (0.3 if lit else 0.8)) + (180,), 0.1, 6)
            if rng.random() < 0.1:  # a gully running down the slope
                L = s(height) * rng.uniform(0.3, 0.8)
                ang = math.pi / 2 + rng.uniform(-0.5, 0.5)
                g = [(x, y + s(1))]
                for k in range(6):
                    gx, gy = g[-1]
                    g.append((gx + math.cos(ang) * L / 6 + rng.uniform(-s(1.2), s(1.2)), gy + math.sin(ang) * L / 6))
                cv.soft("line", smooth(g, 30), fill=A.mix(col, (10, 16, 40), 0.15) + (140,), width=max(2, int(s(1.4))))
                cv.soft("line", [(gx - s(1.0), gy) for gx, gy in smooth(g, 30)], fill=A.mix(crown, col, 0.5) + (110,), width=max(1, int(s(0.7))))
        cv.flush()
        lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask_of(pts)))
        A.paint(img, lay, 1.2 + i * 0.4)
    A.mist(img, rng, (base - s(2)) / A.SCALE, 10, 40, color=(110, 140, 170))


ROCK = ((16, 18, 30), (44, 48, 68), (90, 96, 120))


def rough_rock(img, rng, x0, y0, x1, y1, cap=0.2, palette=ROCK):
    """A broken rock in room units: an irregular lump with flat faces, lit from the upper
    left, cracked, and with snow lying on its top."""
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    n = 7
    pts = []
    for i in range(n):
        a = math.pi + 2 * math.pi * (i + rng.uniform(-0.25, 0.25)) / n
        r = rng.uniform(0.62, 1.1)
        pts.append((cx + math.cos(a) * rx * r, min(y1, cy + math.sin(a) * ry * r * rng.uniform(0.8, 1.3))))
    lay = A.new_layer()
    d = A.Painter(lay)
    A.tone(lay, pts, palette, "sphere", light=-0.25)
    for _ in range(2):  # a flat face or two, catching a little more light
        i = rng.randrange(n)
        a, b = pts[i], pts[(i + 1) % n]
        A.tone(lay, [a, b, (b[0] * 0.6 + cx * 0.4, b[1] * 0.6 + cy * 0.4), (a[0] * 0.6 + cx * 0.4, a[1] * 0.6 + cy * 0.4)], palette, "flat", light=rng.uniform(-0.2, 0.05))
    for _ in range(3):
        x = rng.uniform(x0 + rx * 0.3, x1 - rx * 0.3)
        A.stroke(d, [(x, cy - ry * 0.6), (x + rng.uniform(-2, 2), cy), (x + rng.uniform(-3, 3), cy + ry * 0.7)], palette[0], 0.3, 200)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask_of([(s(x), s(y)) for x, y in pts])))
    if cap:
        snow_cap(lay, max(2, int(s((y1 - y0) * cap))))
    A.shadow(img, [(s(x0), s(y1)), (s(x1 + 4), s(y1)), (s(x1 + 2), s(y1 + 2)), (s(x0 + 2), s(y1 + 2))], 80, 4)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.6)))
    if cap:  # snow drifted against its foot
        drift = A.new_layer()
        dv = A.Canvas(drift)
        for _ in range(int((x1 - x0) * 3)):
            x = rng.uniform(s(x0 - 2), s(x1 + 2))
            A.dab(dv, x, s(y1) - abs(rng.gauss(0, s((y1 - y0) * 0.12))), s(rng.uniform(1.5, 4)), s(rng.uniform(0.6, 1.4)),
                  A.mix(SNOW_MID, SNOW_HI, rng.random() * 0.7) + (255,), 0, 8)
        dv.flush()
        img.alpha_composite(drift)


def boulder(img, rng, x0, y0, x1, y1, cap=0.25):
    """A rock in the snow, cold grey-blue, with snow on its back (`cap` of its height)."""
    lay = A.new_layer()
    A.rock(lay, rng, x0, y0, x1, y1, moss=0.0)
    rgb = ImageChops.multiply(lay.convert("RGB"), Image.new("RGB", lay.size, (96, 106, 156))).convert("RGBA")
    rgb.putalpha(lay.getchannel("A"))
    if cap:
        snow_cap(rgb, max(2, int((y1 - y0) * cap)))
    img.alpha_composite(rgb)


def snow_mass(img, rng, blobs, lit=SNOW_HI, mid=SNOW_MID, low=SNOW_LO, needles=0.3, light_dir=(-1, -1)):
    """A soft form of piled snow made of overlapping round shapes melted together (a
    snow-laden spruce the wind has carved into a figure). Lit from the upper left, deep
    blue on the right, with dark needles showing through here and there."""
    m = Image.new("L", (W, H()), 0)
    md = ImageDraw.Draw(m)
    for cx, cy, rx, ry, *rot in blobs:
        if rot:  # a tilted oval, as a polygon
            a = rot[0]
            pts = [(s(cx) + math.cos(t) * s(rx) * math.cos(a) - math.sin(t) * s(ry) * math.sin(a),
                    s(cy) + math.cos(t) * s(rx) * math.sin(a) + math.sin(t) * s(ry) * math.cos(a)) for t in (i * math.pi / 16 for i in range(32))]
            md.polygon(pts, fill=255)
        else:
            md.ellipse([s(cx - rx), s(cy - ry), s(cx + rx), s(cy + ry)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(s(1.6))).point(lambda v: 255 if v > 110 else 0).filter(ImageFilter.GaussianBlur(1))
    k = s(3)
    lit_edge = ImageChops.subtract(m, A.shifted(m, -light_dir[0] * k, -light_dir[1] * k)).filter(ImageFilter.GaussianBlur(s(2)))
    dark_edge = ImageChops.subtract(m, A.shifted(m, light_dir[0] * k * 2, light_dir[1] * k * 2)).filter(ImageFilter.GaussianBlur(s(3)))
    lay = Image.new("RGBA", (W, H()), mid + (255,))
    for edge, col in ((dark_edge, low), (lit_edge, lit)):
        c = Image.new("RGBA", (W, H()), col + (255,))
        c.putalpha(edge)
        lay.alpha_composite(c)
    cv = A.Canvas(lay)
    box = m.getbbox() or (0, 0, 1, 1)
    for _ in range(int((box[2] - box[0]) * (box[3] - box[1]) / 90)):
        x, y = rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3])
        if m.getpixel((min(W - 1, int(x)), min(H() - 1, int(y)))) < 200:
            continue
        cur = lay.getpixel((int(x), int(y)))
        A.dab(cv, x, y, s(rng.uniform(1.2, 2.6)), s(rng.uniform(0.7, 1.4)), A.mix(cur[:3], A.mix(lit, low, rng.random()), 0.25) + (200,), rng.uniform(-0.5, 0.5), 8)
        if rng.random() < needles * 0.08:
            A.dab(cv, x, y, s(rng.uniform(0.6, 1.4)), s(rng.uniform(0.3, 0.6)), (12, 22, 32, 230), rng.uniform(-0.3, 0.3), 6)
    cv.flush()
    lay.putalpha(m)
    img.alpha_composite(lay)
    return m


def spark_dots(lay, rng, x, y, spread, count, colors, size=(0.5, 1.6)):
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        px, py = x + rng.gauss(0, spread), y + rng.gauss(0, spread)
        r = rng.uniform(*size)
        d.ellipse([px - r, py - r, px + r, py + r], fill=A.mix(*colors, rng.random()) + (rng.randint(150, 255),))


def glow_pool(light, cx, cy, rx, ry, color, alpha, blur):
    lay = Image.new("RGBA", light.size)
    ImageDraw.Draw(lay).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color + (alpha,))
    light.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))



def fox_tracks(img, light, rng, pts, n, size=2.0, glow=1.3):
    """The fox's tracks across the snow, in room units: a single line of prints (a fox sets
    each hind foot in its fore print), each a pad and four toes pressed in, blue in their
    hollows and lit on the far rim, and each still holding a little ember glow. The prints
    are painted into `img`; their glow is added to `light`, and returned as a mask too, so
    it can be hidden behind anything painted in front."""
    line = smooth([(s(x), s(y)) for x, y in pts], 300)
    marks = A.new_layer()
    md = A.Canvas(marks)
    embers = A.new_layer()
    ed = ImageDraw.Draw(embers)
    for i in range(n):
        t = (i + 0.5) / n
        j = int(t * (len(line) - 2))
        (x, y), (x2, y2) = line[j], line[j + 1]
        ang = math.atan2(y2 - y, x2 - x)
        nx, ny = -math.sin(ang), math.cos(ang)
        far = (H() - y) / H()  # smaller and fainter up the slope
        k = s(size) * (1.0 - 0.55 * far)
        side = 0.35 * k * (1 if i % 2 else -1)
        cx, cy = x + nx * side, y + ny * side * 0.4
        fwd = (math.cos(ang), math.sin(ang) * 0.4)
        A.dab(md, cx, cy, k * 0.55, k * 0.4, SNOW_LO + (200,), 0, 10)  # the pad
        A.dab(md, cx - fwd[0] * k * 0.12, cy - fwd[1] * k * 0.12 + k * 0.08, k * 0.5, k * 0.18, SNOW_HI + (150,), 0, 8)  # its lit rim
        for a in (-0.7, -0.25, 0.25, 0.7):  # four toes, splayed ahead of it
            tx = cx + (fwd[0] * math.cos(a) - fwd[1] * math.sin(a)) * k * 0.75
            ty = cy + (fwd[1] * math.cos(a) + fwd[0] * math.sin(a) * 0.4) * k * 0.75
            A.dab(md, tx, ty, k * 0.2, k * 0.15, SNOW_LO + (210,), 0, 7)
        r = k * 0.75
        ed.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=EMBER + (int(min(255, 230 * (1 - far * 0.4) * glow)),))
    md.flush()
    img.alpha_composite(marks.filter(ImageFilter.GaussianBlur(0.7)))
    glow_light = Image.new("RGBA", light.size, (0, 0, 0, 255))
    glow_light.alpha_composite(embers.filter(ImageFilter.GaussianBlur(s(1.6))))
    glow_light.alpha_composite(embers.filter(ImageFilter.GaussianBlur(s(1.6))))
    glow_light.alpha_composite(embers.filter(ImageFilter.GaussianBlur(s(0.35))))
    return glow_light


def fine_paint(layer, rng):
    """Brushwork for things with small detail (a door, antlers, a reindeer's legs) on a
    layer of their own: finer strokes than the room's, then the same grade and glaze."""
    out = A.oil_paint_sprite(layer, rng, A.SCALE, passes=((0.7, 0), (0.4, 10), (0.22, 20)))
    alpha = out.getchannel("A")
    out = ImageEnhance.Color(ImageEnhance.Contrast(out.convert("RGB")).enhance(1.22)).enhance(1.12).convert("RGBA")
    out.alpha_composite(Image.new("RGBA", out.size, NIGHT_GLAZE + (int(255 * 0.05),)))
    out.putalpha(alpha)
    return out


def save_night_room(img, rng, path, open_sky, light=None, warmth=0.05, detail=None):
    """Finish the room as a night painting: the brushwork and the canvas, a cool glaze, the
    finely painted `detail` layer laid in, the sky cut out (for the drifting sky behind),
    then the light laid over and the corners darkened."""
    out = A.finish(img, rng, warmth, NIGHT_GLAZE, vignette=False).convert("RGBA")
    if detail is not None:
        out.alpha_composite(fine_paint(detail, rng))
    if light is not None:
        out = screen(out, light)
    if open_sky is not None:
        out.putalpha(ImageChops.invert(open_sky))
    out.alpha_composite(A.vignette_layer(130))
    if open_sky is not None:  # the vignette doesn't fill the cut-out sky
        out.putalpha(ImageChops.invert(open_sky))
    A.save(out, path)
    return out


def open_sky_mask(sky_only, img):
    return A.sky_mask(sky_only, img)


# ---------------------------------------------------------------- the camp


def kota(img, rng, x0, x1, base, apex):
    """A turf kota: a cone of birch poles covered in sods, its sides bowed out a little,
    half buried in drifted snow, the pole tips crossing at the smoke hole and a low wooden
    door. Lit from the left by the starlit snow, deep in shadow on the right."""
    cx = (x0 + x1) / 2
    left = smooth([(x0, base), (x0 + (cx - x0) * 0.25, base - (base - apex) * 0.42), (cx - (cx - x0) * 0.42, base - (base - apex) * 0.8), (cx - 3, apex + 2)], 40)
    right = smooth([(cx + 3, apex + 2), (cx + (x1 - cx) * 0.42, base - (base - apex) * 0.8), (x1 - (x1 - cx) * 0.25, base - (base - apex) * 0.42), (x1, base)], 40)
    outline = [(s(x), s(y)) for x, y in left + right]
    shape = mask_of(outline)
    lay = Image.new("RGBA", (W, H()))
    d = ImageDraw.Draw(lay)
    for x in range(int(s(x0)), int(s(x1)) + 1):  # light across the cone
        f = (x - s(x0)) / s(x1 - x0)
        lit = max(0.0, 1 - f * 1.5) ** 1.2
        d.line([(x, 0), (x, H())], fill=A.mix((26, 24, 32), (108, 104, 116), lit) + (255,))
    cv = A.Canvas(lay)
    for _ in range(3200):  # sods: short strokes laid in rows round the cone
        y = rng.uniform(s(apex), s(base))
        t = (y - s(apex)) / s(base - apex)
        half = s((x1 - x0) / 2) * (0.06 + 0.94 * t ** 0.85)
        x = s(cx) + rng.uniform(-half, half)
        f = (x - s(x0)) / s(x1 - x0)
        lit = max(0.0, 1 - f * 1.5) ** 1.2
        col = A.mix((30, 28, 34), (132, 124, 128), lit * rng.uniform(0.7, 1.15))
        if rng.random() < 0.25:
            col = A.mix(col, (70, 76, 50), 0.4)  # dead grass in the turf
        tilt = (x - s(cx)) / max(1, half) * 0.25
        A.dab(cv, x, y, s(rng.uniform(1.4, 3.2)), s(rng.uniform(0.5, 0.9)), col + (210,), tilt, 7)
    for _ in range(160):  # snow lodged on the sods, more toward the bottom and on the lit side
        y = s(apex) + s(base - apex) * rng.random() ** 0.6
        t = (y - s(apex)) / s(base - apex)
        half = s((x1 - x0) / 2) * (0.06 + 0.94 * t ** 0.85)
        x = s(cx) + rng.uniform(-half, half * 0.5)
        A.dab(cv, x, y, s(rng.uniform(1.2, 3.4)), s(rng.uniform(0.4, 0.8)), A.mix(SNOW_MID, SNOW_HI, rng.random()) + (230,), rng.uniform(-0.3, 0.3), 7)
    cv.flush()
    lay.putalpha(shape)
    d = ImageDraw.Draw(lay)
    for dx in (-6, -3, 2, 5):  # pole tips crossing above the smoke hole
        d.line([(s(cx + dx * 0.15), s(apex + 4)), (s(cx + dx), s(apex - 8))], fill=(70, 58, 50, 255), width=int(s(0.8)))
        d.line([(s(cx + dx * 0.15) - 2, s(apex + 4)), (s(cx + dx) - 2, s(apex - 8))], fill=(150, 140, 130, 255), width=2)
    # A band of birch bark round the foot, under the sods, white with dark marks.
    bark = A.new_layer()
    bd = A.Painter(bark)
    for xb in range(int(x0), int(x1)):
        t = (xb - x0) / (x1 - x0)
        lit = max(0.0, 1 - t * 1.5)
        top_y = base - 7 + 3 * abs(t - 0.5)
        A.stroke(bd, [(xb, top_y), (xb, base)], A.mix((70, 70, 80), (200, 200, 206), lit), 1.1, 255)
        if rng.random() < 0.5:
            A.stroke(bd, [(xb, top_y + rng.uniform(1, 5)), (xb + 1.2, top_y + rng.uniform(1, 5))], (30, 28, 34), 0.25, 220)
    bark.putalpha(ImageChops.multiply(bark.getchannel("A"), shape))
    lay.alpha_composite(bark)
    # The door: an arched frame of bent birch poles, the plank door standing a little open,
    # firelight inside, and antlers fixed over it.
    dw, dh = (x1 - x0) * 0.1, (base - apex) * 0.34
    arch = A.curve((cx - dw, base), (cx, base - dh * 1.5), (cx + dw, base), 16)
    pd = A.Painter(lay)
    A.tone(lay, arch, ((60, 24, 10), (190, 96, 40), (255, 190, 110)), "flat", light=0.1)  # the opening, lit within
    A.stroke(pd, arch, (90, 72, 58), 1.6, 255)  # the frame poles
    A.stroke(pd, [(px - 0.5, py) for px, py in arch], (150, 132, 112), 0.5, 220)
    door_leaf = [(cx + dw * 0.1, base), (cx + dw * 0.15, base - dh * 0.68), (cx + dw * 0.75, base - dh * 0.55), (cx + dw * 0.8, base)]
    A.tone(lay, door_leaf, ((30, 22, 20), (70, 54, 44), (120, 96, 76)), "flat")
    for kk in (0.33, 0.55):
        A.stroke(pd, [(cx + dw * (0.1 + kk), base - dh * 0.6), (cx + dw * (0.1 + kk), base)], (24, 18, 16), 0.25, 220)
    for side in (-1, 1):  # antlers fixed over the door
        bx, by = cx + side * 1.0, base - dh * 1.12
        A.stroke(pd, A.curve((bx, by), (bx + side * 4, by - 2), (bx + side * 5, by - 6), 8), (170, 160, 146), 0.45, 255)
        for t2 in (0.4, 0.75):
            tx2, ty2 = bx + side * 4 * t2 + side * 0.5, by - 6 * t2
            A.stroke(pd, [(tx2, ty2), (tx2 + side * 1.6, ty2 - 1.2)], (170, 160, 146), 0.3, 255)
    door = [(s(px), s(py)) for px, py in arch]
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.5)))
    for a2 in range(10):  # stones round the foot
        sx = x0 + 4 + a2 * (x1 - x0 - 8) / 9 + rng.uniform(-1, 1)
        if abs(sx - cx) < dw + 2:
            continue
        stone = A.new_layer()
        A.tone(stone, A.oval(sx, base - 0.6, rng.uniform(1.6, 2.6), 1.2), ROCK, "sphere")
        img.alpha_composite(stone)
    # Snow drifted up round the foot of it.
    drift = A.new_layer()
    dv = A.Canvas(drift)
    for _ in range(260):
        x = rng.uniform(s(x0 - 6), s(x1 + 8))
        y = s(base) - abs(rng.gauss(0, s(1.6)))
        A.dab(dv, x, y, s(rng.uniform(2, 6)), s(rng.uniform(0.8, 1.8)), A.mix(SNOW_MID, SNOW_HI, rng.random() * 0.8 + (0.2 if x < s(cx) else 0)) + (255,), 0, 8)
    dv.flush()
    door_gap = Image.new("L", (W, H()), 255)
    ImageDraw.Draw(door_gap).polygon([(x, y + s(1)) for x, y in door], fill=0)
    drift.putalpha(ImageChops.multiply(drift.getchannel("A"), door_gap.filter(ImageFilter.GaussianBlur(2))))
    img.alpha_composite(drift)
    return door


def kota_light(light, door, cx, apex):
    """The kota's fire, seen from outside: glowing in the open door and spilling out across
    the snow, and lighting the smoke where it leaves the smoke hole."""
    dl = Image.new("RGBA", light.size)
    ImageDraw.Draw(dl).polygon(door, fill=(255, 150, 70, 150))
    light.alpha_composite(dl.filter(ImageFilter.GaussianBlur(s(1))))
    light.alpha_composite(dl.filter(ImageFilter.GaussianBlur(s(5))))
    x0, x1 = min(p[0] for p in door), max(p[0] for p in door)
    base = max(p[1] for p in door)
    spill = Image.new("RGBA", light.size)  # a fan of light thrown out over the snow
    ImageDraw.Draw(spill).polygon([(x0, base), (x1, base), (x1 + (x1 - x0) * 1.6, base + s(14)), (x0 - (x1 - x0) * 0.8, base + s(14))], fill=(255, 140, 60, 90))
    light.alpha_composite(spill.filter(ImageFilter.GaussianBlur(s(4))))
    glow_pool(light, cx, apex, s(6), s(5), FIRELIGHT, 110, s(4))


def drying_rack(img, rng, x0, x1, top, base):
    """Two forked poles and a crossbar, with the woven band hanging from it."""
    lay = A.new_layer()
    d = ImageDraw.Draw(lay)
    for x in (x0, x1):
        d.line([(s(x), s(base)), (s(x + 0.6), s(top))], fill=(58, 46, 40, 255), width=int(s(1.1)))
    d.line([(s(x0 - 2), s(top + 1)), (s(x1 + 2), s(top))], fill=(64, 52, 44, 255), width=int(s(1.0)))
    snow_cap(lay, int(s(0.8)))
    # The band: red and white wool, little figures woven into it, frayed at the end.
    bx0, bx1, by0, by1 = s(x0 + 4), s(x0 + 9), s(top + 1.5), s(top + 34)
    d = ImageDraw.Draw(lay)
    d.rectangle([bx0, by0, bx1, by1], fill=(168, 40, 36, 255))
    step = s(2.6)
    y = by0 + s(1)
    figure = 0
    while y < by1 - s(3):
        d.rectangle([bx0 + s(0.8), y, bx1 - s(0.8), y + s(1.6)], fill=(232, 222, 200, 255))
        if figure % 2 == 0:  # a bear: a bigger blot; hares: two small ones
            d.ellipse([bx0 + s(1.6), y + s(0.3), bx1 - s(1.6), y + s(1.3)], fill=(140, 30, 30, 255))
        else:
            d.ellipse([bx0 + s(1.4), y + s(0.5), bx0 + s(2.4), y + s(1.1)], fill=(140, 30, 30, 255))
            d.ellipse([bx1 - s(2.4), y + s(0.5), bx1 - s(1.4), y + s(1.1)], fill=(140, 30, 30, 255))
        y += step
        figure += 1
    for k in range(9):  # the frayed end
        x = bx0 + (bx1 - bx0) * k / 8
        d.line([(x, by1), (x + rng.uniform(-s(0.6), s(0.6)), by1 + s(rng.uniform(1.5, 4)))], fill=(200, 170, 150, 255), width=2)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.4)))


REINDEER_COAT = ((26, 24, 30), (72, 66, 70), (128, 120, 122))
REINDEER_PALE = ((70, 72, 86), (136, 138, 150), (196, 198, 206))
REINDEER_LEG = ((14, 12, 16), (40, 36, 40), (82, 76, 78))
ANTLER = ((40, 34, 32), (96, 86, 80), (164, 154, 144))


def reindeer(img, rng, x, base, size, pose="stand", facing=1, antlers=True):
    """A reindeer in the snow, in room units with `base` under its hooves: grey-brown with
    a hump at the shoulders, a pale shaggy mane and belly, a long face, slender dark legs
    with pale socks, and branching antlers. `pose` is "stand", "graze" (muzzle in the
    snow) or "lie"."""
    tone, stroke, touch, curve = A.tone, A.stroke, A.touch, A.curve
    lay = A.new_layer()
    d = A.Painter(lay)
    k, f = size, facing
    P = lambda dx, dy: (x + f * dx * k, base + dy * k)  # noqa: E731
    drop = 4.2 if pose == "lie" else 0.0  # lying, the body sits on the snow
    A.shadow(lay, [(s(x - 9 * k), s(base)), (s(x + 10 * k), s(base)), (s(x + 8 * k), s(base + 1.6 * k)), (s(x - 7 * k), s(base + 1.6 * k))], 80, 4)
    legs = [] if pose == "lie" else [(-5.6, -0.25), (5.2, -0.25), (-4.0, 0.0), (6.4, 0.0)]  # far legs first
    for lx, lt in legs:
        knee = -3.2 if lx > 0 else -3.6
        leg = [P(lx - 0.7, -7.4), P(lx + 0.8, -7.4), P(lx + 0.45 + (0.3 if lx < 0 else 0), knee), P(lx + 0.3, -0.6), P(lx - 0.3, -0.6), P(lx - 0.4, knee)]
        tone(lay, leg, REINDEER_LEG, "flat", light=lt)
        stroke(d, [P(lx - 0.05, -1.5), P(lx, -0.5)], REINDEER_PALE[1], 0.7 * k, 255)  # pale socks
        touch(d, x + f * lx * k, base - 0.25 * k, 0.75 * k, 0.35 * k, (12, 10, 12))  # broad hooves
    if pose == "lie":
        body = A.oval(x - f * 0.6 * k, base - 3.2 * k, 7.4 * k, 3.4 * k)
        tone(lay, body, REINDEER_COAT, "sphere")
        tone(lay, A.oval(x - f * 4.4 * k, base - 2.2 * k, 3.2 * k, 2.2 * k), REINDEER_COAT, "sphere", light=-0.12)  # haunch, hind leg folded
        tone(lay, [P(3.6, -1.0), P(7.6, -1.2), P(8.0, -0.2), P(3.4, -0.1)], REINDEER_LEG, "flat")  # forelegs folded under the chest
        stroke(d, curve(P(-5.6, -1.4), P(0, -0.6), P(5.4, -1.8), 8), REINDEER_PALE[0], 0.9 * k, 150)
        stroke(d, curve(P(-5.6, -5.2), P(0, -6.2), P(4.8, -5.4), 8), REINDEER_COAT[0], 1.0 * k, 140)  # the dark saddle
    else:
        body = curve(P(-8.0, -7.6), P(-6.0, -11.0), P(0.0, -10.8), 10) + curve(P(0.0, -10.8), P(3.0, -12.4), P(5.6, -11.2), 8) + \
            curve(P(7.2, -9.6), P(7.6, -6.8), P(4.4, -5.4), 8) + curve(P(4.4, -5.4), P(-1, -5.0), P(-5.4, -6.0), 8) + curve(P(-5.4, -6.0), P(-8.4, -6.0), P(-8.0, -7.6), 6)
        tone(lay, body, REINDEER_COAT, "sphere")
        tone(lay, A.oval(x - f * 5.4 * k, base - 8.0 * k, 3.2 * k, 3.0 * k), REINDEER_COAT, "sphere", light=-0.05)  # the haunch
        stroke(d, curve(P(-6.4, -6.4), P(0, -5.4), P(5.4, -6.4), 8), REINDEER_PALE[0], 1.0 * k, 150)  # pale belly
        stroke(d, curve(P(-6.0, -8.0), P(-1, -7.2), P(4.0, -8.0), 8), REINDEER_PALE[1], 0.6 * k, 90)  # the pale flank stripe
        stroke(d, curve(P(-6.4, -10.2), P(0, -10.6), P(4.6, -11.4), 8), REINDEER_COAT[0], 1.0 * k, 140)  # the dark saddle
    touch(d, x - f * 8.0 * k, base + (-8.6 + drop) * k, 0.8 * k, 0.6 * k, REINDEER_PALE[2])  # white tail
    # The neck and head: up and alert, or down to the snow.
    if pose == "graze":
        neck = [P(4.6, -11.0), P(7.6, -8.6), P(10.6, -3.6), P(12.4, -2.0), P(11.2, -1.0), P(8.4, -4.0), P(5.4, -7.0)]
        head = [P(10.4, -4.0), P(12.4, -2.6), P(14.2, -0.4), P(13.6, 0.2), P(12.2, -0.4), P(10.2, -1.8)]
        crown = P(11.0, -4.0)
    else:
        neck = [P(4.6, -11.0 + drop), P(6.8, -13.0 + drop), P(8.6, -16.0 + drop), P(10.2, -15.6 + drop), P(9.4, -12.6 + drop), P(8.4, -9.6 + drop), P(6.8, -8.6 + drop)]
        head = [P(8.6, -16.2 + drop), P(10.6, -16.4 + drop), P(14.0, -14.6 + drop), P(14.4, -13.4 + drop), P(13.0, -12.8 + drop), P(9.6, -13.4 + drop)]
        crown = P(9.6, -16.4 + drop)
    tone(lay, neck, REINDEER_PALE, "flat", light=0.0)
    for _ in range(14):  # the shaggy mane hanging under the neck
        i = rng.randrange(len(neck))
        mx, my = neck[i]
        stroke(d, [(mx, my), (mx + rng.uniform(-0.3, 0.3) * k, my + rng.uniform(0.6, 1.4) * k)], REINDEER_PALE[2], 0.25 * k, 170)
    tone(lay, head, REINDEER_COAT, "flat", light=0.1)
    hx, hy = head[3]
    touch(d, hx - f * 0.3 * k, hy + 0.2 * k, 0.7 * k, 0.5 * k, REINDEER_PALE[1])  # the pale muzzle
    ex, ey = head[1]
    touch(d, ex + f * 0.2 * k, ey + 0.8 * k, 0.32 * k, 0.26 * k, (10, 8, 10))  # eye
    touch(d, crown[0] - f * 0.6 * k, crown[1] + 0.2 * k, 0.6 * k, 0.35 * k, REINDEER_COAT[1], 255, -0.6 * f)  # ear
    if antlers:
        for side, lt in ((-1, -0.25), (1, 0.05)):
            cx, cy = crown[0] + side * 0.3 * k, crown[1]
            up = -1 if pose != "graze" else -0.6
            beam = curve((cx, cy), (cx - f * 4.0 * k, cy + up * 5.0 * k), (cx + f * (1.0 + side * 0.6) * k, cy + up * 11.0 * k), 12)
            stroke(d, beam, ANTLER[1] if lt > 0 else ANTLER[0], 0.42 * k, 255)
            for j in (4, 7, 9, 11):  # tines reaching forward off the beam
                bx, by = beam[j]
                stroke(d, [(bx, by), (bx + f * 1.8 * k, by + up * 1.4 * k)], ANTLER[1] if lt > 0 else ANTLER[0], 0.26 * k, 255)
            if side == 1:  # the brow tine, a little shovel over the face
                stroke(d, [(cx, cy - 0.4 * k), (cx + f * 2.2 * k, cy + 0.6 * k)], ANTLER[2], 0.36 * k, 230)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.5)))


def ahkio(img, rng, x0, x1, base):
    """An ahkio: the boat-shaped sled the reindeer pull, pulled up in the snow."""
    lay = A.new_layer()
    d = A.Painter(lay)
    h = (x1 - x0) * 0.22
    hull = A.curve((x0 - 2, base - h * 1.4), (x0 + (x1 - x0) * 0.15, base + h * 0.3), (x1, base - h * 0.1), 12) + \
        A.curve((x1, base - h * 0.1), (x1 - (x1 - x0) * 0.05, base - h * 1.0), (x0 + (x1 - x0) * 0.1, base - h * 0.9), 10)
    A.tone(lay, hull, ((22, 18, 20), (60, 48, 44), (110, 92, 80)), "flat", light=0.05)
    A.stroke(d, A.curve((x0 + 1, base - h * 0.75), (x0 + (x1 - x0) * 0.5, base - h * 0.95), (x1 - 1, base - h * 0.75), 10), (160, 130, 96), 0.4, 220)
    A.shadow(lay, [(s(x0), s(base)), (s(x1 + 4), s(base)), (s(x1 + 2), s(base + 2)), (s(x0 + 2), s(base + 2))], 70, 4)
    snow_cap(lay, int(s(0.8)))
    img.alpha_composite(lay)


def trodden_path(img, rng, pts, width):
    """A path trodden into the snow: a shallow blue trough, scuffed with footprints."""
    line = smooth([(s(x), s(y)) for x, y in pts], 160)
    lay = A.new_layer()
    cv = A.Canvas(lay)
    for i, (x, y) in enumerate(line):
        t = i / len(line)
        A.dab(cv, x, y, s(width) * (0.6 + 0.4 * t), s(width) * 0.18, A.mix(SNOW_MID, SNOW_LO, 0.35) + (90,), 0, 8)
        if i % 4 == 0:
            A.dab(cv, x + rng.uniform(-s(width) * 0.4, s(width) * 0.4), y + rng.uniform(-s(0.5), s(0.5)), s(0.9), s(0.4), (50, 64, 108, 160), 0, 6)
    cv.flush()
    A.paint(img, lay, 0.8)


def tree_row(img, rng, base, hmin, hmax, fade, x0, x1, step=(4, 9)):
    """A far edge of forest: small snowy spruces, close together, blue with distance."""
    x = x0
    while x < x1:
        h = s(rng.uniform(hmin, hmax))
        snowy_spruce(img, rng, x, base + rng.uniform(-s(0.6), s(0.6)), h, h * rng.uniform(0.3, 0.4), fade=fade, depth=1, shadowed=0.5)
        x += s(rng.uniform(*step))


def stone_ring(img, rng, cx, cy, rx, ry):
    lay = A.new_layer()
    d = A.Canvas(lay)
    for a in range(12):
        t = 2 * math.pi * a / 12
        x, y = cx + math.cos(t) * rx, cy + math.sin(t) * ry
        d.ellipse([x - s(2.2), y - s(1.4), x + s(2.2), y + s(1.4)], fill=A.vary((70, 70, 84), rng, 10))
    d.ellipse([cx - rx * 0.8, cy - ry * 0.6, cx + rx * 0.8, cy + ry * 0.6], fill=(30, 22, 22, 255))
    d.flush()
    snow_cap(lay, 3)
    img.alpha_composite(lay)


def camp():
    rng = random.Random(301)
    img = Image.new("RGBA", (W, H()))
    night_gradient(img, s(90))
    sky_only = img.copy()
    far_fells(img, rng, s(88))
    tree_row(img, rng, s(97), 6, 12, 0.55, s(126), s(330))
    snowfield(img, rng, s(92), H())
    trodden_path(img, rng, [(66, 117), (110, 121), (150, 124), (200, 126), (260, 128), (320, 126)], 7)
    trodden_path(img, rng, [(0, 130), (40, 126), (66, 118)], 6)
    for x, base, h in [(s(168), s(97), s(16)), (s(178), s(96), s(11)), (s(300), s(99), s(20))]:
        snowy_spruce(img, rng, x, base, h, h * 0.38, fade=0.4, depth=2)
    stone_ring(img, rng, s(161), s(120), s(12), s(3))
    # The kota, the rack, the sled and the reindeer go on a layer of their own, painted with
    # finer brushwork so their detail survives.
    figures = A.new_layer()
    door = kota(figures, rng, 20, 112, 116, 38)
    drying_rack(figures, rng, 117, 133, 62, 112)
    woodpile(figures, rng, 136, 104, 146, 112)
    for x, base, size, pose, facing in [(258, 101, 1.0, "lie", -1), (292, 99, 0.95, "graze", -1), (238, 107, 1.1, "lie", 1),
                                        (302, 110, 1.1, "stand", -1), (272, 113, 1.15, "graze", 1)]:
        reindeer(figures, rng, x, base, size, pose, facing)
    ahkio(figures, rng, 214, 238, 122)
    front = A.new_layer()
    snowy_spruce(front, rng, s(4), s(152), s(120), s(34), depth=5)
    snowy_spruce(front, rng, s(316), s(152), s(110), s(32), depth=5)
    img.alpha_composite(front)
    open_sky = open_sky_mask(sky_only, Image.alpha_composite(img, figures))
    figures.alpha_composite(front)  # the framing trees stay in front of everything
    light = black()
    glow_pool(light, s(161), s(118), s(46), s(12), FIRELIGHT, 110, s(10))  # the fire on the snow
    glow_pool(light, s(161), s(110), s(26), s(22), FIRELIGHT, 70, s(8))
    glow_pool(light, s(120), s(100), s(30), s(26), FIRELIGHT, 40, s(10))  # on the kota's side and the rack
    kota_light(light, door, s(66), s(38))
    save_night_room(img, rng, "rooms/camp.png", open_sky, light, detail=figures)
    night_sky_layer("rooms/camp_sky.png", 302, 0.66)


# ---------------------------------------------------------------- the lake


def lake():
    rng = random.Random(311)
    img = Image.new("RGBA", (W, H()))
    horizon = s(84)
    night_gradient(img, horizon)
    sky_only = img.copy()
    far_fells(img, rng, horizon - s(4), layers=((44, (58, 78, 126), (150, 190, 204)), (26, (46, 62, 108), (110, 150, 170)), (12, (36, 50, 92), (80, 116, 140))))
    tree_row(img, rng, horizon + s(2), 4, 9, 0.6, -s(4), s(250), step=(2.5, 6))
    # The ice: dark where the wind has polished it, holding a dim mirror of the sky, with
    # long drifts of snow across it.
    lay = A.new_layer()
    d = ImageDraw.Draw(lay)
    for y in range(horizon + s(3), H()):
        t = (y - horizon) / (H() - horizon)
        d.line([(0, y), (W, y)], fill=A.mix((58, 80, 120), (24, 34, 66), t ** 0.7) + (255,))
    cv = A.Canvas(lay)
    for _ in range(2200):
        x, y = rng.uniform(0, W), rng.uniform(horizon + s(3), H())
        t = (y - horizon) / (H() - horizon)
        band = 0.5 + 0.5 * math.sin(y * 0.05 + math.sin(x * 0.004) * 3)
        col = A.mix((70, 96, 140), SNOW_HI, band * 0.8) if rng.random() < 0.6 else A.mix((30, 44, 80), (90, 120, 160), rng.random())
        A.dab(cv, x, y, s(rng.uniform(3, 12)) * (0.4 + t), s(rng.uniform(0.25, 0.5)) * (0.4 + t), col + (150,), rng.uniform(-0.03, 0.03), 6)
    cv.flush()
    A.paint(img, lay, 0.5)
    # The fishing hole, skinned with new ice, and a ridge of chipped ice around it.
    hole = A.new_layer()
    hd = A.Canvas(hole)
    hd.ellipse([s(144), s(116), s(170), s(123)], fill=(14, 20, 40, 255))
    hd.ellipse([s(146), s(117), s(168), s(122)], fill=(36, 56, 92, 255))
    for _ in range(40):
        t = rng.uniform(0, 2 * math.pi)
        x, y = s(157) + math.cos(t) * s(15), s(119.5) + math.sin(t) * s(4.4)
        A.dab(hd, x, y, s(rng.uniform(1.2, 2.2)), s(rng.uniform(0.7, 1.1)), A.mix(SNOW_HI, SNOW_MID, rng.random()) + (255,), rng.uniform(-0.3, 0.3), 9)
    hd.flush()
    img.alpha_composite(hole)
    # The far shore on the right: snowy spruces and rocks; a snowbank in front on the left.
    for x, base, h in [(s(276), s(104), s(60)), (s(296), s(108), s(84)), (s(312), s(110), s(70)), (s(258), s(100), s(30))]:
        snowy_spruce(img, rng, x, base, h, h * 0.34, depth=4, fade=0.1)
    boulder(img, rng, s(262), s(102), s(290), s(114))
    snowfield(img, rng, s(126), H(), pts=[(0, H()), (0, s(126)), (s(40), s(128)), (s(90), s(134)), (s(120), s(144))], strokes=1500)
    lay = A.new_layer()
    d = ImageDraw.Draw(lay)
    for _ in range(26):  # dead reeds poking through the snowbank
        x = rng.uniform(s(4), s(80))
        y = s(128) + rng.uniform(0, s(10))
        d.line([(x, y), (x + rng.uniform(-s(2), s(2)), y - rng.uniform(s(5), s(13)))], fill=A.mix((60, 58, 66), (110, 104, 100), rng.random()) + (255,), width=2)
    img.alpha_composite(lay)
    open_sky = open_sky_mask(sky_only, img)
    light = black()
    glow_pool(light, s(160), s(108), s(160), s(12), (60, 90, 140), 40, s(20))  # starlight on the ice
    save_night_room(img, rng, "rooms/lake.png", open_sky, light)
    night_sky_layer("rooms/lake_sky.png", 312, 0.58)


# ---------------------------------------------------------------- the forest


def log_cabin(img, rng, x0, x1, ground, wall_h, roof_h):
    """Jussi's cabin, in room units: round grey logs notched at the corners, a roof bowed
    under a deep load of snow with icicles along the eaves, a small four-paned window with
    lamplight behind it, a barred plank door, pelts drying under the eaves and coils of
    snare wire on pegs. Returns the window's rectangle (pixels), for its light."""
    tone, stroke, touch = A.tone, A.stroke, A.touch
    lay = A.new_layer()
    d = A.Painter(lay)
    top = ground - wall_h
    log = 3.2
    logs = ((40, 38, 46), (86, 82, 88), (140, 136, 140))
    y = ground - log
    while y > top - 0.5:
        tone(lay, [(x0, y), (x1, y), (x1, y + log), (x0, y + log)], logs, "flat", light=-0.1 + 0.15 * rng.random())
        stroke(d, [(x0, y + 0.5), (x1, y + 0.5)], logs[2], 0.45, 150)  # the round top of each log, catching light
        stroke(d, [(x0, y + log - 0.2), (x1, y + log - 0.2)], (16, 14, 20), 0.5, 220)  # the dark seam beneath
        for _ in range(int((x1 - x0) / 6)):  # cracks and knots in the wood
            x = rng.uniform(x0 + 2, x1 - 2)
            stroke(d, [(x, y + log * 0.45), (x + rng.uniform(2, 6), y + log * 0.5)], logs[0], 0.18, 140)
        for end in (x0, x1):  # log ends sticking out past the corners, with their rings
            tone(lay, A.oval(end + (-1.4 if end == x0 else 1.4), y + log / 2, 1.9, log / 2), ((70, 60, 56), (130, 118, 108), (184, 170, 156)), "sphere")
            touch(d, end + (-1.4 if end == x0 else 1.4), y + log / 2, 0.5, 0.45, (60, 50, 46), 200)
        y -= log
    gable = [(x0 - 1, top), ((x0 + x1) / 2, top - roof_h * 0.82), (x1 + 1, top)]
    tone(lay, gable, logs, "flat", light=-0.25)
    chimney = (x1 - 28, top - roof_h * 0.95, x1 - 22, top - roof_h * 0.35)
    tone(lay, [(chimney[0], chimney[1]), (chimney[2], chimney[1]), (chimney[2], chimney[3]), (chimney[0], chimney[3])],
         ((40, 36, 40), (80, 72, 74), (130, 120, 118)), "cylinder")
    roof = [(x0 - 7, top + 1.5), ((x0 + x1) / 2, top - roof_h), (x1 + 7, top + 1.5)]
    snow = A.curve(roof[0], (roof[0][0] + 6, top - roof_h * 0.62), roof[1], 12) + A.curve(roof[1], (roof[2][0] - 6, top - roof_h * 0.62), roof[2], 12) + \
        [(x1 + 7, top + 3.4), (x0 - 7, top + 3.4)]
    tone(lay, snow, ((70, 86, 130), (150, 168, 204), (226, 236, 246)), "flat", light=0.1)
    stroke(d, [(x0 - 7, top + 3.2), (x1 + 7, top + 3.2)], (60, 72, 114), 0.8, 220)  # the overhanging lip in shadow
    for _ in range(22):  # icicles
        x = rng.uniform(x0 - 5, x1 + 5)
        L = rng.uniform(1.2, 4.0)
        d.polygon(A.pts([(x - 0.35, top + 3.4), (x + 0.35, top + 3.4), (x, top + 3.4 + L)]), fill=(196, 214, 236, 255))
    tone(lay, [(chimney[0] - 0.6, chimney[1] - 1.6), (chimney[2] + 0.6, chimney[1] - 1.6), (chimney[2] + 0.6, chimney[1]), (chimney[0] - 0.6, chimney[1])],
         ((120, 140, 180), (190, 206, 230), (236, 242, 250)), "flat")  # snow on the chimney
    wx0, wy0, wx1, wy1 = x0 + 18, top + 10, x0 + 30, top + 19
    tone(lay, [(wx0, wy0), (wx1, wy0), (wx1, wy1), (wx0, wy1)], ((90, 40, 20), (190, 110, 50), (255, 200, 120)), "flat", light=0.1)
    for seg in ([(wx0, wy0), (wx1, wy0), (wx1, wy1), (wx0, wy1), (wx0, wy0)], [((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], [(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)]):
        stroke(d, seg, (38, 30, 30), 0.6, 255)
    stroke(d, [(wx0 - 1, wy1 + 0.6), (wx1 + 1, wy1 + 0.6)], SNOW_HI, 0.8, 255)  # snow on the sill
    dx0, dx1 = x0 + 46, x0 + 59
    tone(lay, [(dx0, top + 7), (dx1, top + 7), (dx1, ground), (dx0, ground)], ((40, 30, 28), (82, 64, 54), (130, 106, 88)), "flat")
    for k in range(1, 4):
        x = dx0 + (dx1 - dx0) * k / 4
        stroke(d, [(x, top + 7.4), (x, ground)], (30, 22, 20), 0.25, 200)
    stroke(d, [(dx0 - 1, top + 16), (dx1 + 1, top + 18)], (54, 40, 32), 1.0, 255)  # the bar
    for k, px in enumerate((x0 + 64, x0 + 72, x0 + 81)):  # pelts drying under the eaves
        pelt = [(px, top + 3.6), (px + 4.4, top + 3.6), (px + 5.2, top + 9), (px + 4.0, top + 14), (px + 2.2, top + 16.5), (px + 0.4, top + 14), (px - 0.8, top + 9)]
        tone(lay, pelt, (((60, 40, 30), (120, 84, 56), (176, 136, 96)), ((70, 66, 64), (140, 134, 128), (204, 198, 190)), ((80, 50, 30), (150, 96, 56), (210, 150, 96)))[k], "flat")
        for _ in range(16):
            fx, fy = rng.uniform(px, px + 4.4), rng.uniform(top + 4, top + 14)
            stroke(d, [(fx, fy), (fx + rng.uniform(-0.3, 0.3), fy + 1.2)], (40, 30, 26), 0.12, 120)
    for k in range(4):  # coils of snare wire on pegs
        cx, cy = x1 - 13 + (k % 2) * 6.5, top + 14 + (k // 2) * 9
        stroke(d, [(cx, cy - 3.4), (cx, cy - 2.4)], (60, 46, 36), 0.6, 255)
        for r in (2.4, 1.9, 1.4):
            ring = A.oval(cx + rng.uniform(-0.2, 0.2), cy, r, r * 1.15, 20)
            stroke(d, ring + ring[:1], WIRE[1], 0.15, 220)
        touch(d, cx - 1.6, cy - 1.0, 0.3, 0.3, WIRE[2], 230)
    snow_cap(lay, int(s(0.6)))
    A.shadow(img, [(s(x0), s(ground)), (s(x1 + 10), s(ground)), (s(x1 + 16), s(ground + 3)), (s(x0 + 4), s(ground + 3))], 90, 6)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.5)))
    return (s(wx0), s(wy0), s(wx1), s(wy1))


def woodpile(img, rng, x0, y0, x1, y1):
    lay = A.new_layer()
    d = A.Canvas(lay)
    for row in range(int((y1 - y0) / 3)):
        for col in range(int((x1 - x0) / 3)):
            x, y = s(x0 + col * 3 + (row % 2) * 1.5), s(y1 - row * 3 - 1.5)
            d.ellipse([x - s(1.5), y - s(1.4), x + s(1.5), y + s(1.4)], fill=A.vary((120, 100, 80), rng, 12))
            d.ellipse([x - s(0.6), y - s(0.5), x + s(0.6), y + s(0.5)], fill=(80, 64, 50, 255))
    d.flush()
    snow_cap(lay, int(s(1.5)))
    img.alpha_composite(lay)


def forest():
    rng = random.Random(321)
    img = Image.new("RGBA", (W, H()))
    night_gradient(img, s(100))
    sky_only = img.copy()
    # Deep forest: rows of snowy spruces, bluer and softer with distance.
    rows = [(s(102), 30, 56, 0.7, 7, 0.0), (s(106), 44, 80, 0.45, 11, 0.25), (s(112), 60, 116, 0.2, 20, 0.4)]
    for row, (base, hmin, hmax, fade, step, shadowed) in enumerate(rows):
        x = rng.uniform(-s(6), s(4))
        while x < W + s(10):
            h = s(rng.uniform(hmin, hmax))
            snowy_spruce(img, rng, x, base + rng.uniform(-s(1), s(1)), h, h * rng.uniform(0.28, 0.4), fade=fade, depth=3, shadowed=shadowed * rng.random())
            x += s(rng.uniform(step * 0.6, step * 1.4))
        if row < 2:  # frost haze hanging between the trees, deeper into the forest
            A.mist(img, rng, base / A.SCALE - 6, 26, 70 - row * 25, color=(70, 92, 140))
    snowfield(img, rng, s(108), H(), strokes=4000)
    win = log_cabin(img, rng, 200, 302, 114, 40, 26)
    woodpile(img, rng, 182, 104, 198, 114)
    light = black()
    # The tracks go in before the trees in front, which hide them (and their glow).
    tracks = fox_tracks(img, light, rng, [(60, 142), (120, 134), (190, 127), (250, 123), (318, 119)], 30)
    front = A.new_layer()
    snowy_spruce(front, rng, s(14), s(152), s(150), s(40), depth=5)
    snowy_spruce(front, rng, s(46), s(150), s(120), s(30), depth=5, shadowed=0.2)
    snowy_spruce(front, rng, s(130), s(140), s(90), s(24), depth=4, shadowed=0.1)
    img.alpha_composite(front)
    behind = ImageChops.invert(front.getchannel("A").point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(5)))
    light = screen(light, Image.composite(tracks, black(), behind))
    open_sky = open_sky_mask(sky_only, img)
    wl = Image.new("RGBA", light.size)
    ImageDraw.Draw(wl).rectangle(win, fill=(255, 160, 80, 255))
    light.alpha_composite(wl.filter(ImageFilter.GaussianBlur(s(0.6))))
    light.alpha_composite(wl.filter(ImageFilter.GaussianBlur(s(8))))
    glow_pool(light, (win[0] + win[2]) / 2, s(118), s(16), s(4), FIRELIGHT, 60, s(5))
    save_night_room(img, rng, "rooms/forest.png", open_sky, light)
    night_sky_layer("rooms/forest_sky.png", 322, 0.72, aurora=0.15)


# ---------------------------------------------------------------- the fell top

# The snow-figures, in room units: piled snow in the shapes of a sitting hare, an owl with
# folded wings, and a bear rearing up. Each is a list of ovals (cx, cy, rx, ry[, tilt]).
HARE = [(57, 94, 16, 18), (54, 80, 12, 12), (61, 62, 9.5, 8.5), (56, 47, 2.6, 10, -0.35), (63, 46, 2.6, 10, -0.1), (68, 64, 3, 2.5),
        (44, 104, 6, 6), (70, 106, 6, 5)]
OWL = [(145, 86, 15, 25), (145, 64, 14, 14), (145, 50, 14, 11.5), (136.5, 38, 2.2, 6.5, -0.5), (153.5, 38, 2.2, 6.5, 0.5),
       (145, 108, 12, 4)]
BEAR = [(244, 92, 17, 20, -0.15), (238, 74, 13, 13), (227, 56, 8.5, 8), (217.5, 58.5, 5, 3.4, 0.15), (230.5, 47.5, 2.6, 2.6),
        (219, 69, 3.6, 9, 0.95), (225, 76, 3.8, 9, 1.15), (234, 108, 6, 5), (253, 108, 7, 5)]
FACES = {  # the features the wind left in the snow: hollows (cx, cy, r) and creases (points)
    "hare": ([(64.5, 60.5, 1.3), (69.5, 64.5, 0.9)], [[(64, 84), (66, 92), (64, 100)], [(50, 70), (46, 84), (48, 100)]]),
    "owl": ([(140, 50, 3.2), (150, 50, 3.2), (145, 56, 1.1)], [[(133, 66), (131, 84), (136, 104)], [(157, 66), (159, 84), (154, 104)],
                                                           [(140, 66), (145, 70), (150, 66)]]),
    "bear": ([(224, 54, 1.0), (213, 57.5, 1.3)], [[(227, 64), (235, 66), (240, 76)], [(236, 98), (244, 104), (252, 100)]]),
}


def snow_figure(img, rng, blobs, trunk_x, top_y, face):
    """A snow-figure: a spruce under its load, a dark tip poking out of the top, boughs
    showing at the bottom, and the hollows and creases that make the shape an animal."""
    lay = A.new_layer()
    d = ImageDraw.Draw(lay)
    d.polygon([(s(trunk_x - 1), s(top_y + 4)), (s(trunk_x), s(top_y - 3)), (s(trunk_x + 1), s(top_y + 4))], fill=(14, 24, 28, 255))
    img.alpha_composite(lay)
    m = snow_mass(img, rng, blobs, needles=0.5)
    x0, y0, x1, y1 = m.getbbox()
    A.shadow(img, [(x0, y1 - s(2)), (x1 + s(8), y1 - s(1)), (x1 + s(4), y1 + s(3)), (x0 + s(4), y1 + s(3))], 60, 6)
    marks = A.new_layer()
    md = A.Painter(marks)
    hollows, creases = FACES[face]
    for cx, cy, r in hollows:  # hollows in deep blue shadow, lit along their lower rim
        A.tone(marks, A.oval(cx, cy, r, r * 0.9), (SNOW_LO, A.mix(SNOW_LO, SNOW_MID, 0.4), SNOW_MID), "sphere", light=-0.2)
        A.stroke(md, A.curve((cx - r * 0.8, cy + r * 0.5), (cx, cy + r * 1.1), (cx + r * 0.8, cy + r * 0.5), 6), SNOW_HI, 0.35, 200)
    for line in creases:
        A.stroke(md, A.curve(*line, 10), A.mix(SNOW_LO, SNOW_MID, 0.3), 0.8, 150)
        A.stroke(md, A.curve(*[(x - 0.7, y) for x, y in line], 10), SNOW_HI, 0.4, 140)
    for _ in range(18):  # spruce boughs poking out low down, under the snow
        x = rng.uniform(x0 + s(2), x1 - s(2))
        y = y1 - s(rng.uniform(2, 8))
        if m.getpixel((int(x), int(y))) < 200:
            continue
        side = -1 if x < (x0 + x1) / 2 else 1
        md.polygon([(x, y), (x + side * s(rng.uniform(2, 4)), y + s(rng.uniform(0.4, 1.2))), (x, y + s(0.9))], fill=(12, 22, 30, 230))
    marks.putalpha(ImageChops.multiply(marks.getchannel("A"), m.filter(ImageFilter.MaxFilter(9))))
    img.alpha_composite(marks.filter(ImageFilter.GaussianBlur(0.8)))
    return m


def lichen_and_frost(img, rng, box, mask, frost=0.5):
    """Lichen crusting the stone in pale rosettes, and frost glittering in its cracks."""
    lay = A.new_layer()
    cv = A.Canvas(lay)
    x0, y0, x1, y1 = box
    for _ in range(int((x1 - x0) * (y1 - y0) / 30)):
        x, y = rng.uniform(s(x0), s(x1)), rng.uniform(s(y0), s(y1))
        if mask.getpixel((min(W - 1, int(x)), min(H() - 1, int(y)))) < 200:
            continue
        if rng.random() < 0.6:
            col = rng.choice([(110, 130, 104), (150, 150, 120), (140, 112, 84)])
            A.dab(cv, x, y, s(rng.uniform(0.4, 1.1)), s(rng.uniform(0.3, 0.8)), col + (90,), rng.uniform(0, 3), 7)
        elif rng.random() < frost:
            A.dab(cv, x, y, s(0.25), s(0.25), (220, 236, 255, 230), 0, 5)
    cv.flush()
    img.alpha_composite(lay)


def den_rocks(img, rng):
    """The den's mouth among the rocks on the right: a deep cleft under a great boulder,
    icicles hanging from its lip, a little spruce growing out of the rock above, lichen and
    frost on the stone, and snow drifted round it all."""
    rocks = A.new_layer()
    rough_rock(rocks, rng, 280, 70, 336, 106, 0.1)  # the great boulder the den runs under
    cleft = Image.new("RGBA", (W, H()))
    cd = ImageDraw.Draw(cleft)
    outline = [(s(x), s(y)) for x, y in [(288, 125), (290, 112), (294, 103), (300, 99), (306, 102), (310, 110), (312, 125)]]
    cd.polygon(outline, fill=(14, 16, 30, 255))
    inner = [(s(x), s(y)) for x, y in [(292, 125), (295, 109), (300, 104), (305, 108), (308, 125)]]
    cd.polygon(inner, fill=(3, 4, 10, 255))  # deeper in, darker
    rocks.alpha_composite(cleft.filter(ImageFilter.GaussianBlur(s(0.6))))
    rough_rock(rocks, rng, 262, 94, 292, 126, 0.06)
    rough_rock(rocks, rng, 308, 92, 340, 126, 0.06)
    rough_rock(rocks, rng, 276, 116, 288, 127, 0.25)
    lichen_and_frost(rocks, rng, (262, 70, 330, 126), rocks.getchannel("A").point(lambda v: 255 if v > 250 else 0))
    img.alpha_composite(rocks)
    snowy_spruce(img, rng, s(318), s(76), s(26), s(9), depth=3)
    ice = A.new_layer()
    idr = ImageDraw.Draw(ice)
    for _ in range(12):  # icicles along the lip of the cleft
        x = rng.uniform(s(290), s(311))
        top = s(100) + abs(x - s(300)) * 0.35
        L = s(rng.uniform(1.5, 5))
        idr.polygon([(x - s(0.5), top), (x + s(0.5), top), (x, top + L)], fill=(176, 200, 236, 255))
        idr.line([(x - s(0.2), top), (x - s(0.1), top + L * 0.7)], fill=(236, 244, 255, 255), width=1)
    img.alpha_composite(ice.filter(ImageFilter.GaussianBlur(0.6)))
    lip = A.new_layer()  # snow overhanging the mouth
    lv = A.Canvas(lip)
    for _ in range(60):
        x = rng.uniform(s(286), s(314))
        A.dab(lv, x, s(99.5) + abs(x - s(300)) * 0.3 + rng.uniform(-s(0.6), s(0.6)), s(rng.uniform(1.4, 3)), s(rng.uniform(0.6, 1.1)),
              A.mix(SNOW_MID, SNOW_HI, rng.random()) + (255,), 0, 8)
    lv.flush()
    img.alpha_composite(lip)


def fell_scene(rng):
    img = Image.new("RGBA", (W, H()))
    night_gradient(img, s(100))
    sky_only = img.copy()
    far_fells(img, rng, s(104), layers=((34, (60, 80, 128), (140, 182, 196)), (20, (46, 62, 108), (104, 144, 164)), (9, (36, 50, 92), (80, 116, 140))))
    snowfield(img, rng, s(100), H(), pts=[(0, H()), (0, s(108)), (s(60), s(104)), (s(140), s(108)), (s(220), s(102)), (s(320), s(106)), (s(320), H())],
              lit=(220, 234, 242), mid=(126, 150, 190))
    for x, base, h in [(s(100), s(108), s(16)), (s(108), s(108), s(11)), (s(186), s(104), s(14)), (s(196), s(104), s(9))]:
        snowy_spruce(img, rng, x, base, h, h * 0.36, fade=0.3, depth=2)
    snow_figure(img, rng, HARE, 58, 38, "hare")
    snow_figure(img, rng, OWL, 145, 30, "owl")
    snow_figure(img, rng, BEAR, 236, 42, "bear")
    den_rocks(img, rng)
    return img, sky_only


def fell():
    rng = random.Random(331)
    img, sky_only = fell_scene(rng)
    light = black()
    light = screen(light, fox_tracks(img, light, rng, [(20, 140), (100, 134), (176, 124), (240, 120), (290, 120)], 26, size=1.4))
    open_sky = open_sky_mask(sky_only, img)
    save_night_room(img, rng, "rooms/fell.png", open_sky, light)
    night_sky_layer("rooms/fell_sky.png", 332, 0.72, aurora=0.3)


# ---------------------------------------------------------------- the den


def den():
    """Inside the den under the rocks: boulders piled into walls and a roof, crusted with
    lichen, frost glittering near the mouth, roots hanging through, and on the left the
    opening, where snow has drifted in and the night shows blue, throwing a shaft of cold
    light across the floor to the fox's nest of grass, feathers and old bones."""
    rng = random.Random(341)
    img = Image.new("RGBA", (W, H()))
    d = ImageDraw.Draw(img)
    for y in range(H()):
        d.line([(0, y), (W, y)], fill=A.mix((12, 14, 24), (6, 6, 12), y / H()) + (255,))
    # The floor: packed earth and gravel, needles blown in.
    floor = A.new_layer()
    fv = A.Canvas(floor)
    for _ in range(1600):
        x, y = rng.uniform(0, W), rng.uniform(s(112), H())
        near = max(0.0, 1 - x / s(180))
        A.dab(fv, x, y, s(rng.uniform(0.5, 1.6)), s(rng.uniform(0.3, 0.7)), A.mix((20, 18, 22), (80, 84, 104), near * rng.random()) + (200,), rng.uniform(0, 3), 6)
    fv.flush()
    A.paint(img, floor, 0.4)
    rocks = []
    for _ in range(80):
        x = rng.uniform(20, 340)
        y = rng.uniform(-14, 70) if rng.random() < 0.7 else rng.uniform(60, 122)
        if 150 < x < 270 and 50 < y < 114:
            continue  # leave the back of the den open and dark
        rocks.append((y, x, rng.uniform(10, 26)))
    walls = A.new_layer()
    for y, x, r in sorted(rocks):
        near = max(0.0, 1 - (x - 30) / 170) ** 1.3
        pal = (A.mix((4, 4, 10), ROCK[0], near), A.mix((10, 12, 20), ROCK[1], near * 0.9), A.mix((18, 20, 32), (110, 118, 146), near * 0.85))
        rough_rock(walls, rng, x - r, y - r * 0.7, x + r, y + r * 0.7, 0, pal)
    img.alpha_composite(walls)
    lichen_and_frost(img, rng, (20, 0, 200, 124), walls.getchannel("A"), frost=0.12)
    back = Image.new("RGBA", (W, H()), (2, 2, 6, 0))
    bm = Image.new("L", (W, H()), 0)
    ImageDraw.Draw(bm).ellipse([s(150), s(46), s(280), s(118)], fill=200)
    back.putalpha(bm.filter(ImageFilter.GaussianBlur(s(14))))
    img.alpha_composite(back)
    # The opening: the night sky and starlit snow beyond, icicles along its top.
    op = smooth([(0, s(26)), (s(12), s(22)), (s(26), s(30)), (s(34), s(56)), (s(36), s(90)), (s(30), s(124)), (s(18), s(134)), (0, s(136))], 60)
    sky = Image.new("RGBA", (W, H()))
    night_gradient(sky, s(96))
    sky.alpha_composite(star_layer(rng, W, H(), 120, s(80), glints=False))
    far_fells(sky, rng, s(88), layers=((14, (56, 76, 124), (130, 170, 186)),))
    snow = Image.new("RGBA", (W, H()))
    snowfield(snow, rng, s(88), H(), strokes=700)
    sky.alpha_composite(snow)
    sky.putalpha(mask_of(op))
    img.alpha_composite(sky)
    ice = A.new_layer()
    idr = ImageDraw.Draw(ice)
    for _ in range(14):
        x = rng.uniform(s(3), s(30))
        y = s(23) + (x / s(30)) * s(8)
        L = s(rng.uniform(2, 7))
        idr.polygon([(x - s(0.5), y), (x + s(0.5), y), (x, y + L)], fill=(150, 176, 220, 230))
        idr.line([(x - s(0.15), y), (x, y + L * 0.7)], fill=(230, 240, 255, 255), width=1)
    img.alpha_composite(ice.filter(ImageFilter.GaussianBlur(0.6)))
    snowfield(img, rng, s(110), H(), pts=[(0, H()), (0, s(116)), (s(36), s(114)), (s(70), s(124)), (s(110), s(144))], strokes=900)
    # The nest: a hollow lined with dry grass, a few feathers, old bones by the wall.
    nest = A.new_layer()
    nd = ImageDraw.Draw(nest)
    A.dab(nd, s(212), s(121), s(26), s(4), (16, 14, 14, 220), 0, 16)
    for _ in range(1100):
        x, y = s(212) + rng.gauss(0, s(13)), s(120.5) + rng.gauss(0, s(2.4))
        a = rng.uniform(-0.6, 0.6) + (math.pi if rng.random() < 0.5 else 0)
        L = s(rng.uniform(1.5, 4))
        nd.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L * 0.35)], fill=A.mix((60, 52, 40), (150, 132, 96), rng.random()) + (230,), width=2)
    for fx, fy, fa in ((236, 118, 0.3), (190, 123, -0.4), (228, 124, 2.6)):  # feathers, ptarmigan white
        x, y = s(fx), s(fy)
        nd.line([(x, y), (x + math.cos(fa) * s(3), y + math.sin(fa) * s(1.2))], fill=(210, 210, 214, 255), width=int(s(0.7)))
        nd.line([(x, y), (x + math.cos(fa) * s(3), y + math.sin(fa) * s(1.2))], fill=(120, 120, 130, 255), width=1)
    for bx, by in ((256, 124), (262, 126), (170, 126)):  # small old bones
        nd.line([(s(bx), s(by)), (s(bx + 4), s(by - 0.6))], fill=(176, 168, 150, 255), width=int(s(0.6)))
        for ex in (bx, bx + 4):
            nd.ellipse([s(ex) - s(0.5), s(by - 0.3) - s(0.5), s(ex) + s(0.5), s(by - 0.3) + s(0.5)], fill=(186, 178, 160, 255))
    img.alpha_composite(nest.filter(ImageFilter.GaussianBlur(0.6)))
    roots = A.new_layer()
    rd = ImageDraw.Draw(roots)
    for _ in range(22):
        x = rng.uniform(s(110), s(250))
        pts = [(x, 0)]
        for j in range(int(rng.uniform(6, 13))):
            x += rng.uniform(-s(1.6), s(1.6))
            pts.append((x, pts[-1][1] + s(rng.uniform(2.5, 4.5))))
            if rng.random() < 0.35:
                rx, ry = pts[-1]
                rd.line([(rx, ry), (rx + rng.uniform(-s(4), s(4)), ry + s(rng.uniform(2, 5)))], fill=(46, 38, 34, 255), width=1)
        rd.line(pts, fill=A.mix((26, 20, 18), (60, 50, 42), rng.random()) + (255,), width=max(2, int(s(rng.uniform(0.4, 1.0)))))
        rd.line([(px - 1, py) for px, py in pts], fill=(70, 66, 70, 255), width=1)
        if rng.random() < 0.4:  # a bead of frost at the tip
            ex, ey = pts[-1]
            rd.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=(200, 220, 255, 255))
    img.alpha_composite(roots.filter(ImageFilter.GaussianBlur(0.7)))
    light = black()
    glow_pool(light, s(20), s(90), s(70), s(60), (70, 100, 170), 80, s(26))  # night coming in at the mouth
    shaft = Image.new("RGBA", light.size)  # its cold light laid across the floor
    ImageDraw.Draw(shaft).polygon([(s(20), s(40)), (s(36), s(60)), (s(190), s(130)), (s(120), s(144)), (s(10), s(130))], fill=(60, 90, 150, 70))
    light.alpha_composite(shaft.filter(ImageFilter.GaussianBlur(s(8))))
    save_night_room(img, rng, "rooms/den.png", None, light)


# ---------------------------------------------------------------- the fox's fire

# ---- the fox itself: an arctic fox in its thick white winter coat, painted like the other
# figures, in the cold of the night; only its tail burns.

ARCTIC = ((64, 72, 104), (166, 174, 202), (236, 238, 248))
ARCTIC_DULL = ((50, 52, 64), (122, 122, 134), (188, 188, 196))  # the fox gone cold in its den


def paint_sprite(draw, seed, detail=2, brushes=A.FIGURE_BRUSHES):
    """Like make_art's painted_figure, but returns the painting: drawn large with oil
    brushwork, then shrunk. It comes out SCALE * detail pixels per unit."""
    base = A.SCALE
    A.SCALE = base * detail * A.SUPERSAMPLE
    try:
        img = draw()
    finally:
        A.SCALE = base
    img = A.oil_paint_sprite(img, random.Random(seed), base * detail * A.SUPERSAMPLE, brushes)
    img = img.resize((img.width // A.SUPERSAMPLE, img.height // A.SUPERSAMPLE), Image.LANCZOS)
    img.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))
    return img


def fur_edge(d, outline, palette, rng, count=60, length=0.9):
    """Tufts of thick winter fur standing out along a form's edge."""
    for _ in range(count):
        i = rng.randrange(len(outline) - 1)
        (x0, y0), (x1, y1) = outline[i], outline[i + 1]
        f = rng.random()
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        A.stroke(d, [(x, y), (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-length, length * 0.3))], palette[rng.randrange(1, 3)], 0.22, 170)


def bushy_tail(img, d, rng, upper, lower, palette=ARCTIC, light=0.0):
    """An arctic fox's huge brush: a plume of fur, tufted all along its edge."""
    top, bottom = A.curve(*upper, 16), A.curve(*lower, 16)[::-1]
    A.tone(img, top + bottom[::-1], palette, "flat", light=light)
    for _ in range(160):  # long fur running down the brush, lighter along the top
        i = rng.randrange(len(top) - 1)
        f = rng.random()
        (ux, uy), (lx, ly) = top[i], bottom[i]
        x, y = ux + (lx - ux) * f, uy + (ly - uy) * f
        nx, ny = top[i + 1][0] - ux, top[i + 1][1] - uy
        L = math.hypot(nx, ny) or 1
        col = palette[2] if f < 0.35 else palette[1] if f < 0.75 else palette[0]
        A.stroke(d, [(x, y), (x + nx / L * 1.6, y + ny / L * 1.6)], col, 0.3, 120)
    fur_edge(d, top + bottom[::-1], palette, rng, 110, 1.0)


def fur_fill(d, rng, cx, cy, rx, ry, palette, count=80, angle=0.0):
    """Fur laid over a rounded form: short strokes running along it, lighter on top and
    darker underneath."""
    for _ in range(count):
        a, r = rng.uniform(0, 2 * math.pi), rng.random() ** 0.5
        x, y = cx + math.cos(a) * rx * r * 0.9, cy + math.sin(a) * ry * r * 0.9
        f = (y - (cy - ry)) / (2 * ry)
        col = palette[2] if f < 0.4 else palette[1] if f < 0.75 else palette[0]
        L = 1.0 + rng.random()
        A.stroke(d, [(x, y), (x + math.cos(angle) * L, y + math.sin(angle) * L + 0.3)], col, 0.22, 110)


def fox_standing():
    """The fox standing in the snow, facing left, head up, looking back at whoever follows:
    an arctic fox in its winter coat, compact and round, short-legged, small-eared, with a
    huge brush curling up behind. In a 60x30 box; the fire on its tail is added after."""
    tone, touch, stroke, oval = A.tone, A.touch, A.stroke, A.oval
    img, d = A.sprite(60, 30)
    rng = random.Random(611)
    bushy_tail(img, d, rng, ((37, 15.6), (45, 4.6), (57, 3.0)), ((57, 3.0), (57, 17.6), (37.6, 22)), light=-0.04)
    tone(img, [(16.8, 22), (18.8, 22), (18.6, 28.6), (16.8, 28.6)], ARCTIC, "flat", light=-0.3)  # far legs
    tone(img, [(32.2, 22), (34.6, 22), (35.0, 28.6), (33.2, 28.6)], ARCTIC, "flat", light=-0.3)
    body = oval(25.6, 19.6, 10.2, 6.3)
    tone(img, body, ARCTIC, "sphere")
    fur_edge(d, body, ARCTIC, rng, 90, 0.9)
    fur_fill(d, rng, 25.6, 19.6, 10.2, 6.3, ARCTIC, 160, math.pi)
    tone(img, oval(32.4, 20.6, 5.0, 5.0), ARCTIC, "sphere", light=-0.06)  # haunch
    fur_fill(d, rng, 32.4, 20.6, 5.0, 5.0, ARCTIC, 50, math.pi * 0.6)
    tone(img, [(31.4, 23), (35.0, 22.4), (35.8, 26), (35.2, 28.6), (33.4, 28.6), (33.8, 26)], ARCTIC, "flat", light=-0.04)
    chest = [(19.6, 14.4), (15.0, 11.6), (12.8, 15.2), (14.2, 22.6), (18.6, 24.2), (21.6, 19.6)]
    tone(img, chest, ARCTIC, "flat", light=0.12)
    fur_edge(d, chest[2:5], ARCTIC, rng, 40, 1.3)  # the ruff
    fur_fill(d, rng, 16.6, 17.4, 3.6, 5.0, ARCTIC, 50, math.pi / 2)
    tone(img, [(15.0, 22.0), (17.4, 22.4), (17.2, 28.6), (15.2, 28.6)], ARCTIC, "flat", light=0.05)  # near foreleg
    for x in (17.2, 33.0, 15.6, 33.6):  # big furry paws, pointing forward (left) like the fox
        touch(d, x, 28.6, 1.4, 0.65, ARCTIC[2], 255)
    head = oval(12.6, 11.4, 4.7, 4.1)
    tone(img, head, ARCTIC, "sphere", light=0.08)
    fur_edge(d, head[8:20], ARCTIC, rng, 30, 0.7)  # cheeks
    fur_fill(d, rng, 12.6, 11.4, 4.2, 3.6, ARCTIC, 40, 0.3)
    tone(img, [(10.0, 10.6), (5.0, 12.4), (5.2, 13.3), (10.6, 14.3)], ARCTIC, "flat", light=0.15)  # muzzle
    for ear in ([(9.6, 9.0), (10.4, 4.8), (12.8, 7.8)], [(13.6, 7.8), (15.6, 5.0), (16.4, 9.2)]):  # short ears, rounded at the tip
        tone(img, ear, ARCTIC, "flat", light=-0.06)
        cx, cy = sum(p[0] for p in ear) / 3, sum(p[1] for p in ear) / 3
        touch(d, cx, cy + 0.2, 0.55, 0.8, ARCTIC[0], 150)
    touch(d, 5.2, 12.8, 0.55, 0.45, (16, 14, 18))  # nose
    touch(d, 10.0, 11.0, 0.55, 0.45, (26, 22, 20))  # eye
    touch(d, 9.86, 10.82, 0.18, 0.16, (255, 214, 150), 255)  # the tail's light in it
    stroke(d, [(5.8, 13.5), (9.6, 13.9)], ARCTIC[0], 0.2, 150)  # mouth
    return img


def fox_leaping():
    """The fox in mid-leap, facing right, forelegs reaching and hind legs kicking back, its
    brush streaming out behind. In a 60x30 box; the fire on its tail is added after."""
    tone, touch, oval = A.tone, A.touch, A.oval
    img, d = A.sprite(60, 30)
    rng = random.Random(612)
    bushy_tail(img, d, rng, ((21, 13.0), (10, 4.6), (0.5, 7.0)), ((0.5, 7.0), (7, 18.6), (21, 18.0)), light=-0.04)
    tone(img, [(20, 17), (15, 21), (10, 23.4), (10.6, 24.8), (17, 22.4), (23, 18.6)], ARCTIC, "flat", light=-0.3)  # far hind leg
    tone(img, [(37, 17), (42, 20), (47, 21.4), (46.6, 22.8), (41, 21.6), (35, 18.6)], ARCTIC, "flat", light=-0.3)  # far foreleg
    body = oval(29, 15.2, 11, 4.8)
    tone(img, body, ARCTIC, "sphere")
    fur_edge(d, body, ARCTIC, rng, 80, 0.9)
    tone(img, [(22, 16), (17, 20.4), (12, 23.2), (12.6, 24.6), (19, 22), (25, 18)], ARCTIC, "flat", light=-0.05)  # near hind leg
    tone(img, [(36, 16), (42, 18.6), (48.4, 19.6), (48.4, 21.0), (42, 20.6), (35, 18.6)], ARCTIC, "flat", light=0.05)  # near foreleg
    tone(img, [(36, 11.6), (41, 10.4), (42, 15), (38.6, 18), (35, 17.4)], ARCTIC, "flat", light=0.12)  # chest
    head = oval(43.4, 10.8, 4.4, 3.8)
    tone(img, head, ARCTIC, "sphere", light=0.08)
    tone(img, [(46, 9.8), (51, 11.4), (50.8, 12.3), (46, 13.4)], ARCTIC, "flat", light=0.15)
    for ear in ([(40.6, 8.4), (41.0, 4.6), (43.4, 7.4)], [(43.8, 7.2), (45.6, 4.4), (46.4, 8.4)]):
        tone(img, ear, ARCTIC, "flat", light=-0.1)
    touch(d, 51.0, 11.8, 0.5, 0.4, (16, 14, 18))
    touch(d, 46.0, 10.2, 0.5, 0.4, (26, 22, 20))
    return img


GALLOP = [  # (foreleg angle, hind leg angle, body bob, arch): angles from straight down, + forward
    (62, -62, 0.0, 0.0),  # stretched out, all four legs off the snow
    (18, -18, 0.6, 0.4),  # legs swinging in under the body
    (-32, 34, -0.4, 1.2),  # gathered, back arched, hind feet landing ahead of the fore
    (38, -42, 0.3, 0.5),  # pushing off, reaching forward again
]


def fox_running(frame):
    """The fox bounding along, facing right: `frame` of the four-frame gallop. In a 60x30
    box; its brush streams out behind, and the fire on it is added after."""
    tone, touch, oval = A.tone, A.touch, A.oval
    img, d = A.sprite(60, 30)
    rng = random.Random(614 + frame)
    fore, hind, bob, arch = GALLOP[frame]

    def leg(top, angle, length, light, bend):
        a = math.radians(angle)
        kx, ky = top[0] + math.sin(a) * length * 0.55, top[1] + math.cos(a) * length * 0.55
        b = math.radians(angle + bend)
        fx, fy = kx + math.sin(b) * length * 0.5, ky + math.cos(b) * length * 0.5
        w = 2.0
        tone(img, [(top[0] - w, top[1]), (top[0] + w, top[1]), (kx + w * 0.55, ky), (fx + 0.7, fy), (fx - 0.7, fy), (kx - w * 0.55, ky)], ARCTIC, "flat", light=light)
        touch(d, fx + 0.6, fy, 1.3, 0.65, ARCTIC[2] if light > -0.2 else ARCTIC[1], 255)

    y0 = 15.4 + bob
    bushy_tail(img, d, rng, ((21, y0 - 2.4), (10, y0 - 10), (0.5, y0 - 7.6)), ((0.5, y0 - 7.6), (7, y0 + 3.6), (21, y0 + 2.6)), light=-0.04)
    leg((22.4, y0 + 1.6), hind + 14, 9.6, -0.3, -40)  # far legs
    leg((36.0, y0 + 1.6), fore + 14, 9.0, -0.3, 30)
    body = oval(29, y0, 10.6, 4.6 + arch * 0.6)
    tone(img, body, ARCTIC, "sphere")
    fur_edge(d, body, ARCTIC, rng, 80, 0.9)
    fur_fill(d, rng, 29, y0, 10.6, 4.6, ARCTIC, 120, 0.0)
    tone(img, oval(22.6, y0 + 0.6 - arch * 0.4, 4.6, 4.4), ARCTIC, "sphere", light=0.02)  # haunch
    fur_fill(d, rng, 22.6, y0 + 0.6, 4.4, 4.2, ARCTIC, 40, math.pi * 0.6)
    leg((22.0, y0 + 2.6), hind, 9.6, -0.04, -40)  # near legs
    leg((36.4, y0 + 2.2), fore, 9.0, 0.05, 30)
    tone(img, [(35, y0 - 3.4), (40.6, y0 - 5.2), (42, y0 - 0.6), (38.4, y0 + 3.0), (34.6, y0 + 2.4)], ARCTIC, "flat", light=0.12)  # chest
    head = oval(43.4, y0 - 4.6, 4.4, 3.8)
    tone(img, head, ARCTIC, "sphere", light=0.08)
    fur_fill(d, rng, 43.4, y0 - 4.6, 4.0, 3.4, ARCTIC, 30, 0.2)
    tone(img, [(46, y0 - 5.4), (51, y0 - 4.0), (50.8, y0 - 3.1), (46, y0 - 2.0)], ARCTIC, "flat", light=0.15)
    for ear in ([(40.6, y0 - 7.0), (41.0, y0 - 10.8), (43.4, y0 - 8.0)], [(43.8, y0 - 8.2), (45.6, y0 - 11.0), (46.4, y0 - 7.0)]):
        tone(img, ear, ARCTIC, "flat", light=-0.1)
    touch(d, 51.0, y0 - 3.6, 0.5, 0.4, (16, 14, 18))
    touch(d, 46.0, y0 - 5.2, 0.5, 0.4, (26, 22, 20))
    return img


def fox_curled():
    """The fox lying curled in its den, facing left: nose on its forepaws, ears laid back,
    its brush (cold now, grey as ash, a few embers in it) wrapped round in front. The
    snare wire bites into its foreleg. In a 54x26 box."""
    tone, touch, stroke, curve, oval = A.tone, A.touch, A.stroke, A.curve, A.oval
    img, d = A.sprite(54, 26)
    rng = random.Random(613)
    back = oval(31, 15.6, 14, 7.2)
    tone(img, back, ARCTIC_DULL, "sphere")
    fur_edge(d, back[10:26], ARCTIC_DULL, rng, 90, 1.1)
    tone(img, oval(41, 16.4, 6, 5.6), ARCTIC_DULL, "sphere", light=-0.15)  # haunch
    for x0, lt in ((12.4, -0.2), (15.2, 0.0)):  # forelegs stretched out in front
        tone(img, [(x0 + 4, 18.4), (x0 + 6.4, 19.4), (x0 + 1.4, 23.2), (x0 - 2.6, 23.4), (x0 - 2.4, 22.0)], ARCTIC_DULL, "flat", light=lt)
    tone(img, oval(16.4, 16.6, 5.2, 4.0), ARCTIC_DULL, "sphere", light=0.06)  # head resting low
    tone(img, [(13.4, 15.6), (6.6, 18.6), (6.8, 19.6), (14.0, 20.2)], ARCTIC_DULL, "flat", light=0.1)
    for ex, ey in ((17.4, 13.0), (20.0, 13.6)):  # ears laid back
        tone(img, [(ex - 1.0, ey + 0.6), (ex + 4.6, ey - 1.4), (ex + 1.8, ey + 1.8)], ARCTIC_DULL, "flat", light=-0.15)
    touch(d, 6.7, 19.0, 0.6, 0.5, (16, 14, 16))  # nose
    stroke(d, [(11.4, 16.0), (13.2, 15.8)], ARCTIC_DULL[0], 0.26, 230)  # eye, shut
    brush = curve((44, 12), (55, 22), (40, 24.4), 14) + curve((40, 24.4), (24, 25.2), (12, 23.8), 12) + curve((12, 23.8), (28, 21.6), (42, 19), 12)
    tone(img, brush, ARCTIC_DULL, "flat", light=0.02)
    fur_edge(d, brush[:28], ARCTIC_DULL, rng, 50, 0.8)
    for k in range(8):  # embers still smouldering in the tip of the tail
        touch(d, 14 + k * 1.6 + rng.uniform(-0.4, 0.4), 23.4 + rng.uniform(-0.6, 0.4), 0.32, 0.26, (255, 140 + 10 * k, 70), 200)
    stroke(d, curve((11.8, 21.4), (13.6, 22.6), (15.6, 21.6), 6), WIRE[2], 0.26, 255)  # the wire, biting in
    stroke(d, curve((15.6, 21.6), (18.6, 23.2), (22, 23.4), 6), WIRE[1], 0.18, 230)
    touch(d, 14.0, 22.8, 0.6, 0.3, (140, 40, 40), 160)
    return img


def tail_flames(size, rng, spine, k, heat=1.0, tongues=520, sparks=120):
    """A tail of fire along `spine` (pixels), `k` pixels to a unit: tongues of flame licking
    up off it, white-gold at the root through orange to green at the tip, a glow around it,
    and sparks rising off the end. Returns (glow, flames) as light on black."""
    line = smooth(spine, 200)
    flames = Image.new("RGBA", size)
    fd = ImageDraw.Draw(flames)
    for _ in range(tongues):
        t = rng.random() ** 0.85
        i = min(len(line) - 2, int(t * (len(line) - 1)))
        (x, y), (x2, y2) = line[i], line[i + 1]
        dx, dy = x2 - x, y2 - y
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        width = k * (1.2 + 2.6 * math.sin(math.pi * min(1, 0.15 + t * 0.95)) ** 0.8)
        off = rng.gauss(0, 0.35) * width
        x0, y0 = x + nx * off, y + ny * off
        length = k * rng.uniform(1.5, 5.0) * (0.6 + t * 0.6)
        ang = math.atan2(dy, dx) + rng.gauss(0, 0.35)
        ang = math.atan2(math.sin(ang) - 0.7, math.cos(ang))  # flames lick upward
        pts = [(x0, y0)]
        for j in range(1, 6):
            f = j / 5
            a = ang + math.sin(f * 3 + t * 9 + rng.random()) * 0.5
            pts.append((x0 + math.cos(a) * length * f, y0 + math.sin(a) * length * f))
        base = A.mix(FLAME_CORE, FLAME, min(1, abs(off) / width * 2.5 + t * 2.2)) if t < 0.6 else A.mix(FLAME, SPIRIT_GREEN, min(1, (t - 0.6) * 2.5))
        for j, (p, q) in enumerate(zip(pts, pts[1:])):
            f = j / 5
            col = A.mix(base, FLAME_EDGE if t < 0.6 else (90, 180, 255), f * 0.7)
            fd.line([p, q], fill=col + (int(200 * (1 - f) * heat),), width=max(1, int(k * 0.55 * (1 - f) + 0.5)))
    sp = ImageDraw.Draw(flames)
    tip = line[-1]
    for _ in range(sparks):
        f = rng.random()
        x, y = tip[0] + rng.gauss(0, k * (1.5 + 6 * f)), tip[1] - f * 24 * k + rng.gauss(0, k)
        r = max(1.0, k * 0.22 * (1.2 - f))
        sp.ellipse([x - r, y - r, x + r, y + r], fill=A.mix((255, 210, 120), SPIRIT_GREEN, f) + (int(255 * (1 - f * 0.7) * heat),))
    glow = Image.new("RGBA", size, (0, 0, 0, 255))
    halo = Image.new("RGBA", size)
    hd = ImageDraw.Draw(halo)
    for (x, y) in line[::6]:
        hd.ellipse([x - 4 * k, y - 3 * k, x + 4 * k, y + 3 * k], fill=(255, 130, 50, int(36 * heat)))
    glow.alpha_composite(halo.filter(ImageFilter.GaussianBlur(5 * k)))
    lit = Image.new("RGBA", size, (0, 0, 0, 255))
    lit.alpha_composite(flames.filter(ImageFilter.GaussianBlur(1.2 * k)))
    lit.alpha_composite(flames.filter(ImageFilter.GaussianBlur(0.25 * k)))
    return glow, lit


def warm_side(body, center, radius, strength=150):
    """The tail's firelight falling on the fox's own fur, strongest nearest the fire."""
    m = Image.new("L", body.size, 0)
    cx, cy = center
    ImageDraw.Draw(m).ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=strength)
    m = ImageChops.multiply(m.filter(ImageFilter.GaussianBlur(radius * 0.5)), body.getchannel("A"))
    warm = Image.new("RGBA", body.size, (255, 160, 80, 255))
    warm.putalpha(m)
    out = body.copy()
    out.alpha_composite(warm)
    return out


def fire_fox(pose, seed, detail=2, heat=1.0, sparks=120, body=True):
    """The fire fox as an image: the painted fox, its tail of fire, the firelight on its fur.
    `pose` is "stand" (facing left) or "leap" (facing right). 60x30 units at SCALE*detail."""
    with_body = body
    k = A.SCALE * detail
    draw = {"stand": fox_standing, "leap": fox_leaping}.get(pose) or (lambda: fox_running(pose[1]))
    fox = paint_sprite(draw, 600 + seed % 7, detail)
    rng = random.Random(seed)
    if pose == "stand":  # along the top of the brush and round its tip
        spine = [(42, 12.0), (47, 7.6), (52, 4.8), (55.6, 3.6), (57, 3.0)]
        warm_at = (44 * k, 13 * k)
    elif pose == "leap":
        spine = [(17, 10.6), (11, 7.4), (6, 6.4), (2, 6.6), (0.5, 7.0)]
        warm_at = (14 * k, 12 * k)
    else:  # running: along the top of the brush, which bobs with the gait
        y0 = 15.4 + GALLOP[pose[1]][2]
        spine = [(17, y0 - 4.8), (11, y0 - 8.0), (6, y0 - 9.0), (2, y0 - 8.6), (0.5, y0 - 8.0)]
        warm_at = (14 * k, (y0 - 3) * k)
    glow, flames = tail_flames(fox.size, rng, [(x * k, y * k) for x, y in spine], k, heat, sparks=sparks)
    if not with_body:  # just the fire, to lay over a fox coloured some other way
        return as_glow(flames, 1.6)
    out = as_glow(glow, 2.0)
    out.alpha_composite(warm_side(fox, warm_at, 11 * k, int(60 * heat)))
    out.alpha_composite(as_glow(flames, 1.6))
    return out


def den_tail(frame, frames=6):
    """At the back of the den, the tip of the fox's tail in the dark, twitching, still
    holding a faint light. A 24x10 box; `frame` of `frames` sways it."""
    tone, touch, curve = A.tone, A.touch, A.curve
    img, d = A.sprite(24, 10)
    sway = math.sin(frame / frames * 2 * math.pi)
    tip = (4 + 1.6 * sway, 5.6 - 1.4 * sway)
    rng = random.Random(620 + frame)
    brush = curve((24, 4.4), (12, 0.4 + sway * 0.8), tip, 14) + curve(tip, (11, 11.6 + sway * 0.6), (24, 10.0), 14)
    dark = ((14, 14, 22), (48, 48, 60), (96, 96, 108))  # in the dark of the den
    tone(img, brush, dark, "flat", light=-0.1)
    fur_edge(d, brush, dark, rng, 70, 0.7)
    for k in range(7):
        f = k / 6
        x, y = tip[0] + 1 + (12 - tip[0]) * f, tip[1] + 0.6 + rng.uniform(-0.6, 0.6)
        touch(d, x, y, 0.28, 0.24, (255, 150 + 8 * k, 70), int(170 - 15 * k))
    return img


def den_tail_frames():
    for frame in range(6):
        body = paint_sprite(lambda: den_tail(frame), 630, 2, A.SMALL_BRUSHES)
        glow = Image.new("RGBA", body.size, (0, 0, 0, 255))
        k = A.SCALE * 2
        g = Image.new("RGBA", body.size)
        sway = math.sin(frame / 6 * 2 * math.pi)
        tx, ty = (4 + 1.6 * sway) * k, (5.6 - 1.4 * sway) * k
        ImageDraw.Draw(g).ellipse([tx - 3 * k, ty - 2.5 * k, tx + 8 * k, ty + 3 * k], fill=(255, 130, 50, 110))
        glow.alpha_composite(g.filter(ImageFilter.GaussianBlur(3 * k)))
        out = as_glow(glow, 1.6)
        out.alpha_composite(body)
        A.save(out, f"objects/foxtail_{frame}.png")


def firefox_frames():
    """The fire fox on the fell, waiting: the painted fox, its tail of fire flickering
    through four frames."""
    for frame in range(4):
        A.save(fire_fox("stand", 400 + frame, sparks=60), f"objects/firefox_{frame}.png")


# ---------------------------------------------------------------- figures


FUR_GREY = ((60, 58, 64), (130, 126, 128), (196, 192, 188))
WOLF = ((58, 54, 52), (118, 110, 102), (182, 174, 160))
WOLF_DARK = ((34, 30, 30), (72, 64, 60), (120, 110, 100))
COAT_BLUE = ((22, 28, 60), (48, 60, 108), (96, 110, 160))
TRIM_RED = ((90, 20, 26), (170, 40, 40), (226, 96, 76))
TRIM_YELLOW = ((120, 90, 20), (210, 170, 60), (246, 220, 130))
REINDEER_FUR = ((96, 84, 74), (170, 156, 136), (226, 214, 192))
MITTEN = ((90, 24, 30), (168, 44, 44), (224, 110, 90))
BEARD = ((60, 44, 34), (110, 84, 64), (170, 140, 110))
WIRE = ((90, 94, 106), (168, 172, 184), (236, 238, 246))
BIRCH_BARK = ((90, 80, 70), (206, 196, 178), (250, 246, 236))


def mummo():
    """Mummo, turned toward the left: a long dark-blue wool coat bordered in red and
    yellow, a red shawl over her head, red mittens, reindeer-fur boots, and her stick."""
    tone, touch, stroke, curve, sleeve, oval = A.tone, A.touch, A.stroke, A.curve, A.sleeve, A.oval
    img, d = A.sprite(18, 46)
    for x in (7.4, 10.8):
        tone(img, oval(x, 45.0, 1.9, 1.1), REINDEER_FUR, "sphere")
    coat = curve((5.8, 15), (3.6, 30), (2.4, 44.2)) + curve((2.4, 44.2), (9.4, 45.4), (16.2, 44.2)) + curve((16.2, 44.2), (15.0, 30), (12.8, 15))
    tone(img, coat, COAT_BLUE, core=0.68)
    stroke(d, curve((2.6, 42.6), (9.4, 43.8), (16.0, 42.6), 8), TRIM_RED[1], 1.1, 255)  # the bands at the hem
    stroke(d, curve((2.7, 41.2), (9.4, 42.4), (15.9, 41.2), 8), TRIM_YELLOW[1], 0.5, 255)
    stroke(d, [(9.6, 17), (9.2, 44)], TRIM_RED[1], 0.7, 230)  # down the front
    for x0, x1, lit in ((6.6, 4.4, True), (11.6, 13.8, False)):
        stroke(d, curve((x0, 18), ((x0 + x1) / 2, 30), (x1, 41), 6), COAT_BLUE[2] if lit else COAT_BLUE[0], 1.0, 100)
    stick = [(2.0, 22.4), (1.8, 30), (1.7, 38), (1.5, 46)]
    stroke(d, stick, A.JUNIPER[0], 0.9)
    stroke(d, [(x - 0.2, y) for x, y in stick], A.JUNIPER[2], 0.3, 210)
    sleeve(img, d, (12.8, 16.2), (13.8, 22.0), (13.2, 28.0), 1.2, -0.3, MITTEN, COAT_BLUE)
    sleeve(img, d, (5.4, 16.2), (3.8, 19.8), (2.4, 22.6), 1.25, 0.1, MITTEN, COAT_BLUE)
    for wx, wy in ((13.0, 27.4), (2.6, 22.0)):
        stroke(d, [(wx - 1.1, wy), (wx + 1.1, wy)], TRIM_RED[1], 0.6, 255)  # red cuffs
    shawl = [(4.0, 15.4), (6.6, 13.6), (12.0, 13.6), (14.6, 15.4), (13.6, 21.4), (9.2, 25.4), (4.8, 21.4)]
    tone(img, shawl, A.SCARF, light=0.08)
    for x in (6.4, 8.6, 10.8, 12.6):
        touch(d, x, 18.0, 0.42, 0.34, TRIM_YELLOW[2], 200, 0.785)
    for i in range(14):
        f = i / 13
        x, y = (4.8 + (9.2 - 4.8) * f * 2, 21.4 + 4.0 * f * 2) if f < 0.5 else (9.2 + (13.6 - 9.2) * (f - 0.5) * 2, 25.4 - 4.0 * (f - 0.5) * 2)
        stroke(d, [(x, y), (x, y + 0.9)], A.SCARF[2], 0.15, 170)
    cx, cy = 8.8, 10.2
    A.face_three_quarter(img, d, cx, cy, -1, A.OLD_SKIN, age=1.0)
    stroke(d, [(cx - 1.4, cy - 1.9), (cx + 0.6, cy - 2.05)], (206, 204, 200), 0.35, 230)
    hood = [(cx - 2.7, cy + 1.8), (cx - 2.7, cy - 1.6), (cx - 1.3, cy - 3.8), (cx + 1.0, cy - 4.1), (cx + 2.8, cy - 2.7),
            (cx + 3.1, cy - 0.4), (cx + 2.6, cy + 3.0), (cx + 1.9, cy + 3.6), (cx + 2.0, cy + 0.6), (cx + 1.1, cy - 1.7),
            (cx - 1.0, cy - 2.3), (cx - 2.0, cy - 0.6), (cx - 2.1, cy + 1.9)]
    tone(img, hood, A.SCARF, "sphere", light=0.06)
    tone(img, [(cx - 2.7, cy + 1.4), (cx - 2.1, cy + 1.6), (cx - 1.6, cy + 2.8), (cx - 0.3, cy + 3.5), (cx + 0.5, cy + 3.8),
               (cx - 0.4, cy + 4.2), (cx - 2.0, cy + 3.6)], A.SCARF, "flat", light=0.04)
    touch(d, cx + 0.1, cy + 3.5, 0.55, 0.45, A.SCARF[0])
    return img


def jussi():
    """Jussi the trapper, turned toward the left: a shaggy wolfskin coat belted at the waist,
    a fur hat, a grizzled beard, leather leggings and boots, a bundle of snares in his hand."""
    tone, touch, stroke, curve, sleeve, oval = A.tone, A.touch, A.stroke, A.curve, A.sleeve, A.oval
    img, d = A.sprite(18, 46)
    for x, side in ((6.8, 1), (11.2, -1)):  # legs in leather leggings, boots
        tone(img, [(x - 1.5, 32), (x + 1.5, 32), (x + 1.3, 43.4), (x - 1.3, 43.4)], ((50, 36, 28), (96, 70, 50), (150, 116, 84)))
        tone(img, oval(x - 0.6, 44.6, 2.2, 1.2), ((30, 24, 22), (64, 50, 40), (110, 90, 70)), "sphere")
    coat = [(4.2, 15.0), (7.0, 13.6), (11.6, 13.6), (14.4, 15.2), (15.0, 26), (14.6, 34.6), (9.4, 35.6), (3.6, 34.6), (3.2, 26)]
    tone(img, coat, WOLF, core=0.66)
    rng = random.Random(77)
    for _ in range(90):  # shaggy fur
        x, y = rng.uniform(4, 14.4), rng.uniform(15, 35)
        stroke(d, [(x, y), (x + rng.uniform(-0.4, 0.4), y + rng.uniform(0.8, 1.8))], WOLF[2] if x < 8 else WOLF[0], 0.18, 150)
    stroke(d, [(3.4, 34.4), (9.4, 35.4), (14.8, 34.4)], WOLF[2], 0.6, 200)  # the ragged hem
    stroke(d, [(3.6, 25.4), (14.8, 25.4)], (54, 36, 26), 1.0, 255)  # belt
    touch(d, 7.8, 25.4, 0.6, 0.5, (190, 180, 160))  # buckle
    stroke(d, [(11.8, 25.8), (12.4, 30.2)], (60, 40, 28), 0.8, 255)  # his knife's sheath
    sleeve(img, d, (13.4, 16.0), (14.6, 21.6), (14.2, 27.2), 1.45, -0.3, WOLF_DARK, WOLF)
    sleeve(img, d, (5.0, 16.0), (3.4, 21.0), (4.0, 25.4), 1.5, 0.1, WOLF_DARK, WOLF)
    for k in range(3):  # snares in his near hand, coils of wire
        cy = 27.6 + k * 1.1
        stroke(d, curve((2.4, cy), (4.0, cy + 2.4), (5.6, cy), 8) + curve((5.6, cy), (4.0, cy - 1.2), (2.4, cy), 8), WIRE[1], 0.14, 230)
    cx, cy = 9.0, 9.6
    A.face_three_quarter(img, d, cx, cy, -1, ((120, 80, 70), (190, 140, 112), (236, 196, 160)), age=0.6)
    tone(img, [(cx - 2.0, cy + 1.0), (cx + 2.2, cy + 1.0), (cx + 2.0, cy + 3.8), (cx + 0.2, cy + 5.4), (cx - 1.8, cy + 3.8)], BEARD, "sphere", light=0.05)
    stroke(d, [(cx - 1.0, cy + 1.6), (cx + 0.6, cy + 1.5)], BEARD[0], 0.3, 200)  # mouth in the beard
    hat = [(cx - 3.0, cy - 0.6), (cx - 2.8, cy - 3.6), (cx - 0.6, cy - 5.6), (cx + 2.2, cy - 5.4), (cx + 3.4, cy - 3.0), (cx + 3.2, cy - 0.4)]
    tone(img, hat, WOLF_DARK, "sphere", light=0.1)
    stroke(d, [(cx - 3.0, cy - 1.0), (cx + 3.2, cy - 0.8)], WOLF[2], 0.9, 230)  # the fur brim
    tone(img, [(cx + 2.4, cy - 1.0), (cx + 3.6, cy - 1.0), (cx + 3.4, cy + 3.0), (cx + 2.2, cy + 2.4)], WOLF_DARK, "flat")  # earflap
    return img


# ---- Vilja in winter clothes: a fur-trimmed jacket, a knitted cap and red mittens over
# her summer dress, drawn over the same poses as make_art's Vilja.

JACKET = ((20, 24, 44), (52, 62, 100), (110, 124, 168))  # dark blue felt
FUR_TRIM = ((120, 108, 96), (200, 190, 176), (246, 240, 228))
CAP = ((80, 20, 28), (160, 40, 44), (220, 100, 86))


def winter_jacket(img, d, torso, hem_y, near_sleeve, far_sleeve, head):
    tone, stroke, touch, sleeve, curve = A.tone, A.stroke, A.touch, A.sleeve, A.curve
    sleeve(img, d, *far_sleeve, MITTEN, JACKET)
    tone(img, torso, JACKET, light=0.04)
    xs = [p[0] for p in torso]
    x0, x1 = min(xs), max(xs)
    stroke(d, [(x0 + 0.1, hem_y), (x1 - 0.1, hem_y)], FUR_TRIM[1], 1.1, 255)  # the fur hem
    stroke(d, [(x0 + 0.3, hem_y - 0.4), ((x0 + x1) / 2, hem_y - 0.5)], FUR_TRIM[2], 0.4, 200)
    stroke(d, [((x0 + x1) / 2 + 0.3, torso[1][1] + 0.6), ((x0 + x1) / 2 + 0.4, hem_y - 0.6)], A.MADDER[1], 0.35, 220)  # the front edge
    sleeve(img, d, *near_sleeve, MITTEN, JACKET)
    for (sx, sy), (ex, ey), (wx, wy), wd, lt in (far_sleeve[:5], near_sleeve[:5]):
        stroke(d, [(wx - wd * 0.8, wy - 0.2), (wx + wd * 0.8, wy - 0.2)], FUR_TRIM[1], 0.6, 255)  # fur cuffs
    cx, cy, facing = head
    tone(img, [(cx - 2.5, cy - 0.6), (cx - 2.3, cy - 2.6), (cx - 0.8, cy - 4.0), (cx + 1.2, cy - 4.0), (cx + 2.4, cy - 2.6), (cx + 2.5, cy - 0.6)],
         CAP, "sphere", light=0.05)
    stroke(d, [(cx - 2.5, cy - 0.9), (cx + 2.5, cy - 0.9)], FUR_TRIM[1], 0.7, 255)  # a white band, knitted
    for k in range(5):
        touch(d, cx - 1.8 + k * 0.9, cy - 2.0, 0.22, 0.22, FUR_TRIM[2], 220)
    touch(d, cx - 0.2 * facing, cy - 4.3, 0.8, 0.8, FUR_TRIM[1])  # pompom


def vilja_winter_standing():
    img = A.vilja_standing()
    d = A.Painter(img)
    winter_jacket(img, d, [(3.5, 10.4), (5.4, 9.3), (8.6, 9.3), (10.4, 10.4), (10.8, 20.8), (3.2, 20.8)], 20.8,
                  ((10.2, 11.0), (11.1, 15.8), (11.0, 20.0), 1.15, -0.28), ((3.6, 11.0), (2.8, 15.8), (3.0, 20.0), 1.25, 0.1), (7.1, 5.3, 1))
    A.braid(d, (8.9, 6.6), (10.6, 13), (10.2, 21.8), 1)
    return img


def vilja_winter_walking(frame):
    img = A.vilja_walking(frame)
    d = A.Painter(img)
    phase = frame / 4 * 2 * math.pi
    stride, lift = math.sin(phase), math.cos(phase)
    bob = -0.35 * (1 - abs(stride))
    Y = lambda y: y + bob  # noqa: E731
    swing = -stride
    winter_jacket(img, d, [(5.0, Y(10.3)), (7.2, Y(9.3)), (9.0, Y(10.1)), (9.5, Y(13.4)), (9.7, Y(20.6)), (4.8, Y(20.6))], Y(20.6),
                  ((7.6, Y(10.9)), (7.8 + 1.4 * swing, Y(15.0)), (7.9 + 2.8 * swing, Y(18.8)), 1.15, 0.12),
                  ((6.6, Y(10.9)), (6.0 - 1.4 * swing, Y(15.2)), (5.8 - 2.6 * swing, Y(19.0)), 1.1, -0.3), (7.4, Y(5.2), 1))
    A.braid(d, (5.6, Y(6.2)), (4.6 - 0.3 * lift, Y(12)), (4.0 - 0.6 * lift, Y(20.6)), -1)
    return img


# ---- objects and items


def snowshoes_drawing(w, h, lying=False):
    tone, stroke, oval = A.tone, A.stroke, A.oval
    img, d = A.sprite(w, h)
    frames = [(w * 0.36, h * 0.5, w * 0.3, h * 0.46), (w * 0.64, h * 0.52, w * 0.3, h * 0.45)] if not lying else \
        [(w * 0.5, h * 0.36, w * 0.44, h * 0.26), (w * 0.5, h * 0.64, w * 0.44, h * 0.26)]
    for cx, cy, rx, ry in frames:
        ring = oval(cx, cy, rx, ry, 32)
        stroke(d, ring + ring[:1], (150, 118, 80), max(0.08 * min(w, h), 0.3), 255)
        for k in range(-3, 4):  # sinew lacing, crossed
            off = k / 4
            stroke(d, [(cx + rx * off - rx * 0.4, cy - ry * 0.85), (cx + rx * off + rx * 0.4, cy + ry * 0.85)], (210, 196, 160), 0.03 * min(w, h) + 0.04, 170)
            stroke(d, [(cx + rx * off + rx * 0.4, cy - ry * 0.85), (cx + rx * off - rx * 0.4, cy + ry * 0.85)], (190, 176, 140), 0.03 * min(w, h) + 0.04, 170)
        stroke(d, [(cx - rx * 0.6, cy), (cx + rx * 0.6, cy)], (110, 80, 54), 0.07 * min(w, h) + 0.1, 255)  # the foot strap
    return img


def line_drawing(w, h, frozen=True):
    tone, stroke, curve, oval, touch = A.tone, A.stroke, A.curve, A.oval, A.touch
    img, d = A.sprite(w, h)
    if frozen:
        tone(img, oval(w / 2, h * 0.7, w * 0.34, h * 0.2), ((60, 84, 124), (120, 150, 186), (190, 210, 230)), "sphere")
    for k in range(4):
        r = 0.32 - k * 0.05
        loop = A.oval(w * 0.48 + k * w * 0.02, h * 0.5, w * r, h * r * 1.2, 24)
        stroke(d, loop + loop[:1], (196, 186, 160), 0.035 * w + 0.04, 230)
    stroke(d, curve((w * 0.7, h * 0.5), (w * 0.85, h * 0.3), (w * 0.82, h * 0.18), 6), (196, 186, 160), 0.03 * w + 0.04, 230)
    stroke(d, curve((w * 0.82, h * 0.18), (w * 0.9, h * 0.1), (w * 0.88, h * 0.28), 6), (200, 204, 214), 0.04 * w + 0.04, 255)  # the hook
    touch(d, w * 0.86, h * 0.14, w * 0.03, w * 0.03, (255, 255, 255), 230)
    return img


def snare_drawing(w, h):
    stroke, touch, curve, tone, oval = A.stroke, A.touch, A.curve, A.tone, A.oval
    img, d = A.sprite(w, h)
    stroke(d, [(w * 0.3, h * 0.95), (w * 0.24, h * 0.3)], (96, 74, 54), 0.12 * w, 255)  # the peg, half torn out
    loop = curve((w * 0.26, h * 0.4), (w * 0.95, h * 0.2), (w * 0.7, h * 0.85), 10) + curve((w * 0.7, h * 0.85), (w * 0.3, h * 0.9), (w * 0.26, h * 0.4), 10)
    stroke(d, loop, WIRE[1], 0.035 * w + 0.04, 230)
    tone(img, oval(w * 0.62, h * 0.5, w * 0.2, h * 0.16), ((220, 90, 30), (255, 160, 70), (255, 236, 180)), "sphere")  # the fur
    for k in range(6):
        stroke(d, [(w * 0.55 + k * w * 0.03, h * 0.5), (w * 0.5 + k * w * 0.05, h * 0.3)], (255, 200, 120), 0.02 * w + 0.03, 200)
    return img


def box_drawing(w, h, ember=False):
    tone, stroke, touch, oval = A.tone, A.stroke, A.touch, A.oval
    img, d = A.sprite(w, h)
    top, base = h * 0.4, h * 0.9
    tone(img, [(w * 0.18, top), (w * 0.82, top), (w * 0.82, base), (w * 0.18, base)], BIRCH_BARK, "cylinder")
    rng = random.Random(91)
    for _ in range(9):  # the dark lenticels of birch bark
        x, y = rng.uniform(w * 0.22, w * 0.78), rng.uniform(top + h * 0.05, base - h * 0.05)
        stroke(d, [(x - w * 0.06, y), (x + w * 0.06, y)], (60, 54, 50), 0.02 * h + 0.04, 200)
    stroke(d, [(w * 0.18, base), (w * 0.82, base)], (120, 104, 84), 0.03 * h + 0.04, 255)
    if ember:
        tone(img, oval(w / 2, top, w * 0.32, h * 0.08), ((50, 30, 20), (90, 50, 30), (140, 90, 60)), "flat")
        touch(d, w / 2, top, w * 0.18, h * 0.06, (255, 140, 50), 255)
        touch(d, w / 2 - w * 0.03, top - h * 0.01, w * 0.08, h * 0.03, (255, 236, 160), 255)
        glow = Image.new("RGBA", img.size)
        ImageDraw.Draw(glow).ellipse([s(w * 0.2), s(top - h * 0.3), s(w * 0.8), s(top + h * 0.1)], fill=(255, 140, 50, 140))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s(w * 0.08))))
    else:
        tone(img, oval(w / 2, top, w * 0.33, h * 0.09), BIRCH_BARK, "sphere", light=0.1)  # the lid
        stroke(d, [(w * 0.46, top - h * 0.02), (w * 0.54, top - h * 0.02)], (100, 80, 60), 0.04 * h, 255)
    return img


def fish_drawing(w, h):
    tone, stroke, touch, curve = A.tone, A.stroke, A.touch, A.curve
    img, d = A.sprite(w, h)
    body = curve((w * 0.08, h * 0.55), (w * 0.4, h * 0.2), (w * 0.78, h * 0.5), 12) + curve((w * 0.78, h * 0.5), (w * 0.4, h * 0.82), (w * 0.08, h * 0.55), 12)
    tone(img, body, ((80, 96, 120), (180, 194, 210), (246, 248, 252)), "flat", light=0.1)
    d.polygon(A.pts([(w * 0.76, h * 0.5), (w * 0.96, h * 0.3), (w * 0.92, h * 0.5), (w * 0.96, h * 0.72)]), fill=(120, 134, 156, 255))
    stroke(d, curve((w * 0.16, h * 0.5), (w * 0.4, h * 0.42), (w * 0.72, h * 0.5), 8), (100, 116, 140), 0.02 * h + 0.03, 160)
    touch(d, w * 0.17, h * 0.5, w * 0.03, w * 0.03, (20, 20, 26))
    touch(d, w * 0.35, h * 0.4, w * 0.12, h * 0.03, (255, 255, 255), 200)
    return img


def puukko_drawing(w, h):
    tone, stroke, touch = A.tone, A.stroke, A.touch
    img, d = A.sprite(w, h)
    blade = [(w * 0.5, h * 0.52), (w * 0.92, h * 0.12), (w * 0.86, h * 0.26), (w * 0.56, h * 0.6)]
    tone(img, blade, ((90, 96, 110), (180, 186, 196), (248, 250, 252)), "flat", light=0.05)
    stroke(d, [(w * 0.56, h * 0.5), (w * 0.9, h * 0.14)], (255, 255, 255), 0.02 * h + 0.03, 220)
    tone(img, [(w * 0.46, h * 0.5), (w * 0.58, h * 0.6), (w * 0.52, h * 0.66), (w * 0.42, h * 0.56)], ((80, 60, 40), (150, 120, 80), (210, 180, 130)), "flat")
    handle = [(w * 0.44, h * 0.56), (w * 0.52, h * 0.64), (w * 0.2, h * 0.94), (w * 0.08, h * 0.86)]
    tone(img, handle, ((90, 60, 36), (170, 124, 76), (226, 186, 130)), "cylinder")  # curly birch
    for k in range(4):
        touch(d, w * (0.38 - k * 0.07), h * (0.66 + k * 0.07), w * 0.03, h * 0.02, (110, 74, 44), 200, -0.8)
    return img


def fur_drawing(w, h):
    tone, stroke, oval = A.tone, A.stroke, A.oval
    img, d = A.sprite(w, h)
    tone(img, oval(w / 2, h * 0.55, w * 0.3, h * 0.24), ((220, 90, 30), (255, 160, 70), (255, 236, 180)), "sphere")
    rng = random.Random(93)
    for _ in range(18):
        a = rng.uniform(-2.6, -0.5)
        L = rng.uniform(0.2, 0.36) * w
        x, y = w / 2 + rng.uniform(-w * 0.15, w * 0.15), h * 0.55
        stroke(d, [(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], (255, 200, 120), 0.025 * w + 0.03, 220)
    glow = Image.new("RGBA", img.size)
    ImageDraw.Draw(glow).ellipse([s(w * 0.1), s(h * 0.15), s(w * 0.9), s(h * 0.95)], fill=(255, 150, 60, 110))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s(w * 0.1))))
    return img


def objects():
    A.painted_figure(lambda: snowshoes_drawing(12, 28), "objects/snowshoes.png", 501, brushes=A.SMALL_BRUSHES)
    A.painted_figure(lambda: line_drawing(12, 8), "objects/line.png", 502, brushes=A.SMALL_BRUSHES)
    A.painted_figure(lambda: snare_drawing(10, 12), "objects/snare.png", 503, brushes=A.SMALL_BRUSHES, rim=False)
    A.painted_figure(fox_curled, "objects/fox_grey.png", 504, brushes=A.SMALL_BRUSHES)
    den_tail_frames()
    firefox_frames()


def items():
    for name, draw, seed, rim in (("snowshoes", lambda: snowshoes_drawing(16, 16, lying=True), 511, True),
                                  ("box", lambda: box_drawing(16, 16), 512, True),
                                  ("ember", lambda: box_drawing(16, 16, ember=True), 513, False),
                                  ("line", lambda: line_drawing(16, 16, frozen=False), 514, True),
                                  ("fish", lambda: fish_drawing(16, 16), 515, True),
                                  ("puukko", lambda: puukko_drawing(16, 16), 516, True),
                                  ("fur", lambda: fur_drawing(16, 16), 517, False)):
        A.painted_figure(draw, f"items/{name}.png", seed, brushes=A.SMALL_BRUSHES, rim=rim)


def characters():
    A.painted_figure(mummo, "chars/mummo.png", 521)
    A.painted_figure(jussi, "chars/jussi.png", 522)
    A.painted_figure(vilja_winter_standing, "chars/vilja_winter_stand.png", 11)
    for frame in range(4):
        A.painted_figure(lambda: vilja_winter_walking(frame), f"chars/vilja_winter_walk_{frame}.png", 15 + frame)


def effects():
    """A snowflake, and curtains of the aurora for the game to set rippling in the sky."""
    flake = Image.new("RGBA", (16, 16))
    fd = ImageDraw.Draw(flake)
    fd.ellipse([4, 4, 12, 12], fill=(236, 242, 255, 255))
    A.save(flake.filter(ImageFilter.GaussianBlur(1.6)), "effects/snow.png")
    size = (440, 300)
    edge = Image.new("L", size)
    ed = ImageDraw.Draw(edge)
    for x in range(size[0]):
        u = x / (size[0] - 1)
        ed.line([(x, 0), (x, size[1])], fill=int(255 * min(1.0, u * 3.5, (1 - u) * 3.5)))
    # Three folds of curtain, each fading out at both ends so neighbours blend.
    for i, (pts, height, sway) in enumerate((([(-20, 260), (90, 236), (200, 262), (300, 228), (460, 246)], 220, -0.15),
                                             ([(-20, 220), (120, 270), (240, 232), (340, 276), (460, 250)], 190, 0.12),
                                             ([(-20, 270), (110, 250), (220, 200), (330, 240), (460, 214)], 250, -0.25))):
        rng = random.Random(531 + i)
        light = Image.new("RGBA", size, (0, 0, 0, 255))
        lay = curtain(rng, size, pts, height, 255, sway)
        light.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))
        light.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
        img = as_glow(light, 2.5)
        img.putalpha(ImageChops.multiply(img.getchannel("A"), edge))
        A.save(img, f"effects/aurora_{i}.png")
    # The fire fox leaping across the sky, facing right, its tail streaming out behind.
    A.save(fire_fox("leap", 541, detail=1, sparks=40), "effects/fox_streak.png")


# ---------------------------------------------------------------- the intro, card and title


def intro_fells():
    """The intro: a panorama the camera sweeps across. From the left: a range of fells
    under a blazing sky, the fire fox leaping along a ridge, then a frozen lake in the
    valley, the edge of the forest, and on the right Mummo's camp, the kota glowing, the
    reindeer in the snow. The lights, the fox and its trail are separate glows, which die."""
    with canvas(*INTRO_SIZE):
        rng = random.Random(541)
        img = Image.new("RGBA", (W, H()))
        horizon = s(124)
        night_gradient(img, horizon)
        milky_way(img, rng, s(10), s(70))
        sky_only = img.copy()
        far_fells(img, rng, horizon, layers=((96, (58, 78, 126), (156, 196, 212)), (60, (46, 62, 108), (116, 154, 176)), (28, (36, 50, 92), (80, 116, 140))), freq=(9, 21, 55))
        snowfield(img, rng, horizon + s(2), H(), strokes=9000)
        # The frozen lake in the valley, holding a dim mirror of the sky.
        lake_pts = smooth([(s(290), s(132)), (s(360), s(128)), (s(440), s(131)), (s(470), s(140)), (s(400), s(150)), (s(300), s(148)), (s(270), s(140))], 60)
        ice = Image.new("RGBA", (W, H()))
        idr = ImageDraw.Draw(ice)
        for y in range(s(126), s(152)):
            idr.line([(0, y), (W, y)], fill=A.mix((60, 84, 126), (26, 36, 70), (y - s(126)) / s(26)) + (255,))
        cv = A.Canvas(ice)
        for _ in range(500):
            x, y = rng.uniform(s(270), s(470)), rng.uniform(s(128), s(150))
            A.dab(cv, x, y, s(rng.uniform(2, 8)), s(rng.uniform(0.2, 0.4)), A.mix((90, 120, 160), SNOW_HI, rng.random() * 0.6) + (140,), 0, 6)
        cv.flush()
        ice.putalpha(mask_of(lake_pts).filter(ImageFilter.GaussianBlur(3)))
        img.alpha_composite(ice)
        # Forest along the feet of the fells, thicker in places, and frost haze in the valley.
        for x0, x1, hmin, hmax, step in ((-4, 300, 4, 9, (3, 8)), (250, 560, 5, 11, (2.5, 6)), (560, 840, 5, 12, (2.5, 6))):
            tree_row(img, rng, horizon + s(3), hmin, hmax, 0.55, s(x0), s(x1), step=step)
        for x0, x1 in ((300, 470), (560, 720)):
            tree_row(img, rng, horizon + s(9), 8, 16, 0.35, s(x0), s(x1), step=(3, 7))
        A.mist(img, rng, 128, 14, 70, 240, 520, color=(90, 120, 170))
        # A frozen stream winding down from the lake to the foreground.
        stream = smooth([(s(420), s(146)), (s(440), s(156)), (s(410), s(166)), (s(440), s(176)), (s(470), s(184))], 120)
        sl = A.new_layer()
        sv = A.Canvas(sl)
        for i, (x, y) in enumerate(stream):
            t = i / len(stream)
            w = s(2 + 7 * t)
            A.dab(sv, x, y, w, w * 0.32, A.mix((50, 72, 112), (30, 42, 78), t) + (255,), 0, 10)
            if i % 3 == 0:
                A.dab(sv, x + rng.uniform(-w, w) * 0.5, y, w * 0.4, s(0.25), A.mix((120, 150, 190), SNOW_HI, rng.random() * 0.5) + (200,), 0, 6)
        sv.flush()
        img.alpha_composite(sl.filter(ImageFilter.GaussianBlur(0.8)))
        # The ridge the fox runs along: snow over rock, lit along its crest.
        ridge_pts = smooth([(s(40), s(150)), (s(110), s(112)), (s(160), s(106)), (s(210), s(108)), (s(250), s(116)), (s(330), s(150))], 80)
        mound = Image.new("RGBA", (W, H()))
        snowfield(mound, rng, s(100), s(152), lit=(222, 236, 244), mid=(130, 152, 190), strokes=2600)
        mound.putalpha(ImageChops.multiply(mound.getchannel("A"), mask_of(ridge_pts).filter(ImageFilter.GaussianBlur(s(2)))))
        img.alpha_composite(mound)
        for x0, y0, x1, y1 in ((96, 112, 120, 126), (226, 110, 252, 124), (140, 108, 158, 118)):
            rough_rock(img, rng, x0, y0, x1, y1, 0.3)
        # Groves of snowy spruces through the middle distance.
        for cx, base, n, hmax in ((118, 124, 5, 22), (338, 136, 6, 26), (612, 140, 7, 30), (796, 146, 4, 34)):
            for j in range(n):
                h = s(rng.uniform(hmax * 0.5, hmax))
                snowy_spruce(img, rng, s(cx + rng.uniform(-12, 12)), s(base + rng.uniform(-2, 2)), h, h * rng.uniform(0.3, 0.38), fade=0.25, depth=3)
        # The foreground: drifts carved by the wind, boulders, dead grass poking through.
        fg = A.new_layer()
        fv = A.Canvas(fg)
        for _ in range(500):
            x, y = rng.uniform(0, W), rng.uniform(s(158), H())
            L = s(rng.uniform(8, 30))
            A.dab(fv, x, y, L, s(rng.uniform(0.3, 0.6)), SNOW_HI + (150,), rng.uniform(-0.05, 0.05), 6)
            A.dab(fv, x + s(1), y + s(0.8), L * 0.9, s(rng.uniform(0.3, 0.5)), A.mix(SNOW_LO, SNOW_MID, 0.4) + (130,), rng.uniform(-0.05, 0.05), 6)
        fv.flush()
        img.alpha_composite(fg)
        for x0, y0, x1, y1 in ((36, 160, 62, 178), (186, 166, 206, 180), (404, 168, 420, 180), (520, 166, 548, 182), (668, 174, 690, 184)):
            rough_rock(img, rng, x0, y0, x1, y1, 0.3)
        grass = A.new_layer()
        gd = ImageDraw.Draw(grass)
        for _ in range(160):
            x, y = rng.uniform(0, W), rng.uniform(s(160), H())
            for _ in range(rng.randint(2, 5)):
                gd.line([(x, y), (x + rng.uniform(-s(1.5), s(1.5)), y - rng.uniform(s(2), s(6)))], fill=A.mix((70, 66, 70), (130, 122, 110), rng.random()) + (255,), width=2)
        img.alpha_composite(grass)
        # The forest edge: snowy spruces, close and tall, sweeping past.
        for x, base, h in [(470, 150, 60), (490, 146, 44), (506, 152, 74), (530, 148, 52), (548, 154, 40)]:
            snowy_spruce(img, rng, s(x), s(base), s(h), s(h * 0.34), depth=4, shadowed=0.2)
        for x, base, h in [(380, 128, 14), (396, 127, 10), (620, 128, 16), (636, 127, 12), (812, 130, 18)]:
            snowy_spruce(img, rng, s(x), s(base), s(h), s(h * 0.38), fade=0.4, depth=2)
        rough_rock(img, rng, 572, 152, 600, 168, 0.3)
        rough_rock(img, rng, 594, 158, 612, 170, 0.3)
        # The camp: the kota and the reindeer, painted finely on a layer of their own.
        figures = A.new_layer()
        door = kota(figures, rng, 712, 800, 168, 110)
        for x, base, size, pose, facing in [(640, 162, 1.3, "stand", 1), (672, 170, 1.4, "graze", -1), (618, 174, 1.35, "lie", 1), (690, 160, 1.1, "lie", -1)]:
            reindeer(figures, rng, x, base, size, pose, facing)
        front = A.new_layer()  # spruces framing the view as it passes, nearest of all
        for x, base, h in [(14, 190, 150), (236, 192, 160), (826, 192, 150)]:
            snowy_spruce(front, rng, s(x), s(base), s(h), s(h * 0.3), depth=5, shadowed=0.35)
        img.alpha_composite(front)
        covered = ImageChops.difference(sky_only.convert("RGB"), Image.alpha_composite(img, figures).convert("RGB")).convert("L")
        open_sky = covered.point(lambda v: 0 if v > 10 else 255).filter(ImageFilter.MinFilter(5))
        figures.alpha_composite(front)
        img = A.finish(img, rng, 0.03, NIGHT_GLAZE).convert("RGBA")
        img.alpha_composite(fine_paint(figures, rng))
        stars = star_layer(rng, W, H(), 4200, horizon)
        for layer in (stars.filter(ImageFilter.GaussianBlur(1.2)), stars):
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), open_sky))
            img.alpha_composite(layer)
        # The moon, low over the camp: it stays when the lights go out.
        moon = black()
        mx, my, mr = s(690), s(36), s(9)
        glow_pool(moon, mx, my, mr * 5, mr * 5, (90, 120, 180), 90, mr * 3)
        disc = Image.new("RGBA", (W, H()))
        dd = ImageDraw.Draw(disc)
        dd.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(236, 238, 226, 255))
        for _ in range(9):  # its seas
            ox, oy, r = rng.uniform(-0.6, 0.5) * mr, rng.uniform(-0.6, 0.5) * mr, rng.uniform(0.15, 0.35) * mr
            dd.ellipse([mx + ox - r, my + oy - r, mx + ox + r, my + oy + r], fill=(196, 200, 196, 255))
        moon.alpha_composite(disc.filter(ImageFilter.GaussianBlur(1.2)))
        moon_mask = ImageChops.multiply(open_sky, Image.new("L", (W, H()), 255))
        img = screen(img, Image.composite(moon, black(), moon_mask))
        light = black()
        kota_light(light, door, s(756), s(110))
        img = screen(img, light)
        A.save(img.convert("RGB"), "intro/fells.png")

        # The blazing sky over the whole panorama, and the fox's trail of sparks climbing
        # from the ridge into it.
        size = (W, s(120))
        curtains = []
        for i in range(5):
            x0 = s(-20 + i * 175)
            curtains.append(([(x0 + s(dx), s(y)) for dx, y in ((0, 60), (60, 86), (120, 66), (180, 92), (230, 74))], s(rng.uniform(46, 70)), 255, rng.uniform(-0.3, 0.1)))
            curtains.append(([(x0 + s(dx), s(y)) for dx, y in ((20, 30), (90, 42), (160, 28), (220, 46))], s(rng.uniform(26, 40)), 160, -0.2))
        light = aurora_light(rng, size, curtains)
        trail = Image.new("RGBA", size)
        # It follows the fox's path up from the ridge (`runners` in FOX_INTRO, src/levels.rs).
        line = smooth([(s(166), s(100)), (s(196), s(70)), (s(250), s(44)), (s(360), s(30)), (s(520), s(28)), (s(580), s(32))], 300)
        td = ImageDraw.Draw(trail)
        for i, (p, q) in enumerate(zip(line, line[1:])):
            t = i / len(line)
            td.line([p, q], fill=A.mix(EMBER, GREEN, t) + (int(230 * (1 - t * 0.5)),), width=max(1, int(s(1.0))))
        for _ in range(4000):
            t = rng.random()
            x, y = line[int(t * (len(line) - 1))]
            r = rng.uniform(0.5, 2.0)
            x, y = x + rng.gauss(0, s(1.5 + 4 * t)), y + rng.gauss(0, s(1.5 + 4 * t)) - rng.random() * s(8)
            td.ellipse([x - r, y - r, x + r, y + r], fill=A.mix(EMBER, GREEN, t) + (255,))
        light.alpha_composite(trail.filter(ImageFilter.GaussianBlur(s(3))))
        light.alpha_composite(trail.filter(ImageFilter.GaussianBlur(s(0.6))))
        light.alpha_composite(trail)
        A.save(as_glow(light, 1.8), "intro/aurora.png")

    for frame in range(4):  # the fox bounding along the ridge and up into the sky
        A.save(fire_fox(("run", frame), 560 + frame, detail=2, heat=1.2, sparks=80), f"intro/fox_run_{frame}.png")
    # The fox's last spark, glimmering in the snow.
    size = 256
    img = Image.new("RGBA", (size, size))
    for r, col, a in ((size * 0.28, (255, 120, 40), 90), (size * 0.14, (255, 170, 70), 200), (size * 0.05, (255, 240, 200), 255)):
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], fill=a)
        lay = Image.new("RGBA", (size, size), col + (255,))
        lay.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.45)))
        img.alpha_composite(lay)
    A.save(img, "intro/spark.png")


def card():
    """The menu's card: the fire fox standing on the fell top, its tail ablaze and its
    sparks climbing into a sky full of the lights it has made."""
    rng = random.Random(551)
    img, sky_only = fell_scene(rng)
    painted = A.finish(img, rng, 0.04, NIGHT_GLAZE).convert("RGBA")
    covered = ImageChops.difference(sky_only.convert("RGB"), img.convert("RGB")).convert("L")
    open_sky = covered.point(lambda v: 0 if v > 10 else 255).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(2))
    curtains = [
        ([(-s(20), s(30)), (s(50), s(52)), (s(100), s(38)), (s(150), s(58)), (s(200), s(66)), (s(250), s(54)), (s(340), s(70))], s(66), 255, -0.3),
        ([(-s(10), s(12)), (s(70), s(24)), (s(140), s(14)), (s(210), s(30)), (s(340), s(22))], s(34), 150, -0.2),
    ]
    sky_light = aurora_light(rng, (W, H()), curtains)
    painted = screen(painted, Image.composite(sky_light, black(), open_sky))
    stars = star_layer(rng, W, H(), 300, s(100))
    stars.putalpha(ImageChops.multiply(stars.getchannel("A"), open_sky.point(lambda v: v // 2)))
    painted.alpha_composite(stars)
    # The fox, large, and the trail of sparks spiralling up from its tail into the lights.
    fox = fire_fox("stand", 552, detail=3, heat=1.1, sparks=160)
    fw = s(120)
    fox = fox.resize((fw, fw // 2), Image.LANCZOS)
    fx, fy = s(118), s(140) - fw // 2
    trail = Image.new("RGBA", (W, H()))
    td = ImageDraw.Draw(trail)
    tail_tip = (fx + fw * 0.95, fy + fw // 2 * 0.1)
    line = smooth([tail_tip, (tail_tip[0] + s(14), tail_tip[1] - s(20)), (tail_tip[0] - s(6), tail_tip[1] - s(44)), (tail_tip[0] + s(30), tail_tip[1] - s(70))], 200)
    for _ in range(1800):
        t = rng.random()
        x, y = line[int(t * (len(line) - 1))]
        x, y = x + rng.gauss(0, s(1 + 5 * t)), y + rng.gauss(0, s(1 + 5 * t))
        r = rng.uniform(0.6, 2.2) * (1.3 - t * 0.6)
        td.ellipse([x - r, y - r, x + r, y + r], fill=A.mix((255, 210, 120), GREEN, t) + (int(255 * (1 - t * 0.6)),))
    glow = black()
    glow.alpha_composite(trail.filter(ImageFilter.GaussianBlur(s(1.5))))
    glow.alpha_composite(trail)
    glow_pool(glow, fx + fw * 0.8, fy + fw // 2 * 0.95, s(26), s(5), FIRELIGHT, 120, s(6))  # its fire on the snow
    painted = screen(painted, glow)
    shadow = Image.new("RGBA", (W, H()))  # its shadow on the snow, thrown by the sky
    ImageDraw.Draw(shadow).ellipse([fx + fw * 0.12, fy + fw * 0.46, fx + fw * 0.7, fy + fw * 0.51], fill=(10, 16, 40, 150))
    painted.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s(1.5))))
    # In the night's cold light, like everything else; the tail keeps its own fire.
    alpha = fox.getchannel("A")
    cold = ImageChops.multiply(fox.convert("RGB"), Image.new("RGB", fox.size, (178, 192, 236))).convert("RGBA")
    cold.putalpha(alpha)
    flames = fire_fox("stand", 552, detail=3, heat=1.1, sparks=160, body=False).resize(fox.size, Image.LANCZOS)
    cold.alpha_composite(flames)
    painted.alpha_composite(cold, (int(fx), int(fy)))
    crop = painted.crop((s(70), 0, s(70) + s(192), s(144)))
    A.save(crop.convert("RGB").resize((640, 480), Image.LANCZOS), "cards/fox.png")


def title():
    A.title_logo("THE FIRE FOX", "intro/title_fox.png")


def rooms():
    camp()
    lake()
    forest()
    fell()
    den()


def fox_tale():
    rooms()
    characters()
    objects()
    items()
    effects()
    intro_fells()
    card()
    title()


if __name__ == "__main__":
    for name in sys.argv[1:] or ["fox_tale"]:
        globals()[name]()
    print("art written to", A.ASSETS)
