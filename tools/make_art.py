#!/usr/bin/env python3
"""Paints the placeholder art in assets/, in the manner of Werner Holmberg
(1830-1860): golden side light through spruces, warm sandy roads, mossy rocks,
hazy distances and soft cumulus skies. Replace any PNG with real art.

Everything is laid out in room units (a room is 320x144, the same top-left
coordinates as the hotspot rectangles in assets/story.txt) and painted at
SCALE times that resolution. Sprites must keep the size of their hotspot
rectangle times SCALE, since the game draws them at the rectangle's size.

Usage: python3 tools/make_art.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCALE = 4
W, H = 320 * SCALE, 144 * SCALE

# Holmberg's palette: warm light, deep spruce greens, ochre earth.
# Dawn, the morning after the fire went out: a cool pale sky warming to rose at the
# horizon, the sun just risen on the left, cool blue-violet shadows, mist everywhere.
SKY_TOP = (120, 148, 194)  # cool, pale blue overhead
SKY_HAZE = (250, 212, 196)  # peach and rose at the horizon
SUN = (255, 206, 172)  # rosy gold, low sunlight
DAWN_GLAZE = (255, 196, 178)  # the warm cast over the whole painting
DAWN_SHADE = (28, 32, 68)  # shadows go blue-violet at dawn
DAWN_MIST = (230, 230, 240)
SPRUCE_DARK = (22, 38, 28)
SPRUCE_MID = (40, 62, 40)
SPRUCE_LIGHT = (112, 124, 58)
DISTANT = (118, 138, 132)
GRASS = [(74, 92, 42), (96, 112, 50), (58, 74, 36), (128, 132, 62)]
ROAD = (196, 164, 112)
BARK = (64, 44, 30)
LOG = (112, 86, 60)


def s(v):
    """Room units to canvas pixels."""
    return v * SCALE


def clamp(c):
    return max(0, min(255, int(c)))


def vary(color, rng, amount=10, alpha=255):
    return tuple(clamp(v + rng.uniform(-amount, amount)) for v in color[:3]) + (alpha,)


def mix(a, b, t):
    return tuple(clamp(x + (y - x) * t) for x, y in zip(a, b))


def new_layer(w=None, h=None):
    return Image.new("RGBA", (w or W, h or H), (0, 0, 0, 0))


class Canvas:
    """ImageDraw on an RGBA layer replaces a pixel's alpha with the mark's alpha, so a
    translucent mark punches a hole in anything solid underneath. Marks made through
    this class are drawn opaque on a scratch layer and composited at their alpha."""

    def __init__(self, layer):
        self.layer = layer
        self.d = ImageDraw.Draw(layer, "RGBA")
        self.pending = []

    def __getattr__(self, name):
        return getattr(self.d, name)

    def soft(self, shape, *args, fill, **kwargs):
        self.pending.append((shape, args, fill, kwargs))

    def flush(self):
        by_alpha = {}
        for shape, args, fill, kwargs in self.pending:
            by_alpha.setdefault(fill[3] if len(fill) > 3 else 255, []).append((shape, args, fill[:3], kwargs))
        for alpha, marks in by_alpha.items():
            scratch = new_layer(*self.layer.size)
            sd = ImageDraw.Draw(scratch)
            for shape, args, rgb, kwargs in marks:
                getattr(sd, shape)(*args, fill=rgb + (255,), **kwargs)
            scratch.putalpha(scratch.getchannel("A").point(lambda v: v * alpha // 255))
            self.layer.alpha_composite(scratch)
        self.pending = []


def paint(base, layer, blur=0.0):
    if isinstance(layer, Canvas):
        layer.flush()
        layer = layer.layer
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def dab(d, x, y, rx, ry, color, angle=0.0, points=8):
    """One brush mark: a rotated ellipse-ish polygon. Translucent marks on a Canvas blend properly."""
    ca, sa = math.cos(angle), math.sin(angle)
    pts = []
    for i in range(points):
        a = 2 * math.pi * i / points
        px, py = rx * math.cos(a), ry * math.sin(a)
        pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
    if isinstance(d, Canvas) and len(color) > 3 and color[3] < 255:
        d.soft("polygon", pts, fill=color)
    else:
        d.polygon(pts, fill=color)


def save(img, path):
    out = ASSETS / path
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


# ---------------------------------------------------------------- landscape pieces


def shifted(mask, dx, dy):
    out = Image.new("L", mask.size, 0)
    out.paste(mask, (int(dx), int(dy)))
    return out


def sky(img, rng, top=SKY_TOP, haze=SKY_HAZE, horizon=0.75, clouds=6, cloud_top=0.04, cloud_bottom=0.4, seamless=False):
    """Luminous sky: deep blue overhead, warm haze at the horizon, and cumulus with
    sunlit upper-left edges and cool grey-violet undersides."""
    d = ImageDraw.Draw(img)
    hz = int(H * horizon)
    warm = (255, 196, 170)  # the rose-gold band where the sun is rising
    for y in range(H):
        t = min(1.0, y / hz)
        col = mix(top, haze, t ** 1.3)
        col = mix(col, warm, max(0.0, t - 0.75) * 1.4)
        d.line([(0, y), (W, y)], fill=col + (255,))
    for _ in range(clouds):
        size = rng.uniform(s(22), s(42))
        margin = size * 3.6 if seamless else -W * 0.05  # so a scrolling sky tiles without a seam
        cx = rng.uniform(margin, W - margin)
        base = rng.uniform(H * cloud_top + s(14), H * cloud_bottom)
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for _ in range(int(size / 1.5)):
            x = cx + rng.gauss(0, size * 1.1)
            r = rng.uniform(size * 0.25, size * 0.55) * (1.2 - abs(x - cx) / (size * 3))
            if r <= 0:
                continue
            y = base - abs(rng.gauss(0, size * 0.35)) - r * 0.3  # heaped upward from a flat base
            md.ellipse([x - r, y - r * 0.8, x + r, min(base, y + r * 0.8)], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(s(1.6)))
        dist = (base / H) / cloud_bottom  # lower clouds are further away: hazier
        shade = mix((122, 120, 164), haze, 0.15 + 0.4 * dist)  # lavender undersides
        lit = mix((255, 214, 196), haze, 0.15 * dist)  # tops touched pink and gold by the rising sun
        # Sunlit across the upper body, fading to a cool grey-violet base.
        body = Image.new("RGBA", (W, H))
        bd = ImageDraw.Draw(body)
        top_y = base - size * 1.4
        for y in range(max(0, int(top_y - size)), min(H, int(base + s(4)))):
            t = min(1.0, max(0.0, (y - top_y) / (base - top_y)))
            bd.line([(0, y), (W, y)], fill=mix(lit, shade, t ** 1.6) + (255,))
        body.putalpha(mask.point(lambda v: v * 240 // 255))
        img.alpha_composite(body)
        # A soft brighter crown where the heaped tops catch the sun.
        crown = ImageChops.subtract(mask, shifted(mask, 0, -s(5))).filter(ImageFilter.GaussianBlur(s(3)))
        light = Image.new("RGBA", (W, H), (255, 252, 242, 255))
        light.putalpha(ImageChops.multiply(crown.point(lambda v: min(255, int(v * 1.2))), mask).point(lambda v: v * 150 // 255))
        img.alpha_composite(light)


def hills(img, rng, base_y, height, color, fade, x0=0, x1=W):
    """A far ridge of blue-grey wooded hills, the Häme landscape's horizon."""
    color = mix(color, SKY_HAZE, fade)
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    phase = [rng.uniform(0, 6.28) for _ in range(3)]
    pts = [(x0, H)]
    for x in range(int(x0), int(x1) + 8, 8):
        u = x / W
        y = base_y - height * (0.55 + 0.25 * math.sin(u * 5 + phase[0]) + 0.15 * math.sin(u * 13 + phase[1])
                               + 0.05 * math.sin(u * 37 + phase[2]))
        pts.append((x, y))
    pts.append((x1, H))
    d.polygon(pts, fill=color + (255,))
    for _ in range(int((x1 - x0) / 3)):  # the soft texture of forest on far hills
        x = rng.uniform(x0, x1)
        y = base_y - rng.uniform(0, height * 0.5)
        dab(d, x, y, rng.uniform(3, 8), rng.uniform(2, 4), vary(mix(color, (60, 80, 70), 0.12), rng, 5), 0, 6)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask))
    paint(img, lay, 1.5)


def lake(img, rng, y0, y1, x0=0, x1=W, near=(214, 222, 222), far=(128, 150, 160), glint=(246, 240, 222)):
    """Still water mirroring the bright sky, with soft horizontal glints."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(x0, y), (x1, y)], fill=mix(near, far, t) + (255,))
    for _ in range(int((x1 - x0) / 4)):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        dab(d, x, y, rng.uniform(6, 20), rng.uniform(0.6, 1.2), vary(glint, rng, 6), 0, 6)
    paint(img, lay, 0.8)


def treeline(img, rng, base_y, height, color, blur, fade, count=60, x0=-s(4), x1=W + s(4)):
    """Distant forest edge: a wall of small spruces, paler and bluer with distance."""
    lay = new_layer()
    ImageDraw.Draw(lay).rectangle([x0, base_y - height * 0.15, x1, base_y + s(2)], fill=mix(color, SKY_HAZE, fade / 255) + (255,))
    paint(img, lay, blur)
    x = x0
    while x < x1:
        h = height * rng.uniform(0.55, 1.0)
        spruce(img, rng, x, base_y, h, h * rng.uniform(0.28, 0.4), 0.5, 0.2, blur, 0.0, fade / 255)
        x += rng.uniform(s(3), s(7))


def shadow(img, pts, alpha=90, blur=6):
    """A cast shadow on the ground: light comes from the upper left."""
    lay = new_layer()
    ImageDraw.Draw(lay).polygon(pts, fill=(28, 26, 16, alpha))
    paint(img, lay, blur)


def spruce(img, rng, cx, base, height, width, density=1.0, light=1.0, blur=0.6, trunk_h=0.1, fade=0.0, shadowed=0.0):
    """A Finnish spruce: a narrow spire, then drooping branch tiers hung with dark
    branchlets, a few gaps showing the sky, and warm light caught on the left edges."""
    night = (8, 12, 14)  # `shadowed` sinks a tree into shade, leaving only a rim of light
    dark = mix(mix(SPRUCE_DARK, SKY_HAZE, fade), night, shadowed)
    mid = mix(mix(SPRUCE_MID, SKY_HAZE, fade), night, shadowed * 0.85)
    lit = mix(mix(SPRUCE_LIGHT, SKY_HAZE, fade), night, shadowed * 0.4)
    bark = mix(BARK, SKY_HAZE, fade)
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    top = base - height
    d.polygon([(cx - width * 0.03, base), (cx - width * 0.008, top + height * 0.1),
               (cx + width * 0.008, top + height * 0.1), (cx + width * 0.03, base)], fill=bark + (255,))
    y = top + height * 0.02
    while y < base - height * trunk_h:
        t = (y - top) / height
        env = width / 2 * (0.04 + 0.96 * t ** 0.8)
        for side in (-1, 1):
            if t > 0.15 and rng.random() < 0.12:
                continue  # a gap in the boughs
            length = env * rng.uniform(0.55, 1.12)
            droop = length * rng.uniform(0.18, 0.45)
            steps = max(2, int(length / s(1.1) * density))
            prev = (cx, y)
            for i in range(1, steps + 1):
                f = i / steps
                x = cx + side * length * f
                yy = y + droop * f * f
                d.line([prev, (x, yy)], fill=dark + (255,), width=max(1, round(s(0.35) * (1.4 - f))))
                prev = (x, yy)
                hang = s(0.8 + 2.4 * t) * rng.uniform(0.6, 1.25) * (1.2 - 0.5 * f)
                col = vary(dark if rng.random() < 0.6 else mid, rng, 5)
                dab(d, x, yy + hang * 0.45, s(0.75) * rng.uniform(0.8, 1.3), hang * 0.6, col, side * 0.25, 6)
                if side < 0 and f > 0.35 and rng.random() < 0.28 * light:
                    dab(d, x + s(0.2), yy - s(0.1), s(0.8), s(0.35), vary(lit, rng, 10), -0.3, 6)
                elif side > 0 and rng.random() < 0.05 * light:
                    dab(d, x, yy, s(0.5), s(0.25), vary(mid, rng, 8), 0.3, 6)
        y += rng.uniform(s(1.1), s(2.0)) * (0.8 + 0.4 * t)
    paint(img, lay, blur)


def birch(img, rng, x0, x1, top, base, crown=True):
    """White birch trunk with black marks, shaded on the right, leafy crown above."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    w = x1 - x0
    for i in range(int(w)):
        f = i / w
        d.line([(x0 + i, top), (x0 + i, base)], fill=mix((238, 232, 214), (120, 122, 118), f ** 1.5) + (255,))
    for _ in range(int((base - top) * w / 340)):
        y = rng.uniform(top, base)
        ln = rng.uniform(4, w * 0.4)
        x = rng.uniform(x0 + ln / 2, x1 - ln / 2)
        dab(d, x, y, ln / 2, rng.uniform(1, 2.4), (36, 32, 30, 255), rng.uniform(-0.12, 0.12), 6)
    # Rough dark bark at the foot of an old birch.
    for _ in range(140):
        y = base - abs(rng.gauss(0, s(6)))
        x = rng.uniform(x0 + 3, x1 - 3)
        dab(d, x, y, rng.uniform(2, 5), rng.uniform(3, 8), vary((56, 50, 42), rng, 10), 0, 6)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([x0, top, x1, base], fill=255)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask))
    paint(img, lay, 0.5)
    if crown:
        leaves(img, rng, (x0 + x1) / 2, top - s(4), w * 2.4, s(26))


def leaves(img, rng, cx, cy, spread, height, count=500):
    """Birch foliage: drooping clusters, darker inside, sunlit on the left."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for _ in range(count // 25):
        kx = cx + rng.gauss(0, spread / 3)
        ky = cy + rng.gauss(0, height / 3)
        size = rng.uniform(s(4), s(9))
        for _ in range(40):
            x = kx + rng.gauss(0, size / 2)
            y = ky + abs(rng.gauss(0, size / 1.6))  # clusters hang down
            light = 0.55 + (kx - x) / size * 0.4 + (cx - kx) / spread * 0.6 - (y - ky) / size * 0.3
            col = mix((40, 60, 30), (150, 156, 72), max(0.0, min(1.0, light + rng.uniform(-0.2, 0.2))))
            dab(d, x, y, rng.uniform(2.5, 5), rng.uniform(1.5, 3), col + (255,), rng.uniform(0.8, 2.2), 6)
    paint(img, lay, 0.7)


def pine_trunk(img, rng, x0, x1, top, base):
    lay = new_layer()
    d = Canvas(lay)
    w = x1 - x0
    for i in range(int(w)):
        f = i / w
        d.line([(x0 + i, top), (x0 + i, base)], fill=mix((200, 124, 72), (70, 42, 30), f ** 1.1) + (255,))
    for _ in range(int((base - top) / 3)):
        y = rng.uniform(top, base)
        dab(d, rng.uniform(x0, x1), y, rng.uniform(2, w * 0.3), rng.uniform(1, 2), (70, 40, 28, 160), 0, 6)
    d.flush()
    paint(img, lay, 0.6)


def ground(img, rng, top, colors=GRASS, strokes=9000, light_x=0.25):
    """Meadow of short upward strokes; warmer and lighter toward the sunlit side."""
    lay = new_layer()
    d = Canvas(lay)
    d.rectangle([0, top, W, H], fill=colors[0] + (255,))
    for _ in range(strokes):
        x = rng.uniform(0, W)
        y = rng.uniform(top, H)
        depth = (y - top) / (H - top)
        ln = s(0.8) + depth * s(2.5)
        col = rng.choice(colors)
        sun = max(0.0, 1 - abs(x / W - light_x) * 1.6) * 0.35
        col = mix(col, SUN, sun * rng.random())
        d.line([(x, y), (x + rng.uniform(-2, 2), y - ln)], fill=col + (255,), width=max(1, int(1 + depth * 2)))
    d.flush()
    paint(img, lay, 0.4)


def road(img, rng, pts, color=ROAD):
    """Holmberg's sandy road: warm ochre with ruts and pale sunlit patches."""
    lay = new_layer()
    d = Canvas(lay)
    d.polygon(pts, fill=color + (255,))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    for _ in range(2500):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        dab(d, x, y, rng.uniform(3, 10), rng.uniform(1, 2.5), vary(color, rng, 18, 150), rng.uniform(-0.1, 0.1))
    d.flush()
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask.filter(ImageFilter.GaussianBlur(3))))
    paint(img, lay, 0.6)


def road_details(img, rng, top_y, ruts=(s(124), s(133)), x0=0, x1=W):
    """What makes a painted road read as a road: wheel ruts with lit rims, pebbles,
    and grass tufts creeping in along the edges."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for y0 in ruts:
        pts = [(x, y0 + math.sin(x / s(30) + y0) * s(1.2)) for x in range(int(x0), int(x1) + 8, 8)]
        d.line(pts, fill=(146, 116, 78, 255), width=round(s(1.1)))
        d.line([(x, y + s(0.9)) for x, y in pts], fill=(222, 196, 146, 255), width=round(s(0.5)))
    for _ in range(int((x1 - x0) / 5)):
        x, y = rng.uniform(x0, x1), rng.uniform(top_y + s(4), H)
        r = rng.uniform(1.5, 4.5)
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=vary((150, 140, 124), rng, 20))
        d.arc([x - r, y - r * 0.6, x + r, y + r * 0.6], 180, 300, fill=(230, 220, 196, 255), width=1)
    for _ in range(int((x1 - x0) / 1.5)):
        x = rng.uniform(x0, x1)
        y = top_y + abs(rng.gauss(0, s(3)))
        d.line([(x, y), (x + rng.uniform(-2, 2), y - rng.uniform(s(1), s(3)))],
               fill=vary(rng.choice(GRASS), rng, 12), width=2)
    for _ in range(14):  # tufts out in the road
        cx, cy = rng.uniform(x0, x1), rng.uniform(top_y + s(10), H)
        for _ in range(12):
            d.line([(cx + rng.uniform(-6, 6), cy), (cx + rng.uniform(-10, 10), cy - rng.uniform(s(1), s(2.5)))],
                   fill=vary(rng.choice(GRASS), rng, 12), width=2)
    paint(img, lay, 0.6)


def rock(img, rng, x0, y0, x1, y1, moss=0.5):
    lay = new_layer()
    d = Canvas(lay)
    d.ellipse([x0 - 4, y1 - (y1 - y0) * 0.25, x1 + 8, y1 + 6], fill=(20, 22, 14, 120))  # cast shadow
    d.ellipse([x0, y0, x1, y1], fill=(112, 110, 100, 255))
    for _ in range(int((x1 - x0) * 2)):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        f = (x - x0) / (x1 - x0)
        col = mix((182, 176, 160), (70, 68, 62), f)
        dab(d, x, y, rng.uniform(3, 7), rng.uniform(2, 4), col + (160,), rng.uniform(0, 3))
    for _ in range(int((x1 - x0) * moss)):
        x = rng.uniform(x0 + 4, x1 - 4)
        y = y0 + abs(rng.gauss(0, (y1 - y0) * 0.18))
        dab(d, x, y, rng.uniform(3, 7), rng.uniform(2, 3), vary((96, 112, 48), rng, 16, 220), rng.uniform(0, 3))
    d.flush()
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([x0 - 6, y0 - 6, x1 + 10, y1 + 8], fill=255)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask))
    paint(img, lay, 0.7)


WEATHERED = (140, 124, 102)  # sun-silvered pine logs


def log_shade(t, across):
    """Brightness of a point on a round log: t runs top (0) to bottom (1) of the log,
    `across` is 0 at the sunlit end of the wall and 1 at the far end."""
    roundness = 0.62 + 0.5 * math.sin(math.pi * (0.08 + 0.8 * t)) - 0.25 * t
    return roundness * (1.08 - 0.22 * across)


def farm_building(img, rng, x0, x1, side_x1, ground, wall_h, roof_h, rise, door=None, windows=(), side_window=None,
                  chimney=False, sooty=False):
    """A Finnish log building seen at an angle, as Holmberg painted them: the gable end
    faces us in the sun, the long side recedes in shadow, under a weathered board roof.
    All arguments are room units."""
    X0, X1, XS, G = s(x0), s(x1), s(side_x1), s(ground)
    top = G - s(wall_h)
    peak = ((X0 + X1) / 2, top - s(roof_h))
    ov = s(4)  # roof overhang
    R = s(rise)
    dw = XS - X1
    log_h = s(3.2)
    lay = new_layer()
    d = Canvas(lay)

    # Side wall, in shadow, logs following its perspective slope.
    y = top
    while y < G:
        for py in range(int(log_h)):
            t = py / log_h
            col = mix(mix(WEATHERED, (52, 46, 44), 0.55), (24, 22, 26), 0.25 * (1 - log_shade(t, 0.5)))
            d.line([(X1, y + py), (XS, y + py - R)], fill=col + (255,), width=1)
        d.line([(X1, y + log_h - 1), (XS, y + log_h - 1 - R)], fill=(28, 24, 22, 255), width=2)
        y += log_h
    if side_window:
        wx0, wy0, wx1, wy1 = [s(v) for v in side_window]
        k0, k1 = (wx0 - X1) / dw * R, (wx1 - X1) / dw * R
        d.polygon([(wx0, wy0 - k0), (wx1, wy0 - k1), (wx1, wy1 - k1), (wx0, wy1 - k0)], fill=(96, 86, 72, 255))
        m = s(0.8)
        d.polygon([(wx0 + m, wy0 - k0 + m), (wx1 - m, wy0 - k1 + m), (wx1 - m, wy1 - k1 - m), (wx0 + m, wy1 - k0 - m)],
                  fill=(70, 84, 92, 255))
    # Shadow under the side eave.
    d.soft("polygon", [(X1, top), (XS, top - R), (XS, top - R + s(5)), (X1, top + s(5))], fill=(10, 8, 6, 120))

    # Gable wall in the sun: round logs, moss chinking between them.
    y = top
    while y < G:
        for py in range(int(log_h)):
            t = py / log_h
            for seg in range(4):  # brighter at the sunlit (left) end
                sx0 = X0 + (X1 - X0) * seg / 4
                sx1 = X0 + (X1 - X0) * (seg + 1) / 4
                b = log_shade(t, seg / 3)
                col = tuple(clamp(c * b) for c in WEATHERED)
                d.line([(sx0, y + py), (sx1, y + py)], fill=col + (255,), width=1)
        d.line([(X0, y + log_h - 1), (X1, y + log_h - 1)], fill=(34, 28, 22, 255), width=2)
        for _ in range(int((X1 - X0) / 18)):  # moss and tow stuffed in the seams
            dab(d, rng.uniform(X0, X1), y + log_h - 1, rng.uniform(3, 8), 1.2, vary((104, 112, 60), rng, 14, 220), 0, 6)
        for _ in range(int((X1 - X0) / 10)):  # grain and checks in the wood
            gx = rng.uniform(X0, X1)
            d.line([(gx, y + rng.uniform(1, log_h - 2)), (gx + rng.uniform(6, 26), y + rng.uniform(1, log_h - 2))],
                   fill=vary((88, 76, 62), rng, 10, 150), width=1)
        y += log_h
    # Log ends at both corners, notched and sticking out.
    y = top
    while y < G:
        for cx in (X0 - s(0.6), X1 + s(0.6)):
            d.ellipse([cx - log_h * 0.6, y, cx + log_h * 0.6, y + log_h], fill=(176, 150, 112, 255))
            d.ellipse([cx - log_h * 0.32, y + log_h * 0.25, cx + log_h * 0.32, y + log_h * 0.75], outline=(130, 104, 76, 255))
            d.arc([cx - log_h * 0.6, y, cx + log_h * 0.6, y + log_h], 30, 150, fill=(90, 70, 52, 255), width=2)
        y += log_h

    for wx0, wy0, wx1, wy1 in windows:  # small windows of four panes reflecting the sky
        wx0, wy0, wx1, wy1 = s(wx0), s(wy0), s(wx1), s(wy1)
        f = s(1.1)
        d.rectangle([wx0 - f, wy0 - f, wx1 + f, wy1 + f * 1.6], fill=(178, 160, 128, 255))
        for py in range(int(wy0), int(wy1)):
            t = (py - wy0) / max(1, wy1 - wy0)
            d.line([(wx0, py), (wx1, py)], fill=mix((196, 210, 214), (70, 84, 92), t) + (255,))
        d.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], fill=(150, 132, 104, 255), width=round(s(0.5)))
        d.line([(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)], fill=(150, 132, 104, 255), width=round(s(0.5)))
        d.line([(wx0 - f, wy1 + f * 1.6), (wx1 + f, wy1 + f * 1.6)], fill=(60, 48, 36, 255), width=2)

    if door:
        dx0, dy0, dx1, dy1 = [s(v) for v in door]
        f = s(1.2)
        d.rectangle([dx0 - f, dy0 - f, dx1 + f, dy1], fill=(160, 140, 108, 255))
        for i in range(int(dx1 - dx0)):
            t = i / (dx1 - dx0)
            d.line([(dx0 + i, dy0), (dx0 + i, dy1)], fill=mix((92, 70, 48), (50, 38, 28), t) + (255,))
        for k in range(1, 4):
            xx = dx0 + (dx1 - dx0) * k / 4
            d.line([(xx, dy0), (xx, dy1)], fill=(36, 26, 18, 255), width=2)
        for yy in (dy0 + (dy1 - dy0) * 0.25, dy0 + (dy1 - dy0) * 0.75):
            d.line([(dx0, yy), (dx1, yy)], fill=(70, 54, 38, 255), width=round(s(0.7)))
        d.ellipse([dx1 - s(2), (dy0 + dy1) / 2 - s(0.5), dx1 - s(1), (dy0 + dy1) / 2 + s(0.5)], fill=(40, 36, 34, 255))
        d.ellipse([dx0 - s(3), dy1 - s(1.2), dx1 + s(3), dy1 + s(2)], fill=(132, 128, 116, 255))  # doorstep stone

    if sooty:  # a smoke sauna's walls blacken near the top
        for i in range(int(s(14))):
            t = i / s(14)
            d.soft("line", [(X0, top + i), (X1, top + i)], fill=(20, 16, 14, int(170 * (1 - t) ** 1.5)), width=1)
        vx = (X0 + X1) / 2 + s(6)
        d.rectangle([vx, top + s(3), vx + s(6), top + s(6)], fill=(14, 10, 8, 255))  # smoke vent
        for _ in range(30):
            dab(d, vx + s(3) + rng.gauss(0, s(3)), top + s(2) - abs(rng.gauss(0, s(3))), rng.uniform(3, 7), rng.uniform(2, 4),
                (20, 16, 14, 90), 0, 6)

    # Gable triangle: vertical weatherboards, shaded under the eaves.
    gl, gr = (X0 - ov * 0.2, top), (X1 + ov * 0.2, top)
    d.polygon([gl, peak, gr], fill=mix(WEATHERED, (60, 52, 44), 0.25) + (255,))
    half = (gr[0] - gl[0]) / 2
    for bx in range(int(gl[0]), int(gr[0]), int(s(1.6))):
        h = s(roof_h) * max(0.0, 1 - abs(bx - peak[0]) / half)
        d.line([(bx, top), (bx, top - h)], fill=vary((70, 60, 50), rng, 8, 255), width=1)
    d.polygon([(gl[0], top + s(0.3)), (gr[0], top + s(0.3)), (gr[0], top - s(0.6)), (gl[0], top - s(0.6))], fill=(60, 50, 40, 255))

    # The roof's far slope, receding with the side wall; weathered boards, poles, moss.
    eave_r = (X1 + ov, top + s(1))
    plane = [peak, (peak[0] + dw, peak[1] - R), (eave_r[0] + dw, eave_r[1] - R), eave_r]
    d.polygon(plane, fill=(106, 100, 90, 255))
    for i in range(70):
        f = i / 70
        a = (peak[0] + dw * f, peak[1] - R * f)
        b = (eave_r[0] + dw * f, eave_r[1] - R * f)
        d.line([a, b], fill=vary((128, 120, 106) if i % 2 else (88, 82, 74), rng, 8), width=2)
    for f in (0.3, 0.68):  # weight poles laid along the roof
        a = (peak[0] + (eave_r[0] - peak[0]) * f, peak[1] + (eave_r[1] - peak[1]) * f)
        d.line([a, (a[0] + dw, a[1] - R)], fill=(64, 56, 46, 255), width=round(s(0.9)))
        d.line([(a[0], a[1] - s(0.4)), (a[0] + dw, a[1] - R - s(0.4))], fill=(150, 136, 112, 255), width=1)
    for _ in range(int(dw * 0.6)):
        f, g = rng.random(), rng.random() ** 0.6
        x = peak[0] + (eave_r[0] - peak[0]) * g + dw * f
        y = peak[1] + (eave_r[1] - peak[1]) * g - R * f
        dab(d, x, y, rng.uniform(3, 9), rng.uniform(1.5, 3), vary((98, 110, 54), rng, 14, 210), 0.5, 6)
    d.line([plane[2], plane[3]], fill=(30, 26, 22, 255), width=round(s(0.8)))  # eave edge
    if chimney:  # fieldstone chimney rising through the ridge
        f = 0.55
        cx, cy = peak[0] + dw * f, peak[1] - R * f
        cw, ch = s(6), s(11)
        d.polygon([(cx - cw / 2, cy + s(3)), (cx - cw / 2, cy - ch), (cx + cw / 2, cy - ch), (cx + cw / 2, cy + s(4))],
                  fill=(112, 106, 96, 255))
        for _ in range(26):
            sx = rng.uniform(cx - cw / 2, cx + cw / 2)
            sy = rng.uniform(cy - ch, cy + s(3))
            lit_ = (cx - sx) / cw + 0.5
            dab(d, sx, sy, rng.uniform(3, 6), rng.uniform(2, 4), vary(mix((84, 80, 74), (190, 182, 166), lit_), rng, 12), 0, 7)
        d.rectangle([cx - cw / 2 - s(1), cy - ch - s(1.4), cx + cw / 2 + s(1), cy - ch], fill=(80, 74, 66, 255))

    # Front edges of the roof: bargeboards, lit on the left slope, with shadow beneath.
    for a, b, col in (((X0 - ov, top + s(1)), peak, (176, 160, 134)), (peak, eave_r, (98, 88, 76))):
        d.soft("polygon", [a, b, (b[0], b[1] + s(3.5)), (a[0], a[1] + s(3.5))], fill=(14, 10, 8, 110))
        d.line([a, b], fill=col + (255,), width=round(s(1.3)))
    # Damp ground line along the foot of the walls.
    d.soft("polygon", [(X0 - s(2), G - s(1.5)), (X1, G - s(1.5)), (XS, G - R - s(1.5)), (XS, G - R + s(1)), (X1, G + s(1.5)),
                       (X0 - s(2), G + s(1.5))], fill=(30, 26, 18, 140))
    d.flush()
    paint(img, lay, 0.6)


def woodpile(img, rng, x0, y0, x1, y1):
    """Split birch logs stacked end-out under a little roof of boards."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    X0, Y0, X1, Y1 = s(x0), s(y0), s(x1), s(y1)
    r = s(1.3)
    y = Y1 - r
    while y > Y0 + r:
        x = X0 + r + rng.uniform(0, r)
        while x < X1 - r:
            rr = r * rng.uniform(0.8, 1.1)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(226, 220, 204, 255))  # birch bark rim
            d.ellipse([x - rr * 0.8, y - rr * 0.8, x + rr * 0.8, y + rr * 0.8], fill=vary((206, 172, 120), rng, 14))
            d.arc([x - rr, y - rr, x + rr, y + rr], 20, 160, fill=(80, 64, 48, 255), width=2)
            x += rr * 2.05
        y -= r * 1.85
    d.polygon([(X0 - s(1), Y0 + s(1)), (X1 + s(1), Y0 - s(1)), (X1 + s(1), Y0 + s(1)), (X0 - s(1), Y0 + s(3))], fill=(96, 88, 76, 255))
    paint(img, lay, 0.5)

def leafy_tree(img, rng, cx, base, height, width, fade=0.0, trunk=(70, 56, 44), white_trunk=False, shadowed=0.0):
    """A birch or alder: a slender trunk and rounded leaf masses, each lit from the upper
    left (light, mid and shadow greens), the way Holmberg built up foliage."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    trunk_col = mix((226, 220, 204) if white_trunk else trunk, SKY_HAZE, fade)
    tw = max(2.0, width * 0.05)
    d.polygon([(cx - tw, base), (cx - tw * 0.5, base - height * 0.75), (cx + tw * 0.5, base - height * 0.75), (cx + tw, base)],
              fill=trunk_col + (255,))
    if white_trunk:
        for _ in range(int(height / 10)):
            y = rng.uniform(base - height * 0.7, base)
            d.line([(cx - tw * 0.8, y), (cx + tw * 0.4, y)], fill=mix((40, 36, 32), SKY_HAZE, fade) + (255,), width=2)
    night = (10, 14, 10)
    shadow_c = mix(mix((34, 52, 30), SKY_HAZE, fade), night, shadowed)
    mid_c = mix(mix((78, 100, 44), SKY_HAZE, fade), night, shadowed * 0.8)
    lit_c = mix(mix((188, 178, 84), SKY_HAZE, fade * 0.8), night, shadowed * 0.35)
    trunk = mix(trunk, night, shadowed * 0.7)
    crown_y = base - height * 0.62
    masses = []
    for _ in range(int(9 + width / s(3))):
        mx = cx + rng.gauss(0, width * 0.2)
        my = crown_y + rng.gauss(0, height * 0.1)
        masses.append((mx, my, rng.uniform(width * 0.16, width * 0.28)))
    masses.sort(key=lambda m: m[1])
    for mx, my, r in masses:
        for _ in range(int(r * 1.6)):  # shadow body, drooping
            a = rng.uniform(0, 6.28)
            rr = r * math.sqrt(rng.random())
            dab(d, mx + math.cos(a) * rr, my + abs(math.sin(a)) * rr * 0.9, rng.uniform(2.5, 5), rng.uniform(2, 3.5),
                vary(shadow_c, rng, 6), rng.uniform(0, 3), 6)
        for _ in range(int(r * 1.1)):  # mid tones toward the light
            a = rng.uniform(math.pi * 0.9, math.pi * 1.9)
            rr = r * math.sqrt(rng.random()) * 0.9
            dab(d, mx + math.cos(a) * rr, my + math.sin(a) * rr * 0.8, rng.uniform(2.5, 5), rng.uniform(1.5, 3),
                vary(mid_c, rng, 8), rng.uniform(0, 3), 6)
        for _ in range(int(r * 0.7)):  # sunlit rim, upper left
            a = rng.uniform(math.pi * 1.0, math.pi * 1.5)
            rr = r * rng.uniform(0.55, 1.0)
            dab(d, mx + math.cos(a) * rr, my + math.sin(a) * rr * 0.8, rng.uniform(2, 4), rng.uniform(1.2, 2.4),
                vary(lit_c, rng, 12), rng.uniform(0, 3), 6)
    paint(img, lay, 0.5)


def meadow(img, rng, top, bottom, sunlit=0.5):
    """Patchy summer grass: broad swathes of olive, yellow-green and ochre, then blades."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    d.rectangle([0, top, W, bottom], fill=GRASS[0] + (255,))
    for _ in range(140):
        x, y = rng.uniform(0, W), rng.uniform(top, bottom)
        col = rng.choice([(118, 128, 56), (150, 150, 66), (86, 104, 46), (168, 154, 82), (70, 88, 44)])
        col = mix(col, SUN, sunlit * rng.random() * 0.5)
        dab(d, x, y, rng.uniform(s(4), s(14)), rng.uniform(s(1), s(3)), col + (255,), rng.uniform(-0.1, 0.1), 10)
    for _ in range(int(W * (bottom - top) / 120)):
        x, y = rng.uniform(0, W), rng.uniform(top, bottom)
        depth = (y - top) / max(1, bottom - top)
        col = mix(rng.choice(GRASS), SUN, sunlit * 0.4 * rng.random())
        d.line([(x, y), (x + rng.uniform(-2, 2), y - s(0.6) - depth * s(1.8))], fill=col + (255,), width=1 + int(depth * 2))
    for _ in range(int(W / 6)):  # a few flowers catching the light
        x, y = rng.uniform(0, W), rng.uniform(top, bottom)
        d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=rng.choice([(240, 232, 200), (226, 196, 90), (200, 120, 160)]) + (255,))
    paint(img, lay, 0.5)


def pole_fence(img, rng, x0, x1, y_back, y_front, fade=0.0):
    """Riukuaita: the old Finnish fence of slanted grey poles between upright pairs."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    post = mix((92, 84, 72), SKY_HAZE, fade)
    pole = mix((150, 140, 120), SKY_HAZE, fade)
    pole_dark = mix((96, 88, 76), SKY_HAZE, fade)
    height = s(9)
    x = x0
    while x < x1:
        y = y_back + (y_front - y_back) * (x - x0) / max(1, x1 - x0)
        for dx in (-s(0.4), s(0.4)):
            d.line([(x + dx, y), (x + dx, y - height)], fill=post + (255,), width=round(s(0.45)))
        x += s(5)
    x = x0 - s(4)
    while x < x1 + s(2):
        y = y_back + (y_front - y_back) * (x - x0) / max(1, x1 - x0)
        d.line([(x, y - s(0.5)), (x + s(9), y - height * 0.95)], fill=pole_dark + (255,), width=round(s(0.55)))
        d.line([(x, y - s(0.8)), (x + s(9), y - height * 0.95 - s(0.3))], fill=pole + (255,), width=round(s(0.3)))
        x += s(1.5)
    paint(img, lay, 0.6)


def ferns(img, rng, cx, cy, size, count=1):
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        x0 = cx + rng.uniform(-size, size)
        for _ in range(9):
            a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
            ln = size * rng.uniform(0.5, 1.0)
            pts = [(x0 + math.cos(a) * ln * t + math.sin(t * 3) * 2, cy + math.sin(a) * ln * t * 0.6 + (ln * t * 0.4) ** 1.2 * 0.08)
                   for t in (0, 0.25, 0.5, 0.75, 1.0)]
            col = vary(mix((60, 92, 40), (150, 160, 70), 0.5 - math.cos(a) * 0.5), rng, 10)
            d.line(pts, fill=col, width=2)
            for (px, py) in pts[1:]:
                dab(d, px, py, rng.uniform(2, 4), 1.2, col, a, 5)
    paint(img, lay, 0.5)


def oil_paint(img, rng, passes=((3.0, 0), (1.6, 10), (0.85, 18), (0.45, 30))):
    """Repaint the finished scene as an oil painting: rounds of brushstrokes, coarse to
    fine. Each stroke takes its colour from the scene and runs along the edges of forms;
    finer rounds only touch places where the painting still differs from the scene, so
    flat sky stays broad and soft while trees and buildings keep their detail."""
    src = img.convert("RGB")
    gray = src.convert("L").filter(ImageFilter.GaussianBlur(s(0.8)))
    gx = gray.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], 8, 128)).load()
    gy = gray.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], 8, 128)).load()
    canvas = src.filter(ImageFilter.GaussianBlur(s(passes[0][0])))
    for size, threshold in passes:
        r = s(size)
        ref = src.filter(ImageFilter.GaussianBlur(r * 0.5)).load()
        cur = canvas.load()
        d = ImageDraw.Draw(canvas, "RGBA")
        step = max(1, int(r))
        cells = [(x + rng.uniform(-r / 2, r / 2), y + rng.uniform(-r / 2, r / 2))
                 for y in range(0, H, step) for x in range(0, W, step)]
        rng.shuffle(cells)
        for x, y in cells:
            xi, yi = min(W - 1, max(0, int(x))), min(H - 1, max(0, int(y)))
            c = ref[xi, yi]
            if threshold:
                k = cur[xi, yi]
                if abs(c[0] - k[0]) + abs(c[1] - k[1]) + abs(c[2] - k[2]) < threshold:
                    continue
            dx, dy = gx[xi, yi] - 128, gy[xi, yi] - 128
            angle = math.atan2(dy, dx) + math.pi / 2 if dx * dx + dy * dy > 6 else rng.uniform(-0.25, 0.25)
            col = tuple(clamp(v + rng.uniform(-6, 6)) for v in c) + (230,)
            dab(d, x, y, r * rng.uniform(1.3, 2.3), r * rng.uniform(0.5, 0.75), col, angle, 8)
    return canvas.convert("RGBA")


def vignette_layer(strength=110):
    """Darkened corners and edges, as on an old varnished canvas."""
    small = Image.new("L", (64, 29))
    for y in range(29):
        for x in range(64):
            dx, dy = (x - 31.5) / 32, (y - 14) / 14.5
            small.putpixel((x, y), clamp(strength * max(0.0, dx * dx * 0.7 + dy * dy * 0.8 - 0.3)))
    dark = Image.new("RGBA", (W, H), (26, 16, 10, 255))
    dark.putalpha(small.resize((W, H), Image.BILINEAR))
    return dark


def finish(img, rng, warmth=0.07, glaze=DAWN_GLAZE, vignette=True):
    """Unify like an old varnished canvas: oil brushwork, a richer, more contrasting grade,
    a warm glaze, the weave of the canvas, and darkened corners."""
    img = oil_paint(img, rng)
    rgb = ImageEnhance.Color(ImageEnhance.Contrast(img.convert("RGB")).enhance(1.22)).enhance(1.12)
    img = rgb.convert("RGBA")
    img.alpha_composite(Image.new("RGBA", (W, H), glaze + (int(255 * warmth),)))
    weave = Image.new("L", (8, 8))
    for y in range(8):
        for x in range(8):
            weave.putpixel((x, y), 140 if (x % 4 < 2) ^ (y % 4 < 2) else 110)
    weave = weave.resize((16, 16), Image.BILINEAR)
    tile = Image.new("L", (W, H))
    for y in range(0, H, 16):
        for x in range(0, W, 16):
            tile.paste(weave, (x, y))
    img.alpha_composite(Image.merge("RGBA", [tile, tile, tile, Image.new("L", (W, H), 16)]))
    if vignette:
        img.alpha_composite(vignette_layer())
    return img.convert("RGB")


def sky_mask(open_sky, img):
    """White where the painted room still shows the open sky it started from."""
    diff = ImageChops.difference(open_sky.convert("RGB"), img.convert("RGB")).convert("L")
    return diff.point(lambda v: 255 if v <= 8 else 0).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.5))



def save_room(img, rng, path, open_sky, warmth=0.07, light=None):
    """Finish the room and cut out its sky, so the game's drifting sky shows through. The
    light overlay (sun, shade, pools of light) and the darkened corners are laid over the
    finished room as one layer, so they fall on the painting and the drifting sky alike."""
    out = finish(img, rng, warmth, vignette=False).convert("RGBA")
    out.putalpha(ImageChops.invert(open_sky))
    overlay = new_layer()
    if light is not None:
        overlay.alpha_composite(light)
    overlay.alpha_composite(vignette_layer())
    save(Image.alpha_composite(out, overlay), path)


def sunlight(sun, rays, glow=s(140), glow_alpha=150, color=SUN):
    """The low sun's glow and the god rays fanning out from it, on a layer of their own.
    `sun` may be off the canvas; each ray is (direction in degrees, width in degrees, alpha)."""
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    sx, sy = sun
    for r in range(int(glow), 0, -4):
        md.ellipse([sx - r, sy - r, sx + r, sy + r], fill=int(glow_alpha * (1 - r / glow) ** 2))
    rays_mask = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rays_mask)
    reach = W * 2
    for angle, width, alpha in rays:
        a0, a1 = math.radians(angle - width / 2), math.radians(angle + width / 2)
        rd.polygon([(sx, sy), (sx + math.cos(a0) * reach, sy + math.sin(a0) * reach),
                    (sx + math.cos(a1) * reach, sy + math.sin(a1) * reach)], fill=alpha)
    rays_mask = rays_mask.filter(ImageFilter.GaussianBlur(s(9))).point(lambda v: v // 2)
    layer = Image.new("RGBA", (W, H), color + (255,))
    layer.putalpha(ImageChops.lighter(mask.filter(ImageFilter.GaussianBlur(s(4))), rays_mask))
    return layer


def shade(img, rng, outline, strength=170, dapples=0, color=DAWN_SHADE, softness=2.5):
    # `img` may be the room or its light overlay (which also falls over the drifting sky).
    """Cool shadow over an area (room units), as if cast by trees out of the picture, with
    dapples of sun breaking through."""
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.polygon([(s(x), s(y)) for x, y in outline], fill=strength)
    xs, ys = [s(x) for x, _ in outline], [s(y) for _, y in outline]
    for _ in range(dapples):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        r = rng.uniform(s(1.5), s(5))
        md.ellipse([x - r, y - r * 0.4, x + r, y + r * 0.4], fill=0)
    layer = Image.new("RGBA", (W, H), color + (255,))
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(s(softness))))
    img.alpha_composite(layer)


def pool(img, cx, cy, rx, ry, strength=90, color=SUN):
    # Like shade(), this may go on the room or on its light overlay.
    """A pool of sunlight (room units)."""
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([s(cx - rx), s(cy - ry), s(cx + rx), s(cy + ry)], fill=strength)
    layer = Image.new("RGBA", (W, H), color + (255,))
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(s(min(rx, ry) * 0.6))))
    img.alpha_composite(layer)


def mist(img, rng, y, height, alpha=90, x0=0, x1=320, color=DAWN_MIST):
    """A band of mist lying low (room units), thickest in the middle, in soft drifts."""
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for _ in range(int((x1 - x0) / 3)):
        x = rng.uniform(x0, x1)
        r = rng.uniform(8, 24)
        md.ellipse([s(x - r), s(y - height * 0.35), s(x + r), s(y + height * 0.35)], fill=alpha)
    layer = Image.new("RGBA", (W, H), color + (255,))
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(s(height * 0.45))))
    img.alpha_composite(layer)


def canopy(img, rng, x0, y0, x1, y1, shadowed=0.7):
    """Leaves overhanging the picture from a tree out of frame, dark against the light,
    their edges catching the sun (room units)."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    night = (10, 14, 10)
    for _ in range(int((x1 - x0) * (y1 - y0) * 1.2)):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        # Dense toward the corner of the frame, thinning to ragged edges.
        edge = min(1.0, max(0.0, 1.6 - 1.4 * math.hypot((x - x0) / (x1 - x0), (y - y0) / (y1 - y0))))
        if rng.random() > edge:
            continue
        col = mix(mix((40, 58, 32), (96, 110, 50), rng.random()), night, shadowed * rng.uniform(0.7, 1.0))
        dab(d, s(x), s(y), rng.uniform(3, 7), rng.uniform(2, 4), col + (255,), rng.uniform(0, 3), 6)
    for _ in range(int((x1 - x0) * 1.5)):  # sun on the lowest leaves
        x = rng.uniform(x0, x1)
        y = y0 + (y1 - y0) * rng.uniform(0.3, 0.9)
        dab(d, s(x), s(y), rng.uniform(2, 4), rng.uniform(1, 2), (176, 166, 80, 200), rng.uniform(0, 3), 6)
    paint(img, lay, 0.6)

def sky_layer(path, seed, warmth=0.07, **kwargs):
    """A sky twice the room's width, painted the same way. The game scrolls it slowly."""
    global W
    base = W
    W = base * 2
    try:
        rng = random.Random(seed)
        img = Image.new("RGBA", (W, H))
        sky(img, rng, seamless=True, **kwargs)
        img = oil_paint(img, rng)
        img.alpha_composite(Image.new("RGBA", (W, H), DAWN_GLAZE + (int(255 * warmth),)))
    finally:
        W = base
    save(img.convert("RGB"), path)


# ---------------------------------------------------------------- rooms


def village():
    """A lakeside farmyard late on a summer afternoon: the low sun over the left edge,
    gold on the lake and the meadow, the near yard in the shade of trees out of frame."""
    rng = random.Random(1)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, horizon=0.58, clouds=5, cloud_bottom=0.42)
    open_sky = img.copy()
    hills(img, rng, s(80), s(16), (100, 98, 148), 0.3)  # violet against the dawn
    lake(img, rng, s(78), s(88), near=(250, 206, 190), far=(116, 126, 168), glint=(255, 224, 206))
    treeline(img, rng, s(80), s(12), (70, 84, 96), 1.6, 120, x0=0, x1=s(90))  # far shore
    mist(img, rng, s(83), s(9), 160, 40, 220)  # morning mist on the lake
    treeline(img, rng, s(92), s(30), (52, 72, 52), 1.0, 40, x0=-s(4), x1=s(98))
    treeline(img, rng, s(92), s(30), (52, 72, 52), 1.0, 40, x0=s(178), x1=W + s(4))
    leafy_tree(img, rng, s(8), s(100), s(70), s(34), white_trunk=True, shadowed=0.35)
    meadow(img, rng, s(88), s(118), 0.6)
    mist(img, rng, s(95), s(7), 90)  # and lying low over the meadow
    spruce(img, rng, s(104), s(98), s(52), s(17), 0.9, 0.9, 0.6, fade=0.08)
    spruce(img, rng, s(176), s(98), s(46), s(15), 0.9, 0.9, 0.6, fade=0.08)
    pole_fence(img, rng, s(96), s(182), s(100), s(102))
    road(img, rng, [(0, s(110)), (W * 0.4, s(108)), (W, s(111)), (W, H), (0, H)], (192, 160, 108))
    road_details(img, rng, s(109))
    shadow(img, [(s(88), s(100)), (s(88), s(104)), (s(124), s(114)), (s(100), s(101))], 80)
    shadow(img, [(s(300), s(104)), (s(300), s(106)), (s(320), s(114)), (s(320), s(105))], 80)
    woodpile(img, rng, 1, 84, 15, 100)
    farm_building(img, rng, 16, 66, 88, 100, 38, 14, 3, door=(33, 77, 45, 100), sooty=True)
    farm_building(img, rng, 184, 262, 300, 104, 50, 24, 5, door=(236, 76, 250, 104), windows=[(196, 66, 210, 77)],
                  side_window=(276, 68, 287, 78), chimney=True)
    shadow(img, [(s(230), s(115)), (s(246), s(115)), (s(266), s(119)), (s(240), s(119))], 110, 4)  # Kyllikki's
    # Cold hearth: a ring of stones round grey ash and charred logs.
    lay = new_layer()
    d = Canvas(lay)
    d.ellipse([s(132), s(103), s(172), s(119)], fill=(84, 80, 76, 255))
    for _ in range(80):
        dab(d, rng.uniform(s(138), s(166)), rng.uniform(s(106), s(116)), rng.uniform(3, 8), rng.uniform(2, 4),
            vary((138, 134, 128), rng, 20, 160), rng.uniform(0, 3))
    d.line([(s(142), s(109)), (s(161), s(113))], fill=(30, 24, 20, 255), width=round(s(2)))
    d.line([(s(144), s(114)), (s(162), s(107))], fill=(40, 30, 24, 255), width=round(s(2)))
    paint(img, d, 0.6)
    for a in range(12):
        ang = 2 * math.pi * a / 12
        x = s(152) + math.cos(ang) * s(21)
        y = s(111) + math.sin(ang) * s(8)
        rock(img, rng, x - s(4), y - s(3), x + s(4), y + s(3), 0.1)
    # Stump for the bread.
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for i in range(s(24)):
        f = i / s(24)
        d.line([(s(46) + i, s(104)), (s(46) + i, s(120))], fill=mix((150, 112, 74), (52, 38, 26), f) + (255,))
    for _ in range(40):
        x = rng.uniform(s(46), s(70))
        d.line([(x, s(105)), (x + rng.uniform(-2, 2), s(120))], fill=(44, 32, 22, 255), width=2)
    d.ellipse([s(46), s(101), s(70), s(108)], fill=(200, 164, 114, 255))
    for r in range(1, 6):
        d.ellipse([s(58) - r * s(2), s(104.5) - r * s(0.6), s(58) + r * s(2), s(104.5) + r * s(0.6)], outline=(150, 116, 78, 255))
    paint(img, lay, 0.6)
    shadow(img, [(s(66), s(117)), (s(70), s(120)), (s(86), s(121)), (s(82), s(117))], 90, 4)
    for x in (s(30), s(110), s(290)):
        rock(img, rng, x, s(122), x + s(rng.uniform(10, 16)), s(130), 0.6)
    spruce(img, rng, s(318), s(150), s(170), s(52), 1.2, 0.6, 0.5, shadowed=0.72)  # a dark spruce framing the right
    canopy(img, rng, -6, -6, 70, 24, 0.75)  # leaves overhanging the top-left corner
    # Light and shade go on an overlay that falls over the room and the drifting sky alike.
    light = new_layer()
    shade(light, rng, [(-10, -10), (330, -10), (330, 154), (-10, 154)], 60, 0, softness=1)  # dawn's cool wash: only the sun is warm
    pool(light, 150, 108, 80, 12, 70)  # first sun across the yard and the cold hearth
    shade(light, rng, [(0, 124), (120, 128), (220, 130), (320, 122), (320, 144), (0, 144)], 195, 40)  # near yard in shade
    shade(light, rng, [(0, 0), (320, 0), (320, 60), (0, 40)], 60, 0, softness=20)  # the sky still cool overhead
    # The sun just above the hills on the left, its rays raking almost flat across the scene.
    light.alpha_composite(sunlight((s(-24), s(72)), [(-6, 4, 60), (0, 3, 70), (6, 4, 60), (12, 3, 45)], s(80), 140))
    save_room(img, rng, "rooms/village.png", sky_mask(open_sky, img), light=light)
    sky_layer("rooms/village_sky.png", 101, horizon=0.58, clouds=10, cloud_bottom=0.42)  # dawn colours from the palette


def path():
    """After Holmberg's Summer Day in Häme: a sandy road winding out of the dark
    spruces toward a sunlit valley and far blue hills."""
    rng = random.Random(2)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(118, 146, 194), horizon=0.6, clouds=6, cloud_bottom=0.5)
    open_sky = img.copy()
    hills(img, rng, s(94), s(18), (100, 100, 152), 0.3, s(150), W)
    treeline(img, rng, s(98), s(14), (70, 88, 88), 1.4, 110, x0=s(150), x1=W)
    meadow(img, rng, s(94), s(122), 0.6)
    mist(img, rng, s(96), s(10), 170, 140, 320)  # dawn mist filling the valley
    # The road: across the foreground, with a branch winding off into the valley.
    road(img, rng, [(0, s(116)), (s(150), s(113)), (s(206), s(108)), (s(226), s(100)), (s(246), s(95)),
                    (s(252), s(95)), (s(240), s(101)), (s(232), s(108)), (s(250), s(113)), (W, s(114)), (W, H), (0, H)])
    road_details(img, rng, s(114), (s(126), s(136)))
    for _ in range(4):
        leafy_tree(img, rng, s(rng.uniform(200, 290)), s(rng.uniform(96, 100)), s(rng.uniform(20, 30)),
                   s(rng.uniform(14, 20)), fade=0.35)
    # Dark woods framing the left and right.
    for _ in range(9):  # dark woods walling the left...
        spruce(img, rng, s(rng.uniform(-10, 140)), s(rng.uniform(106, 112)), s(rng.uniform(90, 130)),
               s(rng.uniform(26, 36)), 0.9, 0.9, 0.9, fade=rng.uniform(0.02, 0.12), shadowed=rng.uniform(0.35, 0.55))
    for _ in range(4):  # ...and the right, so the sunlit valley glows between them
        spruce(img, rng, s(rng.uniform(280, 330)), s(rng.uniform(108, 114)), s(rng.uniform(100, 140)),
               s(rng.uniform(28, 38)), 0.9, 0.9, 0.8, fade=0.05, shadowed=0.55)
    leafy_tree(img, rng, s(112), s(114), s(96), s(40), white_trunk=True, shadowed=0.25)
    leafy_tree(img, rng, s(210), s(110), s(70), s(30), white_trunk=True, fade=0.05)

    for x in (s(30), s(105), s(160), s(214), s(300)):
        shadow(img, [(x - s(3), s(114)), (x + s(3), s(114)), (x + s(40), s(140)), (x + s(24), s(140))], 70, 10)
    # The old spruce the magpie sits in, with a bare branch reaching right.
    spruce(img, rng, s(160), s(114), s(118), s(66), 1.25, 1.1, 0.5, 0.1)
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    d.line([(s(160), s(57)), (s(176), s(53)), (s(192), s(52))], fill=BARK + (255,), width=round(s(1.6)))
    paint(img, lay, 0.4)
    # Anthill: a heap of needles.
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    d.polygon([(s(228), s(122)), (s(240), s(104)), (s(250), s(99)), (s(260), s(104)), (s(272), s(122))], fill=(110, 82, 52, 255))
    for _ in range(900):
        x, y = rng.uniform(s(230), s(270)), rng.uniform(s(100), s(122))
        if abs(x - s(250)) < (y - s(99)) * 1.1:
            col = mix((156, 116, 72), (70, 50, 34), (x - s(230)) / s(40))
            d.line([(x, y), (x + rng.uniform(-3, 3), y + rng.uniform(-2, 2))], fill=vary(col, rng, 16), width=1)
    paint(img, lay, 0.4)
    shadow(img, [(s(262), s(118)), (s(272), s(122)), (s(300), s(126)), (s(286), s(119))], 90, 5)
    rock(img, rng, s(40), s(118), s(64), s(128), 0.8)
    light = new_layer()
    shade(light, rng, [(-10, -10), (330, -10), (330, 154), (-10, 154)], 55, 0, softness=1)  # dawn's cool wash: only the sun is warm
    pool(light, 228, 102, 40, 10, 80)  # the first sun reaching the valley road
    shade(light, rng, [(0, 126), (160, 129), (320, 124), (320, 144), (0, 144)], 190, 30)  # the near road in shade
    shade(light, rng, [(-20, 0), (30, 0), (50, 144), (-20, 144)], 120, 0, softness=16)  # deeper in the woods on the left
    shade(light, rng, [(0, 0), (320, 0), (320, 50), (0, 30)], 60, 0, softness=20)
    # The sun low behind the left-hand woods, rays slanting through the trunks.
    light.alpha_composite(sunlight((s(-20), s(86)), [(-4, 3, 80), (3, 2.5, 75), (9, 3, 70), (15, 2, 50)], s(70), 120))
    save_room(img, rng, "rooms/path.png", sky_mask(open_sky, img), 0.08, light=light)
    sky_layer("rooms/path_sky.png", 102, 0.08, top=(118, 146, 194), horizon=0.6, clouds=12, cloud_bottom=0.5)


def grove():
    """A forest interior: dark spruce walls, a glade of green-gold light, an old birch
    and pine, mossy boulders and ferns."""
    rng = random.Random(3)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(124, 148, 172), haze=(240, 214, 204), horizon=0.6, clouds=2)
    open_sky = img.copy()
    treeline(img, rng, s(104), s(80), (90, 112, 106), 2.4, 140, 90)
    mist(img, rng, s(88), s(28), 150, 0, 320, (222, 226, 238))  # dawn mist between the far trunks
    for _ in range(12):
        spruce(img, rng, rng.uniform(0, W), s(106), s(rng.uniform(80, 110)), s(rng.uniform(20, 30)), 0.7, 0.5, 1.4,
               fade=0.45)
    mist(img, rng, s(100), s(14), 120, 0, 320, (222, 226, 238))
    for _ in range(3):
        leafy_tree(img, rng, s(rng.uniform(60, 180)), s(106), s(rng.uniform(50, 70)), s(rng.uniform(26, 34)), fade=0.35,
                   white_trunk=True)
    meadow(img, rng, s(104), H, 0.6)
    pine_trunk(img, rng, s(252), s(262), -10, s(114))
    for x in (s(18), s(302)):  # the grove's dark walls
        spruce(img, rng, x, s(120), s(140), s(48), 1.1, 0.9, 0.5, shadowed=0.55)
    shadow(img, [(s(194), s(114)), (s(224), s(114)), (s(276), s(144)), (s(236), s(144))], 80, 10)
    shadow(img, [(s(252), s(114)), (s(262), s(114)), (s(300), s(144)), (s(284), s(144))], 70, 8)
    birch(img, rng, s(194), s(224), -10, s(114), crown=False)
    leaves(img, rng, s(170), s(8), s(110), s(30), 900)
    # Offering stone with its worn cup hollow.
    rock(img, rng, s(98), s(98), s(142), s(122), 0.5)
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    d.ellipse([s(113), s(102), s(125), s(107)], fill=(56, 54, 48, 255))
    d.arc([s(113), s(102), s(125), s(107)], 200, 340, fill=(190, 184, 166, 255), width=2)
    paint(img, lay, 0.5)
    for x, w in ((s(26), 18), (s(60), 14), (s(278), 20)):
        rock(img, rng, x, s(116), x + s(w), s(128), 1.2)
    for cx, cy in ((s(80), s(118)), (s(160), s(126)), (s(236), s(122)), (s(40), s(134))):
        ferns(img, rng, cx, cy, s(9), 2)
    # The clearing's edges sink into shade; light falls on the stone and the old birch.
    light = new_layer()
    shade(light, rng, [(-10, -10), (330, -10), (330, 154), (-10, 154)], 45, 0, softness=1)  # dawn's cool wash: only the sun is warm
    shade(light, rng, [(-20, 0), (55, 0), (50, 144), (-20, 144)], 170, 6, softness=14)
    shade(light, rng, [(285, 0), (340, 0), (340, 144), (290, 144)], 170, 6, softness=14)
    shade(light, rng, [(0, 126), (320, 126), (320, 144), (0, 144)], 160, 20)
    pool(light, 120, 112, 34, 12, 80)  # on the offering stone
    pool(light, 210, 90, 16, 40, 60)  # down the birch
    # Low dawn sun from the left, its shafts slanting between the trunks onto the stone.
    light.alpha_composite(sunlight((s(-20), s(50)), [(8, 6, 120), (15, 3, 80), (22, 4, 95), (3, 3, 70)], s(60), 90))
    save_room(img, rng, "rooms/grove.png", sky_mask(open_sky, img), 0.05, light=light)
    sky_layer("rooms/grove_sky.png", 103, 0.05, top=(124, 148, 172), haze=(240, 214, 204), horizon=0.6, clouds=4)


# ---------------------------------------------------------------- intro


INTRO_HEIGHT = 360  # room units: the night scene is 2.5 rooms tall, for the camera to tilt up


def aurora(img, rng, y_base, amplitude, height, alpha=150):
    """Revontulet: curtains of green light with violet upper edges, made of fine vertical rays."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    phase = [rng.uniform(0, 6.28) for _ in range(4)]
    for x in range(0, W, 2):
        u = x / W
        y = y_base + amplitude * (math.sin(u * 4.2 + phase[0]) * 0.6 + math.sin(u * 9.5 + phase[1]) * 0.3)
        strength = 0.35 + 0.65 * max(0.0, math.sin(u * 3.1 + phase[2])) ** 0.7 * (0.7 + 0.3 * math.sin(u * 23 + phase[3]))
        h = height * strength * rng.uniform(0.75, 1.15)
        steps = 24
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            col = mix((120, 255, 170), (170, 90, 220), t0 ** 1.4)
            a = int(alpha * strength * (1 - t0) ** 1.3 * (0.4 if t0 < 0.04 else 1))
            d.line([(x, y - h * t0), (x, y - h * t1)], fill=col + (a,), width=2)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(s(1.4))))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(s(6))))  # the glow around it


def intro_night():
    """The intro backdrop: the village by the lake on a dark autumn night under the
    northern lights. The game shows the bottom first, then tilts up to the sky."""
    global H
    base_h = H
    H = s(INTRO_HEIGHT)
    try:
        rng = random.Random(9)
        img = Image.new("RGBA", (W, H))
        horizon = H - s(52)
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = min(1.0, y / horizon)
            d.line([(0, y), (W, y)], fill=mix(mix((4, 6, 20), (14, 30, 58), t ** 1.6), (40, 72, 88), max(0.0, t - 0.85) * 4) + (255,))
        stars = new_layer()
        sd = ImageDraw.Draw(stars)
        for _ in range(2600):
            x, y = rng.uniform(0, W), rng.uniform(0, horizon) ** 1.08 * horizon ** -0.08
            b = rng.random() ** 3
            r = 0.6 + b * 1.6
            sd.ellipse([x - r, y - r, x + r, y + r], fill=(220, 230, 255, int(80 + 175 * b)))
        for _ in range(4000):  # the Milky Way, a faint diagonal band
            u = rng.random()
            x = u * W + rng.gauss(0, s(18))
            y = (0.15 + 0.5 * u) * horizon + rng.gauss(0, s(10))
            sd.point((x, y), fill=(200, 210, 240, rng.randint(40, 120)))
        aurora(img, rng, s(150), s(26), s(110), 150)
        aurora(img, rng, s(212), s(14), s(70), 110)
        open_sky = img.copy()
        # The lake mirrors the sky, darker and broken into ripples.
        lake_top, lake_bottom = horizon + s(4), H - s(24)
        sky_strip = img.crop((0, lake_top - (lake_bottom - lake_top) * 3, W, lake_top)).transpose(Image.FLIP_TOP_BOTTOM)
        sky_strip = sky_strip.resize((W, lake_bottom - lake_top))
        ripple = Image.new("RGBA", sky_strip.size)
        for y in range(sky_strip.height):
            shift = int(math.sin(y * 0.9) * (1 + y / 8))
            ripple.paste(sky_strip.crop((0, y, W, y + 1)), (shift, y))
        ripple = ImageChops.multiply(ripple, Image.new("RGBA", ripple.size, (150, 170, 190, 255)))
        img.paste(ripple, (0, lake_top))
        hills(img, rng, horizon + s(5), s(12), (14, 22, 38), 0.0)
        treeline(img, rng, horizon + s(6), s(10), (8, 14, 18), 0.8, 0, x0=0, x1=W)
        img.paste(ripple.crop((0, s(6), W, ripple.height)), (0, lake_top + s(6)))  # keep the near water clear
        # The shore and the village in silhouette, roof edges catching the aurora's green.
        lay = new_layer()
        d = ImageDraw.Draw(lay)
        d.rectangle([0, H - s(26), W, H], fill=(10, 14, 12, 255))
        for _ in range(1500):
            x, y = rng.uniform(0, W), rng.uniform(H - s(26), H)
            d.line([(x, y), (x + rng.uniform(-2, 2), y - rng.uniform(4, 12))], fill=vary((18, 26, 22), rng, 6), width=2)
        for (x0, x1, top, peak_h) in ((s(24), s(92), H - s(56), s(16)), (s(196), s(300), H - s(64), s(24))):
            ground_y = H - s(24)
            d.rectangle([x0, top, x1, ground_y], fill=(14, 16, 20, 255))
            for y in range(int(top), int(ground_y), int(s(3.2))):
                d.line([(x0, y), (x1, y)], fill=(22, 26, 30, 255), width=2)
            pk = ((x0 + x1) / 2, top - peak_h)
            d.polygon([(x0 - s(4), top), pk, (x1 + s(4), top)], fill=(12, 14, 18, 255))
            d.line([(x0 - s(4), top), pk], fill=(70, 150, 120, 255), width=round(s(0.5)))  # rim light from the aurora
            d.line([pk, (x1 + s(4), top)], fill=(40, 90, 80, 255), width=round(s(0.4)))
        d.rectangle([s(222), H - s(48), s(234), H - s(40)], fill=(20, 22, 26, 255))  # dark window: the fire is out
        paint(img, lay, 0.6)
        for x in (s(110), s(168), s(316), s(4)):
            spruce(img, rng, x, H - s(22), s(rng.uniform(50, 70)), s(18), 0.9, 0.0, 0.6, fade=0.0)
        lay = new_layer()
        d = ImageDraw.Draw(lay)
        cx, cy = s(INTRO_EMBER[0]), s(INTRO_EMBER[1])
        for a in range(10):  # the hearth's ring of stones, faintly lit
            ang = 2 * math.pi * a / 10
            x, y = cx + math.cos(ang) * s(8), cy + math.sin(ang) * s(2.6)
            d.ellipse([x - s(2), y - s(1.4), x + s(2), y + s(1.4)], fill=(40, 34, 30, 255))
        paint(img, lay, 0.8)
        # Stars go on after the brushwork, which would smear them into streaks, and only
        # where nothing was painted in front of the open sky.
        covered = ImageChops.difference(open_sky.convert("RGB"), img.convert("RGB")).convert("L")
        sky_mask = covered.point(lambda v: 0 if v > 10 else 255).filter(ImageFilter.MinFilter(5))
        img = finish(img, rng, 0.03, (120, 150, 255)).convert("RGBA")
        for layer in (stars.filter(ImageFilter.GaussianBlur(1.2)), stars):
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), sky_mask))
            img.alpha_composite(layer)
    finally:
        H = base_h
    save(img.convert("RGB"), "intro/night.png")


INTRO_EMBER = (160, 342)  # room units within the night scene: where the last ember glows


def ember_glow():
    size = 256
    img = Image.new("RGBA", (size, size))
    for r in range(size // 2, 0, -1):
        t = r / (size / 2)
        a = int(255 * (1 - t) ** 2.2)
        col = mix((255, 236, 170), (220, 70, 20), t)
        ImageDraw.Draw(img).ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], fill=col + (a,))
    save(img, "intro/ember.png")


def title_logo():
    """The title: TIETÄJÄ in burnished gold with a dark outline and an inner glow, and the
    subtitle between two thin gilt rules."""
    from PIL import ImageFont

    def font(name, size):
        for path in (f"/usr/share/fonts/noto/{name}", str(ASSETS / "fonts/NotoSerif-Medium.ttf")):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        raise SystemExit("no font for the title")

    w, h = 1600, 520
    big = font("NotoSerif-Black.ttf", 230)
    small = font("NotoSerif-Bold.ttf", 52)
    title, subtitle = "TIETÄJÄ", "THE ORIGIN OF FIRE"
    spacing = 18

    def spaced(draw, text, fnt, y, fill, spacing, stroke=0, stroke_fill=None):
        widths = [draw.textlength(ch, font=fnt) for ch in text]
        x = (w - sum(widths) - spacing * (len(text) - 1)) / 2
        for ch, cw in zip(text, widths):
            draw.text((x, y), ch, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += cw + spacing
        return (w - sum(widths) - spacing * (len(text) - 1)) / 2, x - spacing

    mask = Image.new("L", (w, h))
    spaced(ImageDraw.Draw(mask), title, big, 40, 255, spacing)
    outline = Image.new("L", (w, h))
    spaced(ImageDraw.Draw(outline), title, big, 40, 255, spacing, stroke=10, stroke_fill=255)

    out = Image.new("RGBA", (w, h))
    glow = Image.new("RGBA", (w, h), (255, 170, 60, 255))
    glow.putalpha(outline.filter(ImageFilter.GaussianBlur(26)).point(lambda v: v * 150 // 255))
    out.alpha_composite(glow)
    edge = Image.new("RGBA", (w, h), (40, 20, 8, 255))
    edge.putalpha(outline)
    out.alpha_composite(edge)
    gold = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(gold)
    top, bottom = 70, 300
    for y in range(h):
        t = min(1.0, max(0.0, (y - top) / (bottom - top)))
        col = mix((255, 244, 196), (226, 170, 72), min(1.0, t * 1.8)) if t < 0.55 else mix((226, 170, 72), (138, 82, 30), (t - 0.55) / 0.45)
        gd.line([(0, y), (w, y)], fill=col + (255,))
    bevel = ImageChops.subtract(mask, shifted(mask, 3, 4)).filter(ImageFilter.GaussianBlur(1.5))
    gold.putalpha(mask)
    out.alpha_composite(gold)
    shine = Image.new("RGBA", (w, h), (255, 255, 236, 255))
    shine.putalpha(ImageChops.multiply(bevel, mask))
    out.alpha_composite(shine)

    d = ImageDraw.Draw(out)
    x0, x1 = spaced(d, subtitle, small, 340, (236, 214, 160, 255), 10, stroke=2, stroke_fill=(40, 24, 10, 255))
    for xa, xb in ((x0 - 260, x0 - 40), (x1 + 40, x1 + 260)):
        d.line([(xa, 372), (xb, 372)], fill=(220, 180, 100, 255), width=3)
        xm = xb if xa < x0 else xa
        d.polygon([(xm - 9, 372), (xm, 363), (xm + 9, 372), (xm, 381)], fill=(240, 206, 130, 255))
    save(out, "intro/title.png")


# ---------------------------------------------------------------- figures and objects


class Painter:
    """Draws opaque marks directly and composites translucent ones right away, so
    they blend with what's underneath instead of cutting see-through holes."""

    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img)

    def __getattr__(self, name):
        method = getattr(self.d, name)

        def call(*args, fill=None, **kwargs):
            if name in ("ellipse", "chord", "arc", "pieslice", "rectangle") and args and len(args[0]) == 2:
                (x0, y0), (x1, y1) = args[0]  # mirrored shapes can arrive with corners swapped
                args = ([(min(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1))],) + args[1:]
            if fill is not None and len(fill) > 3 and fill[3] < 255:
                scratch = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
                getattr(ImageDraw.Draw(scratch), name)(*args, fill=fill[:3] + (255,), **kwargs)
                scratch.putalpha(scratch.getchannel("A").point(lambda v: v * fill[3] // 255))
                self.img.alpha_composite(scratch)
            else:
                method(*args, fill=fill, **kwargs)

        return call


def sprite(w, h):
    img = Image.new("RGBA", (s(w), s(h)), (0, 0, 0, 0))
    return img, Painter(img)


def soften(img, blur=0.8):
    """Painted softness plus a faint dark rim so figures read against busy backgrounds."""
    alpha = img.getchannel("A")
    rim = Image.new("RGBA", img.size, (24, 18, 12, 0))
    rim.putalpha(alpha.filter(ImageFilter.MaxFilter(3)).point(lambda v: v * 70 // 255))
    rim.alpha_composite(img.filter(ImageFilter.GaussianBlur(blur)))
    return rim


SUPERSAMPLE = 2


def oil_paint_sprite(img, rng, scale, passes=((0.9, 0), (0.5, 10), (0.28, 18), (0.14, 30))):
    """The oil-paint pass for a figure on a transparent background. Colours are sampled
    with alpha-weighted blur so edges don't pick up dark fringes, strokes only start
    inside the figure, and the original silhouette is kept."""
    w, h = img.size
    alpha = img.getchannel("A")
    ap = alpha.load()

    def sampled(radius):
        return img.convert("RGBa").filter(ImageFilter.GaussianBlur(radius)).convert("RGBA").convert("RGB")

    gray = img.convert("L").filter(ImageFilter.GaussianBlur(scale * 0.25))
    gx = gray.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], 8, 128)).load()
    gy = gray.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], 8, 128)).load()
    canvas = sampled(passes[0][0] * scale)
    for size, threshold in passes:
        r = size * scale
        ref = sampled(r * 0.5).load()
        cur = canvas.load()
        d = ImageDraw.Draw(canvas, "RGBA")
        step = max(1, int(r))
        cells = [(x + rng.uniform(-r / 2, r / 2), y + rng.uniform(-r / 2, r / 2))
                 for y in range(0, h, step) for x in range(0, w, step)]
        rng.shuffle(cells)
        for x, y in cells:
            xi, yi = min(w - 1, max(0, int(x))), min(h - 1, max(0, int(y)))
            if ap[xi, yi] < 128:
                continue
            c = ref[xi, yi]
            if threshold:
                k = cur[xi, yi]
                if abs(c[0] - k[0]) + abs(c[1] - k[1]) + abs(c[2] - k[2]) < threshold:
                    continue
            dx, dy = gx[xi, yi] - 128, gy[xi, yi] - 128
            angle = math.atan2(dy, dx) + math.pi / 2 if dx * dx + dy * dy > 6 else math.pi / 2 + rng.uniform(-0.3, 0.3)
            col = tuple(clamp(v + rng.uniform(-5, 5)) for v in c) + (235,)
            dab(d, x, y, r * rng.uniform(1.2, 2.0), r * rng.uniform(0.45, 0.7), col, angle, 8)
    out = canvas.convert("RGBA")
    out.putalpha(alpha)
    return out


def painted_sprite(draw, path, seed, blur=0.4):
    """Draw an object at double the output resolution, oil-paint it, then scale it down."""
    global SCALE
    base = SCALE
    SCALE = base * SUPERSAMPLE
    try:
        img = draw()
    finally:
        SCALE = base
    img = oil_paint_sprite(img, random.Random(seed), base * SUPERSAMPLE)
    img = img.resize((img.width // SUPERSAMPLE, img.height // SUPERSAMPLE), Image.LANCZOS)
    save(soften(img, blur), path)

def curve(p0, p1, p2, n=10):
    """Points along a quadratic curve from p0 to p2, bending toward p1 (room units)."""
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def pts(points):
    """Room units to sprite pixels."""
    return [(s(x), s(y)) for x, y in points]


# Figures are painted as Holmberg built them: masses of light and shade, lit from the
# left, in earthy colours with violet-blue shadows, no outlines, and details suggested
# with a stroke or two. Each tone is (shadow, mid, light).
SKIN = ((132, 94, 92), (204, 158, 124), (244, 206, 166))
OLD_SKIN = ((116, 84, 82), (186, 142, 116), (230, 192, 158))
HAIR = ((104, 78, 52), (178, 138, 76), (232, 200, 132))
MADDER = ((70, 30, 44), (146, 52, 40), (204, 106, 66))
SCARF = ((60, 22, 32), (124, 36, 34), (184, 80, 62))
INDIGO = ((26, 28, 44), (58, 60, 80), (110, 108, 112))
DRESS = ((22, 22, 34), (50, 48, 64), (96, 90, 102))
LINEN = ((118, 122, 130), (198, 190, 168), (246, 236, 208))
APRON_BLUE = ((96, 104, 124), (172, 176, 186), (226, 226, 228))
WOOL = ((74, 66, 62), (126, 112, 98), (184, 168, 144))
JUNIPER = ((70, 52, 36), (128, 96, 62), (188, 156, 108))
FELT = ((36, 34, 36), (66, 64, 64), (110, 106, 102))
PLUMAGE = ((8, 8, 14), (26, 26, 34), (74, 80, 100))
WHITE_FEATHER = ((150, 154, 166), (214, 214, 210), (248, 246, 238))


def ramp(size, angle):
    """A 0..255 gradient across `size`, increasing along `angle` (radians)."""
    w, h = size
    big = max(w, h) * 2
    g = Image.linear_gradient("L").resize((big, big)).rotate(math.degrees(angle), resample=Image.BILINEAR)
    left, top = (big - w) // 2, (big - h) // 2
    return g.crop((left, top, left + w, top + h))


def tone(img, outline, palette, kind="cylinder", light=0.0, core=0.62):
    """Fill a shape (room units) with light-to-shade modelling. Cylinders are lit on the
    left with a core shadow past the middle and a little reflected light at the far edge,
    darkening toward the ground; spheres are lit from the upper left; flat shapes take a
    gentle gradient. `light` makes the whole form lighter (+) or darker (-)."""
    p = pts(outline)
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = max(1, int(max(xs)) + 3 - x0), max(1, int(max(ys)) + 3 - y0)
    if kind == "sphere":
        g = Image.new("L", (w, h))
        gd = ImageDraw.Draw(g)
        cx, cy = w * 0.32, h * 0.3
        for r in range(int(max(w, h) * 1.2), 0, -1):
            gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255 - int(255 * min(1.0, r / (max(w, h) * 1.05))))
    elif kind == "cylinder":
        g = ramp((w, h), 0).point(lambda v: int(255 * max(0.0, 1 - (v / 255 / core) ** 2.2)) if v / 255 < core
                                  else int(255 * 0.18 * (v / 255 - core) / (1 - core)))
        g = ImageChops.multiply(g, ramp((w, h), math.pi / 2).point(lambda v: 255 - int(v * 0.35)))
    else:
        g = ramp((w, h), 0).point(lambda v: 255 - int(v * 0.55))
    g = g.point(lambda v: max(0, min(255, int(v + light * 255))))
    shaded = ImageOps.colorize(g, black=palette[0], mid=palette[1], white=palette[2], midpoint=110).convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(p, fill=255)
    layer = Image.new("RGBA", img.size)
    layer.paste(shaded, (x0, y0))
    layer.putalpha(mask)
    img.alpha_composite(layer)


def stroke(d, points, color, width, alpha=255):
    """A brushstroke along points (room units)."""
    d.line(pts(points), fill=color + (alpha,), width=max(1, round(s(width))))


def touch(d, x, y, rx, ry, color, alpha=255, angle=0.0):
    """A single dab of paint (room units)."""
    dab(d, s(x), s(y), s(rx), s(ry), color + (alpha,), angle, 9)


def oval(cx, cy, rx, ry, n=28):
    return [(cx + math.cos(a) * rx, cy + math.sin(a) * ry) for a in (i * 2 * math.pi / n for i in range(n))]


def sleeve(img, d, shoulder, elbow, wrist, width, light, skin, cloth=LINEN):
    """A full sleeve bending at the elbow, ending in a hand."""
    (sx, sy), (ex, ey), (wx, wy) = shoulder, elbow, wrist
    tone(img, [(sx - width, sy), (sx + width, sy), (ex + width * 0.9, ey), (ex - width * 0.9, ey)], cloth, light=light)
    tone(img, [(ex - width * 0.9, ey), (ex + width * 0.9, ey), (wx + width * 0.6, wy), (wx - width * 0.6, wy)], cloth, light=light - 0.05)
    touch(d, ex, ey, width * 0.95, 0.5, cloth[0], 90)  # the crease at the elbow
    tone(img, [(wx - 0.55, wy), (wx + 0.6, wy), (wx + 0.7, wy + 1.2), (wx + 0.25, wy + 1.9), (wx - 0.45, wy + 1.6)],
         skin, "sphere", light=light)


def face_three_quarter(img, d, cx, cy, facing, skin, age=0.0):
    """A face turned a little toward `facing` (+1 right, -1 left), in light and shade. The
    light always comes from the left, whichever way the face turns."""
    f = lambda dx: cx + dx * facing  # noqa: E731
    tone(img, oval(cx + 0.25 * facing, cy + 0.25, 1.85, 2.6), skin, "sphere", light=0.08 - age * 0.05)
    touch(d, f(-1.95), cy + 0.5, 0.42, 0.7, skin[1])  # the near ear
    touch(d, f(-0.2), cy - 0.65, 1.7, 0.45, skin[0], 110 + int(age * 60))  # shade under the brow
    touch(d, f(-0.45), cy - 0.3, 0.38, 0.24 - age * 0.06, (96, 64, 60), 190)  # eyes, deep in that shade
    touch(d, f(1.05), cy - 0.3, 0.3, 0.22 - age * 0.06, (96, 64, 60), 200)
    shade_x, lit_x = (f(0.75), f(0.4)) if facing > 0 else (f(0.4), f(0.75))
    stroke(d, [(shade_x - 0.1, cy - 0.5), (shade_x + 0.1 * facing, cy + 1.05 + age * 0.2)], skin[0], 0.3, 170)  # nose
    stroke(d, [(lit_x - 0.1, cy - 0.4), (lit_x + 0.05 * facing, cy + 0.95 + age * 0.2)], skin[2], 0.22, 200)
    touch(d, f(0.45), cy + 1.75, 0.55, 0.16, (150, 70, 66) if age < 0.5 else (136, 80, 74), 220)  # mouth
    touch(d, f(0.45), cy + 2.05, 0.38, 0.14, skin[2], 160)  # the lip catching light
    touch(d, min(f(-0.9), f(0.9)) + (0.0 if facing > 0 else 1.8), cy + 0.9, 0.62, 0.55, (226, 140, 118), 90)  # sunlit cheek
    touch(d, f(1.7), cy + 0.7, 0.4, 1.4, skin[0], 110)  # the far cheek turning away
    touch(d, f(0.4), cy + 2.75, 0.85, 0.28, skin[0], 120)  # under the chin
    if age:  # smile lines and crow's feet, a few soft strokes
        for side in (-1, 1):
            stroke(d, curve((f(0.45) + side * 0.75, cy + 1.0), (f(0.45) + side * 0.95, cy + 1.6), (f(0.45) + side * 0.7, cy + 2.1), 4),
                   skin[0], 0.14, int(140 * age))
            stroke(d, [(f(side * 1.35), cy - 0.35), (f(side * 1.75), cy - 0.6)], skin[0], 0.12, int(130 * age))


# ---- Vilja


def vilja_head(img, d, cx, cy):
    """Vilja's head in three-quarter view: hair swept over the near ear, a red headband."""
    tone(img, [(cx - 2.5, cy + 0.8), (cx - 2.3, cy - 1.8), (cx - 0.6, cy - 3.3), (cx + 1.5, cy - 3.1), (cx + 2.4, cy - 1.6),
               (cx + 2.2, cy + 0.6)], HAIR, "sphere", light=-0.15)
    face_three_quarter(img, d, cx, cy, 1, SKIN)
    tone(img, [(cx - 2.2, cy + 1.2), (cx - 2.1, cy - 1.4), (cx - 0.9, cy - 2.85), (cx + 0.1, cy - 2.9), (cx - 0.5, cy - 2.0),
               (cx - 1.4, cy - 1.2), (cx - 1.6, cy + 0.2)], HAIR, "sphere", light=0.12)
    tone(img, [(cx + 0.1, cy - 2.9), (cx + 1.5, cy - 2.7), (cx + 2.2, cy - 1.4), (cx + 2.15, cy - 0.2), (cx + 1.5, cy - 1.6),
               (cx + 0.4, cy - 2.2)], HAIR, "sphere", light=-0.05)
    for k in range(4):  # sun along the hair
        stroke(d, curve((cx - 1.9 + k * 0.25, cy - 0.4), (cx - 1.3 + k * 0.3, cy - 2.4), (cx + 0.1 + k * 0.4, cy - 2.85), 6),
               HAIR[2], 0.16, 160)
    stroke(d, curve((cx - 2.3, cy - 1.4), (cx - 0.2, cy - 2.6), (cx + 2.2, cy - 1.6), 8), MADDER[1], 0.38, 235)


def vilja_profile_head(img, d, cx, cy):
    """Vilja's head in profile, facing right."""
    tone(img, oval(cx, cy, 2.1, 2.6), SKIN, "sphere", light=0.05)
    tone(img, [(cx + 1.2, cy - 2.4), (cx + 2.15, cy - 1.0), (cx + 2.3, cy - 0.15), (cx + 2.95, cy + 0.6), (cx + 2.45, cy + 0.85),
               (cx + 2.55, cy + 1.45), (cx + 2.35, cy + 1.75), (cx + 2.5, cy + 2.05), (cx + 2.1, cy + 2.6), (cx + 1.0, cy + 2.85),
               (cx + 0.2, cy + 2.5), (cx + 0.9, cy - 0.5)], SKIN, "flat", light=0.1)
    touch(d, cx + 1.5, cy - 0.35, 0.36, 0.22, (96, 64, 60), 210)  # the eye under its brow
    stroke(d, [(cx + 1.1, cy - 0.75), (cx + 2.0, cy - 0.85)], SKIN[0], 0.2, 140)
    touch(d, cx + 2.35, cy + 1.6, 0.25, 0.1, (150, 70, 66), 220)
    touch(d, cx + 1.1, cy + 0.9, 0.6, 0.55, (226, 140, 118), 90)
    touch(d, cx + 1.4, cy + 2.95, 0.9, 0.25, SKIN[0], 120)
    touch(d, cx - 0.2, cy + 0.4, 0.45, 0.7, SKIN[0], 200)  # ear
    touch(d, cx - 0.15, cy + 0.35, 0.25, 0.45, SKIN[1], 220)
    tone(img, [(cx - 2.2, cy + 1.6), (cx - 2.4, cy - 1.2), (cx - 1.0, cy - 2.8), (cx + 0.8, cy - 3.0), (cx + 2.0, cy - 2.2),
               (cx + 1.1, cy - 1.9), (cx + 0.3, cy - 1.1), (cx - 0.6, cy - 0.1), (cx - 1.0, cy + 1.6)], HAIR, "sphere", light=0.08)
    for k in range(4):
        stroke(d, curve((cx - 1.8 + k * 0.3, cy + 0.6), (cx - 1.2 + k * 0.3, cy - 2.0), (cx + 1.6, cy - 2.4 + k * 0.1), 6),
               HAIR[2], 0.16, 150)
    stroke(d, curve((cx - 2.2, cy - 0.6), (cx - 0.2, cy - 2.7), (cx + 1.9, cy - 2.2), 8), MADDER[1], 0.38, 235)


def braid(d, top, bend, bottom, lit_side):
    """A plait: a dark rope with lit lobes leaning alternately, tied with a red ribbon."""
    line = curve(top, bend, bottom, 14)
    stroke(d, line, HAIR[0], 1.45)
    stroke(d, [(x - 0.28 * lit_side, y) for x, y in line], HAIR[1], 0.9)
    for i in range(1, len(line) - 1):
        x, y = line[i]
        touch(d, x - 0.3 * lit_side, y, 0.48, 0.31, HAIR[2], 190, -0.7 if i % 2 else 0.7)
    touch(d, bottom[0], bottom[1] + 0.6, 0.7, 0.4, MADDER[1])


def vilja_standing():
    """Turned three-quarters to the right, standing in the sun."""
    img, d = sprite(14, 40)
    for x, y in ((5.0, 38.9), (7.8, 39.1)):  # birch-bark shoes, barely there under the hem
        touch(d, x, y, 1.1, 0.55, JUNIPER[1])
    skirt = curve((4.2, 17.4), (2.6, 28), (1.6, 38.6)) + curve((1.6, 38.6), (7.2, 40.0), (12.5, 38.8)) + curve((12.5, 38.8), (11.2, 28), (9.5, 17.4))
    tone(img, skirt, MADDER, core=0.7)
    for x0, x1, lit in ((5.4, 3.8, True), (7.6, 8.8, False), (9.0, 11.4, False)):  # broad folds, not lines
        stroke(d, curve((x0, 18.6), ((x0 + x1) / 2, 28), (x1, 38.2), 6), MADDER[2] if lit else MADDER[0], 0.9, 110)
    apron = curve((5.2, 18.2), (4.7, 27), (5.0, 35.4)) + curve((5.0, 35.4), (7.4, 36.2), (9.4, 35.2)) + curve((9.4, 35.2), (9.4, 27), (8.6, 18.2))
    tone(img, apron, LINEN, light=0.05)
    stroke(d, curve((5.0, 35.4), (7.4, 36.2), (9.4, 35.2), 6), LINEN[2], 0.35, 200)  # the lit hem
    stroke(d, [(5.2, 32.8), (9.2, 32.8)], MADDER[1], 0.3, 160)  # the embroidered band, as one stroke
    sleeve(img, d, (3.6, 11.0), (2.9, 15.8), (3.1, 20.0), 1.05, 0.1, SKIN)
    sleeve(img, d, (10.2, 11.0), (11.0, 15.8), (10.9, 20.0), 0.95, -0.28, SKIN)
    tone(img, [(3.8, 10.6), (5.5, 9.5), (8.5, 9.5), (10.1, 10.6), (9.6, 17.6), (4.3, 17.6)], LINEN, light=0.05)
    tone(img, [(4.5, 11.8), (6.4, 12.6), (7.1, 14.3), (7.7, 12.6), (9.4, 11.8), (9.5, 17.5), (4.4, 17.5)], INDIGO, light=0.08)
    stroke(d, [(4.3, 17.5), (9.6, 17.5)], MADDER[1], 0.7)  # belt
    stroke(d, [(4.5, 17.3), (6.5, 17.3)], MADDER[2], 0.25, 200)
    touch(d, 7.0, 10.2, 0.45, 0.4, (210, 210, 214), 230)  # the silver brooch, one bright touch
    tone(img, [(6.3, 7.8), (7.9, 7.8), (7.8, 9.8), (6.4, 9.8)], SKIN, light=-0.15)
    vilja_head(img, d, 7.1, 5.3)
    braid(d, (8.9, 6.6), (10.6, 13), (10.2, 21.8), 1)
    return img


def vilja_walking(frame):
    """In profile, walking to the right: frame 0-3 of the walk cycle."""
    img, d = sprite(14, 40)
    phase = frame / 4 * 2 * math.pi
    stride, lift = math.sin(phase), math.cos(phase)
    bob = -0.35 * (1 - abs(stride))  # highest as the legs pass

    def Y(y):
        return y + bob
    for side, shade in ((1, JUNIPER[1]), (-1, JUNIPER[0])):  # feet striding under the hem
        x = 7.2 + 3.4 * stride * side
        up = max(0.0, lift * side) * 0.7
        touch(d, x, 39.3 - up, 1.2, 0.5, shade, 255, -0.3 * up)
    spread = abs(stride)
    front_hem, back_hem = 11.6 + 1.0 * spread, 2.4 - 1.0 * spread
    skirt = (curve((5.3, Y(17.4)), (3.2 - spread * 0.4, 28), (back_hem, 38.4)) + curve((back_hem, 38.4), (7.0, 39.8), (front_hem, 38.9))
             + curve((front_hem, 38.9), (10.2 + spread * 0.4, 28), (8.7, Y(17.4))))
    tone(img, skirt, MADDER, core=0.72)
    lead = 1 if stride >= 0 else -1  # which leg presses the cloth forward
    stroke(d, curve((6.4, Y(18.6)), (5.0, 28), (back_hem + 1.0, 38.0), 6), MADDER[2], 0.9, 110)
    stroke(d, curve((8.0, Y(18.6)), (9.4 + spread * 0.3, 28), (front_hem - 1.0, 38.4), 6), MADDER[0], 1.0, 110 + int(40 * spread * lead))
    apron = curve((7.8, Y(18.2)), (9.4 + spread * 0.3, 27), (11.0 + spread * 0.6, 35.6)) + [(11.4 + spread * 0.6, 35.0)] + curve((11.4 + spread * 0.6, 35.0), (10.3, 27), (8.9, Y(18.2)))
    tone(img, apron, LINEN, "flat")
    swing = -stride  # arms swing against the legs
    sleeve(img, d, (6.6, Y(10.9)), (6.0 - 1.4 * swing, Y(15.2)), (5.8 - 2.6 * swing, Y(19.0)), 0.95, -0.3, SKIN)  # far arm
    tone(img, [(5.3, Y(10.4)), (7.2, Y(9.4)), (8.9, Y(10.2)), (9.2, Y(13.4)), (8.8, Y(17.6)), (5.4, Y(17.6)), (5.0, Y(13.0))], LINEN, light=0.05)
    tone(img, [(5.2, Y(12.2)), (8.9, Y(12.0)), (9.1, Y(13.6)), (8.8, Y(17.5)), (5.4, Y(17.5))], INDIGO, light=0.08)
    stroke(d, [(5.3, Y(17.5)), (8.9, Y(17.5))], MADDER[1], 0.7)
    sleeve(img, d, (7.6, Y(10.9)), (7.8 + 1.4 * swing, Y(15.0)), (7.9 + 2.8 * swing, Y(18.8)), 1.0, 0.12, SKIN)  # near arm
    tone(img, [(7.0, Y(7.8)), (8.4, Y(7.6)), (8.5, Y(9.8)), (7.1, Y(9.9))], SKIN, light=-0.15)
    vilja_profile_head(img, d, 7.4, Y(5.2))
    braid(d, (5.6, Y(6.2)), (4.6 - 0.3 * lift, Y(12)), (4.0 - 0.6 * lift, Y(20.6)), -1)
    return img


# ---- Kyllikki


def kyllikki():
    """Old Kyllikki, turned toward the left (toward whoever comes to talk), a little bent:
    red headscarf, wool shawl, dark dress, a striped Häme apron, felt boots and her stick."""
    img, d = sprite(18, 48)
    for x in (7.6, 10.6):
        touch(d, x, 47.2, 1.5, 0.75, FELT[1])
    skirt = curve((6.2, 25), (4.0, 36), (2.6, 46.8)) + curve((2.6, 46.8), (9.4, 48.1), (16.2, 46.8)) + curve((16.2, 46.8), (15.0, 36), (12.6, 25))
    tone(img, skirt, DRESS, core=0.7)
    for x0, x1, lit in ((7.2, 4.6, True), (9.8, 10.6, False), (11.6, 14.2, False)):
        stroke(d, curve((x0, 26.4), ((x0 + x1) / 2, 36), (x1, 46.2), 6), DRESS[2] if lit else DRESS[0], 1.0, 100)
    apron = curve((6.6, 25.5), (5.6, 35), (6.0, 44)) + curve((6.0, 44), (9.0, 45), (12.0, 44)) + curve((12.0, 44), (12.4, 35), (11.2, 25.5))
    tone(img, apron, APRON_BLUE)
    for k in range(6):  # the stripes, as a few soft strokes
        x = 6.7 + k * 0.95
        stroke(d, [(x, 26.0), (x - 0.3 + (x - 9.0) * 0.06, 43.6)], (60, 78, 128), 0.3, 150)
    tone(img, [(4.8, 16.2), (6.8, 14.6), (11.2, 14.4), (13.4, 16.0), (12.8, 25.6), (5.4, 25.6)], DRESS, light=0.05)
    stick = [(2.0, 21.4), (1.8, 30), (1.7, 38), (1.5, 48)]  # juniper stick, in her near hand
    stroke(d, stick, JUNIPER[0], 0.9)
    stroke(d, [(x - 0.2, y) for x, y in stick], JUNIPER[2], 0.3, 210)
    for y in (31.5, 37.2, 42.8):
        touch(d, 1.75, y, 0.5, 0.35, JUNIPER[0])
    sleeve(img, d, (13.0, 16.0), (14.0, 22.0), (13.6, 28.6), 1.0, -0.3, OLD_SKIN, DRESS)  # far arm, hand at the apron
    sleeve(img, d, (5.2, 16.0), (3.6, 19.6), (2.4, 22.2), 1.05, 0.1, OLD_SKIN, DRESS)  # near arm, on the stick
    shawl = [(4.0, 15.6), (6.6, 14.0), (12.0, 14.0), (14.4, 15.6), (13.6, 21.0), (9.0, 26.6), (4.8, 21.0)]
    tone(img, shawl, WOOL, light=0.05)
    for i in range(16):  # the fringe, a row of soft strokes
        f = i / 15
        x, y = (4.8 + (9.0 - 4.8) * f * 2, 21.0 + 5.6 * f * 2) if f < 0.5 else (9.0 + (13.6 - 9.0) * (f - 0.5) * 2, 26.6 - 5.6 * (f - 0.5) * 2)
        stroke(d, [(x, y), (x, y + 0.9)], WOOL[2], 0.15, 170)
    for x in (6.2, 8.4, 10.6):  # red diamonds knitted in, just touches
        touch(d, x, 18.2, 0.42, 0.34, MADDER[1], 210, 0.785)
    # Head bowed a little forward, toward the left.
    cx, cy = 8.7, 10.4
    face_three_quarter(img, d, cx, cy, -1, OLD_SKIN, age=1.0)
    stroke(d, [(cx - 1.4, cy - 1.9), (cx + 0.6, cy - 2.05)], (196, 194, 190), 0.35, 230)  # grey hair at the brow
    scarf = [(cx - 2.6, cy + 1.6), (cx - 2.6, cy - 1.6), (cx - 1.2, cy - 3.6), (cx + 1.0, cy - 3.9), (cx + 2.6, cy - 2.6),
             (cx + 2.9, cy - 0.4), (cx + 2.4, cy + 2.8), (cx + 1.8, cy + 3.4), (cx + 1.9, cy + 0.6), (cx + 1.1, cy - 1.6),
             (cx - 1.0, cy - 2.2), (cx - 1.9, cy - 0.6), (cx - 2.0, cy + 1.8)]
    tone(img, scarf, SCARF, "sphere", light=0.06)
    # The cloth comes down along the near cheek to the knot, framing the face.
    tone(img, [(cx - 2.6, cy + 1.2), (cx - 2.0, cy + 1.4), (cx - 1.5, cy + 2.6), (cx - 0.3, cy + 3.3), (cx + 0.4, cy + 3.6),
               (cx - 0.4, cy + 4.0), (cx - 1.9, cy + 3.4)], SCARF, "flat", light=0.04)
    tone(img, [(cx + 1.9, cy + 0.6), (cx + 2.4, cy + 2.8), (cx + 1.0, cy + 3.7), (cx + 0.4, cy + 3.6), (cx + 1.2, cy + 2.6)],
         SCARF, "flat", light=-0.15)
    for x, y in ((cx - 1.3, cy - 2.5), (cx + 0.4, cy - 3.1), (cx + 1.9, cy - 1.9), (cx + 2.3, cy + 0.6), (cx - 2.2, cy - 0.2)):
        touch(d, x, y, 0.22, 0.2, (234, 214, 168), 200)  # the print, suggested
    touch(d, cx + 0.1, cy + 3.3, 0.55, 0.45, SCARF[0])  # the knot under her chin
    return img


def magpie():
    """The magpie, facing right, the spindle in its beak: tonal blacks with a blue-green gleam."""
    img, d = sprite(16, 12)
    tail = [(0.0, 3.4), (5.2, 5.2), (5.0, 7.4), (0.4, 8.4)]
    tone(img, tail, PLUMAGE, "flat")
    for k, col in enumerate(((60, 120, 112), (70, 90, 160), (110, 70, 150))):  # the tail's sheen
        stroke(d, [(0.5 + k * 0.3, 4.4 + k * 0.9), (5.0, 5.8 + k * 0.4)], col, 0.3, 170)
    tone(img, oval(7.2, 6.3, 4.2, 3.2), PLUMAGE, "sphere")
    tone(img, [(4.8, 4.6), (9.6, 4.2), (10.2, 6.6), (5.8, 8.2)], PLUMAGE, "flat", light=0.06)
    for k in range(4):  # blue-green gleam along the wing
        stroke(d, [(5.4 + k * 1.0, 6.8 - k * 0.3), (4.6 + k * 1.0, 8.0 - k * 0.25)], (70, 130, 150), 0.18, 180)
    tone(img, oval(6.2, 5.3, 1.8, 1.1), WHITE_FEATHER, "sphere")  # shoulder patch
    tone(img, oval(7.9, 7.8, 2.3, 1.6), WHITE_FEATHER, "sphere", light=-0.05)  # belly
    tone(img, oval(11.25, 3.4, 2.45, 2.5), PLUMAGE, "sphere", light=0.05)
    touch(d, 11.7, 2.8, 0.42, 0.42, (28, 22, 20))
    touch(d, 11.55, 2.65, 0.14, 0.14, (240, 240, 236))  # the bright eye
    d.polygon(pts([(13.3, 3.1), (15.5, 3.8), (13.3, 4.5)]), fill=(24, 24, 28, 255))
    stroke(d, [(12.9, 4.9), (16.0, 2.1)], JUNIPER[2], 0.42)  # the spindle
    touch(d, 15.1, 3.0, 0.7, 0.7, LINEN[2])  # wool on the whorl
    for x in (6.6, 8.6):
        stroke(d, [(x, 9.3), (x - 0.2, 11.6)], (44, 44, 48), 0.3)
        stroke(d, [(x - 0.9, 11.8), (x + 0.7, 11.8)], (44, 44, 48), 0.25)
    return img


FIGURE_BRUSHES = ((1.0, 0), (0.6, 8), (0.35, 16), (0.2, 26))


def rim_light(img, sun=(255, 226, 170), strength=150):
    """Sunlight catching the left edges of a figure."""
    alpha = img.getchannel("A")
    shifted = Image.new("L", alpha.size, 0)
    shifted.paste(alpha, (max(1, img.width // 40), max(1, img.width // 60)))
    rim = ImageChops.subtract(alpha, shifted).filter(ImageFilter.GaussianBlur(max(1, img.width // 90)))
    light = Image.new("RGBA", img.size, sun + (255,))
    light.putalpha(rim.point(lambda v: v * strength // 255))
    img.alpha_composite(light)
    img.putalpha(alpha)
    return img


def painted_figure(draw, path, seed, detail=2):
    """Paint a figure at twice the output size with brushwork as coarse as the backgrounds',
    then shrink it. Soft edges, no outline, and the sun's rim on its left side. The game
    tints figures with each room's light."""
    global SCALE
    base = SCALE
    SCALE = base * detail * SUPERSAMPLE
    try:
        img = draw()
    finally:
        SCALE = base
    img = oil_paint_sprite(img, random.Random(seed), base * detail * SUPERSAMPLE, FIGURE_BRUSHES)
    img = img.resize((img.width // SUPERSAMPLE, img.height // SUPERSAMPLE), Image.LANCZOS)
    img.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))  # edges melt a little
    save(rim_light(img), path)


def skull():
    img, d = sprite(14, 12)
    d.line([(s(7), 0), (s(7), s(2))], fill=(90, 70, 50, 255), width=2)
    d.ellipse([s(1), s(1), s(13), s(9.6)], fill=(222, 212, 190, 255))
    d.ellipse([s(8), s(1.4), s(13), s(9.4)], fill=(150, 140, 120, 140))
    d.rectangle([s(3.4), s(7), s(10.6), s(11.4)], fill=(206, 196, 174, 255))
    d.ellipse([s(3), s(3.4), s(5.8), s(6.2)], fill=(36, 30, 26, 255))
    d.ellipse([s(8.2), s(3.4), s(11), s(6.2)], fill=(36, 30, 26, 255))
    for x in (s(4.6), s(6.4), s(8.2)):
        d.line([(x, s(9)), (x, s(11.4))], fill=(60, 50, 40, 255), width=2)
    return img


def bread(w, h):
    img, d = sprite(w, h)
    d.ellipse([s(w * 0.06), s(h * 0.18), s(w * 0.94), s(h * 0.95)], fill=(96, 60, 34, 255))
    d.ellipse([s(w * 0.12), s(h * 0.22), s(w * 0.6), s(h * 0.62)], fill=(150, 104, 62, 200))
    for i in range(3):
        x = s(w * (0.3 + 0.18 * i))
        d.arc([x - s(w * 0.08), s(h * 0.35), x + s(w * 0.08), s(h * 0.6)], 200, 340, fill=(64, 38, 22, 255), width=2)
    return soften(img, 0.6)


def button(w, h):
    img, d = sprite(w, h)
    d.ellipse([s(w * 0.1), s(h * 0.1), s(w * 0.9), s(h * 0.9)], fill=(160, 104, 44, 255))
    d.ellipse([s(w * 0.2), s(h * 0.2), s(w * 0.8), s(h * 0.8)], fill=(214, 160, 80, 255))
    d.ellipse([s(w * 0.26), s(h * 0.24), s(w * 0.5), s(h * 0.44)], fill=(255, 236, 180, 220))
    for x in (0.42, 0.6):
        d.ellipse([s(w * x), s(h * 0.5), s(w * (x + 0.1)), s(h * 0.6)], fill=(90, 56, 24, 255))
    return soften(img, 0.4)


def tinder(w, h):
    img, d = sprite(w, h)
    d.pieslice([s(w * 0.04), s(-h * 0.2), s(w * 0.96), s(h * 1.4)], 0, 180, fill=(124, 104, 82, 255))
    for i, col in enumerate([(160, 140, 112), (102, 86, 68), (140, 120, 96)]):
        f = 0.3 + 0.22 * i
        d.arc([s(w * 0.04 + w * 0.06 * i), s(-h * 0.2 + h * f), s(w * 0.96 - w * 0.06 * i), s(h * 1.4 - h * 0.1 * i)],
              10, 170, fill=col + (255,), width=round(s(0.5)))
    return soften(img, 0.5)


def spindle(w, h):
    img, d = sprite(w, h)
    d.line([(s(w * 0.12), s(h * 0.88)), (s(w * 0.88), s(h * 0.12))], fill=(176, 140, 92, 255), width=round(s(1)))
    d.ellipse([s(w * 0.5), s(h * 0.24), s(w * 0.78), s(h * 0.52)], fill=(120, 82, 52, 255))
    d.ellipse([s(w * 0.2), s(h * 0.4), s(w * 0.56), s(h * 0.76)], fill=(236, 230, 214, 255))
    return soften(img, 0.6)


def fire():
    img, d = sprite(30, 22)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([s(1), s(8), s(29), s(24)], fill=(255, 150, 60, 110))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s(2))))
    rng = random.Random(7)
    for color, scale_ in (((214, 70, 24), 1.0), ((246, 150, 44), 0.75), ((255, 230, 150), 0.45)):
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay, "RGBA")
        for _ in range(9):
            cx = s(15) + rng.gauss(0, s(4) * scale_)
            hgt = s(rng.uniform(10, 20)) * scale_
            wid = s(rng.uniform(2, 4)) * scale_
            ld.polygon([(cx - wid, s(22)), (cx + rng.uniform(-s(1), s(1)), s(22) - hgt), (cx + wid, s(22))], fill=color + (230,))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2)))
    return img


def shadow_sprite():
    """A soft contact shadow the game draws under the player's feet."""
    img = Image.new("L", (s(16), s(4)), 0)
    ImageDraw.Draw(img).ellipse([s(1), s(0.6), s(15), s(3.4)], fill=150)
    img = img.filter(ImageFilter.GaussianBlur(s(0.6)))
    out = Image.new("RGBA", img.size, (24, 18, 10, 255))
    out.putalpha(img)
    save(out, "objects/shadow.png")


def effect_sprites():
    """Small sprites the game animates for the rooms' effects."""
    def soft_dot(size, color, falloff=2.0):
        img = Image.new("RGBA", (size, size))
        for r in range(size // 2, 0, -1):
            a = int(255 * (1 - r / (size / 2)) ** falloff)
            ImageDraw.Draw(img).ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], fill=color + (a,))
        return img
    save(soft_dot(64, (255, 250, 230), 3.0), "effects/sparkle.png")
    save(soft_dot(32, (255, 240, 200), 1.6), "effects/mote.png")
    smoke = soft_dot(128, (118, 112, 108), 1.3).filter(ImageFilter.GaussianBlur(4))  # woodsmoke shows against white cloud
    save(smoke, "effects/smoke.png")
    for frame, lift in ((0, -1.0), (1, 0.6)):  # a distant bird, wings up and down
        img = Image.new("RGBA", (48, 24))
        d = ImageDraw.Draw(img)
        d.line([(2, 12 + 8 * lift), (14, 12 + 3 * lift), (24, 14), (34, 12 + 3 * lift), (46, 12 + 8 * lift)],
               fill=(36, 36, 44, 255), width=4, joint="curve")
        d.ellipse([20, 11, 28, 17], fill=(36, 36, 44, 255))
        save(img, f"effects/bird_{frame}.png")
    img = Image.new("RGBA", (32, 24))  # a yellowing birch leaf
    d = ImageDraw.Draw(img)
    d.polygon([(2, 12), (12, 3), (26, 6), (30, 12), (26, 18), (12, 21)], fill=(196, 188, 70, 255))
    d.line([(2, 12), (28, 12)], fill=(150, 130, 50, 255), width=2)
    save(img.filter(ImageFilter.GaussianBlur(0.5)), "effects/leaf.png")


def items():
    save(bread(16, 16), "items/bread.png")
    save(button(16, 16), "items/button.png")
    save(spindle(16, 16), "items/spindle.png")
    save(tinder(16, 12).crop((0, 0, s(16), s(12))).resize((s(16), s(16))), "items/tinder.png")
    save(bread(14, 8), "objects/bread.png")
    save(button(6, 6), "objects/button.png")
    save(tinder(14, 8), "objects/tinder.png")
    save(fire(), "objects/fire.png")


if __name__ == "__main__":
    village()
    path()
    grove()
    painted_figure(vilja_standing, "chars/vilja_stand.png", 11)
    for frame in range(4):
        painted_figure(lambda: vilja_walking(frame), f"chars/vilja_walk_{frame}.png", 15 + frame)
    painted_figure(kyllikki, "chars/kyllikki.png", 12)
    painted_figure(magpie, "chars/magpie.png", 13)
    effect_sprites()
    painted_sprite(skull, "objects/skull.png", 14, 0.3)
    shadow_sprite()
    items()
    intro_night()
    ember_glow()
    title_logo()
    print("art written to", ASSETS)
