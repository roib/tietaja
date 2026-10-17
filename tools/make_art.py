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

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCALE = 4
W, H = 320 * SCALE, 144 * SCALE

# Holmberg's palette: warm light, deep spruce greens, ochre earth.
SKY_TOP = (110, 146, 182)
SKY_HAZE = (246, 232, 198)
SUN = (255, 228, 160)
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


def new_layer(w=W, h=H):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


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


def sky(img, rng, top=SKY_TOP, haze=SKY_HAZE, horizon=0.75, clouds=6, cloud_top=0.04, cloud_bottom=0.4):
    """Luminous sky: deep blue overhead, warm haze at the horizon, and cumulus with
    sunlit upper-left edges and cool grey-violet undersides."""
    d = ImageDraw.Draw(img)
    hz = int(H * horizon)
    warm = (252, 226, 178)
    for y in range(H):
        t = min(1.0, y / hz)
        col = mix(top, haze, t ** 1.3)
        col = mix(col, warm, max(0.0, t - 0.75) * 1.4)
        d.line([(0, y), (W, y)], fill=col + (255,))
    for _ in range(clouds):
        cx = rng.uniform(-W * 0.05, W * 1.05)
        base = rng.uniform(H * cloud_top + s(14), H * cloud_bottom)
        size = rng.uniform(s(20), s(36))
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
        shade = mix((150, 150, 172), haze, 0.25 + 0.4 * dist)
        lit = mix((255, 250, 236), haze, 0.2 * dist)
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


def lake(img, rng, y0, y1, x0=0, x1=W):
    """Still water mirroring the bright sky, with soft horizontal glints."""
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(x0, y), (x1, y)], fill=mix((214, 222, 222), (128, 150, 160), t) + (255,))
    for _ in range(int((x1 - x0) / 4)):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        dab(d, x, y, rng.uniform(6, 20), rng.uniform(0.6, 1.2), vary((246, 240, 222), rng, 6), 0, 6)
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


def spruce(img, rng, cx, base, height, width, density=1.0, light=1.0, blur=0.6, trunk_h=0.1, fade=0.0):
    """A Finnish spruce: a narrow spire, then drooping branch tiers hung with dark
    branchlets, a few gaps showing the sky, and warm light caught on the left edges."""
    dark = mix(SPRUCE_DARK, SKY_HAZE, fade)
    mid = mix(SPRUCE_MID, SKY_HAZE, fade)
    lit = mix(SPRUCE_LIGHT, SKY_HAZE, fade)
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


def light_shafts(img, rng, shafts, alpha=34):
    """Diagonal sunbeams falling from the upper left."""
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    for x, w in shafts:
        d.polygon([(x, -10), (x + w, -10), (x + w + s(60), H), (x + s(60), H)], fill=SUN + (alpha,))
    paint(img, lay, 24)


def dapple(img, rng, top, count=60, alpha=60):
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    for _ in range(count):
        x, y = rng.uniform(0, W), rng.uniform(top, H)
        r = rng.uniform(6, 22)
        d.ellipse([x - r, y - r * 0.35, x + r, y + r * 0.35], fill=SUN + (alpha,))
    paint(img, lay, 4)


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

def leafy_tree(img, rng, cx, base, height, width, fade=0.0, trunk=(70, 56, 44), white_trunk=False):
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
    shadow_c = mix((34, 52, 30), SKY_HAZE, fade)
    mid_c = mix((78, 100, 44), SKY_HAZE, fade)
    lit_c = mix((176, 176, 84), SKY_HAZE, fade * 0.8)
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


def finish(img, rng, warmth=0.07):
    """Unify like an old varnished canvas: oil brushwork, a warm glaze, the weave of the
    canvas, and darkened corners."""
    img = oil_paint(img, rng)
    img.alpha_composite(Image.new("RGBA", (W, H), (255, 214, 140, int(255 * warmth))))
    weave = Image.new("L", (8, 8))
    for y in range(8):
        for x in range(8):
            weave.putpixel((x, y), 140 if (x % 4 < 2) ^ (y % 4 < 2) else 110)
    weave = weave.resize((16, 16), Image.BILINEAR)
    tile = Image.new("L", (W, H))
    for y in range(0, H, 16):
        for x in range(0, W, 16):
            tile.paste(weave, (x, y))
    texture = Image.merge("RGBA", [tile, tile, tile, Image.new("L", (W, H), 16)])
    img.alpha_composite(texture)
    small = Image.new("L", (64, 29))
    for y in range(29):
        for x in range(64):
            dx, dy = (x - 31.5) / 32, (y - 14) / 14.5
            small.putpixel((x, y), clamp(85 * max(0.0, dx * dx * 0.7 + dy * dy * 0.8 - 0.35)))
    dark = Image.new("RGBA", (W, H), (30, 18, 8, 255))
    dark.putalpha(small.resize((W, H), Image.BILINEAR))
    img.alpha_composite(dark)
    return img.convert("RGB")


# ---------------------------------------------------------------- rooms


def village():
    """A lakeside farmyard on a summer afternoon."""
    rng = random.Random(1)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, horizon=0.58, clouds=5, cloud_bottom=0.42)
    hills(img, rng, s(80), s(16), (110, 128, 150), 0.35)
    lake(img, rng, s(78), s(88))
    treeline(img, rng, s(80), s(12), (76, 96, 92), 1.6, 120, x0=0, x1=s(90))  # far shore
    treeline(img, rng, s(92), s(30), (52, 72, 52), 1.0, 40, x0=-s(4), x1=s(98))
    treeline(img, rng, s(92), s(30), (52, 72, 52), 1.0, 40, x0=s(178), x1=W + s(4))
    leafy_tree(img, rng, s(8), s(100), s(70), s(34), white_trunk=True)
    leafy_tree(img, rng, s(310), s(98), s(56), s(30), fade=0.1)
    meadow(img, rng, s(88), s(118), 0.7)
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
    light_shafts(img, rng, [(s(30), s(14)), (s(120), s(8))], 22)
    save(finish(img, rng), "rooms/village.png")


def path():
    """After Holmberg's Summer Day in Häme: a sandy road winding out of the dark
    spruces toward a sunlit valley and far blue hills."""
    rng = random.Random(2)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(104, 142, 182), horizon=0.6, clouds=6, cloud_bottom=0.5)
    hills(img, rng, s(94), s(18), (104, 124, 150), 0.3, s(150), W)
    treeline(img, rng, s(98), s(14), (70, 92, 84), 1.4, 110, x0=s(150), x1=W)
    meadow(img, rng, s(94), s(122), 0.9)
    # The road: across the foreground, with a branch winding off into the valley.
    road(img, rng, [(0, s(116)), (s(150), s(113)), (s(206), s(108)), (s(226), s(100)), (s(246), s(95)),
                    (s(252), s(95)), (s(240), s(101)), (s(232), s(108)), (s(250), s(113)), (W, s(114)), (W, H), (0, H)])
    road_details(img, rng, s(114), (s(126), s(136)))
    for _ in range(4):
        leafy_tree(img, rng, s(rng.uniform(200, 290)), s(rng.uniform(96, 100)), s(rng.uniform(20, 30)),
                   s(rng.uniform(14, 20)), fade=0.35)
    # Dark woods framing the left and right.
    for _ in range(9):
        spruce(img, rng, s(rng.uniform(-10, 140)), s(rng.uniform(106, 112)), s(rng.uniform(90, 130)),
               s(rng.uniform(26, 36)), 0.9, 0.9, 0.9, fade=rng.uniform(0.05, 0.25))
    for _ in range(4):
        spruce(img, rng, s(rng.uniform(280, 330)), s(rng.uniform(108, 114)), s(rng.uniform(100, 140)),
               s(rng.uniform(28, 38)), 0.9, 0.9, 0.8, fade=0.1)
    leafy_tree(img, rng, s(112), s(114), s(96), s(40), white_trunk=True)
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
    light_shafts(img, rng, [(s(50), s(10)), (s(95), s(16))], 26)
    dapple(img, rng, s(112), 40, 50)
    save(finish(img, rng, 0.08), "rooms/path.png")


def grove():
    """A forest interior: dark spruce walls, a glade of green-gold light, an old birch
    and pine, mossy boulders and ferns."""
    rng = random.Random(3)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(120, 150, 150), haze=(226, 228, 190), horizon=0.6, clouds=2)
    treeline(img, rng, s(104), s(80), (98, 122, 112), 2.4, 140, 90)
    for _ in range(12):
        spruce(img, rng, rng.uniform(0, W), s(106), s(rng.uniform(80, 110)), s(rng.uniform(20, 30)), 0.7, 0.5, 1.4,
               fade=0.45)
    for _ in range(3):
        leafy_tree(img, rng, s(rng.uniform(60, 180)), s(106), s(rng.uniform(50, 70)), s(rng.uniform(26, 34)), fade=0.35,
                   white_trunk=True)
    meadow(img, rng, s(104), H, 0.6)
    pine_trunk(img, rng, s(252), s(262), -10, s(114))
    for x in (s(18), s(302)):
        spruce(img, rng, x, s(120), s(140), s(48), 1.1, 0.9, 0.5)
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
    light_shafts(img, rng, [(s(70), s(20)), (s(150), s(10))], 44)
    dapple(img, rng, s(108), 40, 55)
    save(finish(img, rng, 0.05), "rooms/grove.png")


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


def shaded_poly(img, pts, base, light_amt=0.35, dark_amt=0.4):
    """Fill a shape with a smooth left-to-right gradient: sunlit left, shadowed right."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    xs = [p[0] for p in pts]
    x0, x1 = min(xs), max(xs)
    grad = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(grad)
    for x in range(w):
        f = min(1.0, max(0.0, (x - x0) / max(1.0, x1 - x0)))
        col = mix(base, (255, 236, 196), light_amt * max(0.0, 1 - 2.2 * f))
        col = mix(col, (14, 12, 22), dark_amt * max(0.0, 1.6 * f - 0.6))
        gd.line([(x, 0), (x, h)], fill=col + (255,))
    img.paste(grad, (0, 0), mask)


def soften(img, blur=0.8):
    """Painted softness plus a faint dark rim so figures read against busy backgrounds."""
    alpha = img.getchannel("A")
    rim = Image.new("RGBA", img.size, (24, 18, 12, 0))
    rim.putalpha(alpha.filter(ImageFilter.MaxFilter(3)).point(lambda v: v * 70 // 255))
    rim.alpha_composite(img.filter(ImageFilter.GaussianBlur(blur)))
    return rim


SUPERSAMPLE = 2


def oil_paint_sprite(img, rng, passes=((0.9, 0), (0.5, 10), (0.28, 18), (0.14, 30))):
    """The oil-paint pass for a figure on a transparent background. Colours are sampled
    with alpha-weighted blur so edges don't pick up dark fringes, strokes only start
    inside the figure, and the original silhouette is kept."""
    w, h = img.size
    scale = SCALE * SUPERSAMPLE
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
    """Draw a figure at double resolution, oil-paint it, then scale it down to size."""
    global SCALE
    base = SCALE
    SCALE = base * SUPERSAMPLE
    try:
        img = draw()
    finally:
        SCALE = base
    img = oil_paint_sprite(img, random.Random(seed))
    img = img.resize((img.width // SUPERSAMPLE, img.height // SUPERSAMPLE), Image.LANCZOS)
    save(soften(img, blur), path)


def curve(p0, p1, p2, n=10):
    """Points along a quadratic curve from p0 to p2, bending toward p1 (room units)."""
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def pts(points):
    """Room units to sprite pixels."""
    return [(s(x), s(y)) for x, y in points]


def folds(d, rng, tops, bottoms, y0, y1, base):
    """Cloth folds: a shadowed valley with a sunlit ridge to its left."""
    for xt, xb in zip(tops, bottoms):
        mid = ((xt + xb) / 2 + rng.uniform(-0.3, 0.3), (y0 + y1) / 2)
        line = pts(curve((xt, y0), mid, (xb, y1), 8))
        d.line(line, fill=mix(base, (20, 10, 10), 0.45) + (170,), width=round(s(0.5)))
        d.line([(x - s(0.5), y) for x, y in line], fill=mix(base, (255, 236, 200), 0.3) + (120,), width=round(s(0.35)))


def vilja():
    img, d = sprite(14, 40)
    rng = random.Random(21)
    skin, hair = (238, 200, 168), (222, 184, 102)
    red, linen = (168, 46, 36), (230, 220, 198)
    for x in (4.8, 7.6):  # shoes peeking under the hem
        d.ellipse([s(x), s(38.3), s(x + 2.2), s(40)], fill=(66, 46, 32, 255))
    skirt = (curve((4.4, 17.2), (2.6, 27), (1.4, 38.6)) + curve((1.4, 38.6), (7, 40.2), (12.6, 38.6))
             + curve((12.6, 38.6), (11.4, 27), (9.6, 17.2)))
    shaded_poly(img, pts(skirt), red, 0.32, 0.45)
    folds(d, rng, [5.4, 6.6, 7.8, 8.9], [3.0, 5.6, 8.6, 11.2], 18.5, 38.6, red)
    d.line(pts(curve((1.4, 38.6), (7, 40.2), (12.6, 38.6))), fill=(110, 26, 22, 255), width=round(s(0.6)))  # hem band
    apron = curve((5.3, 18), (4.6, 27), (5.0, 35.6)) + curve((5.0, 35.6), (7.2, 36.6), (9.4, 35.6)) + curve((9.4, 35.6), (9.6, 27), (8.9, 18))
    shaded_poly(img, pts(apron), (220, 210, 186), 0.25, 0.35)
    folds(d, rng, [6.4, 7.8], [5.8, 8.6], 19, 35.4, (220, 210, 186))
    shaded_poly(img, pts([(3.6, 10.4), (5.4, 9.3), (8.6, 9.3), (10.4, 10.4), (9.9, 17.8), (4.1, 17.8)]), linen)  # blouse
    shaded_poly(img, pts([(4.9, 11.4), (9.1, 11.4), (9.5, 17.8), (4.5, 17.8)]), (132, 34, 30), 0.25, 0.4)  # bodice
    d.line(pts([(4.5, 12.6), (9.5, 12.6)]), fill=(196, 160, 90, 255), width=round(s(0.25)))  # lacing
    d.line(pts([(4.2, 17.6), (9.8, 17.6)]), fill=(70, 40, 30, 255), width=round(s(0.6)))  # belt
    for side, (sx, hx) in ((-1, (3.7, 2.5)), (1, (10.3, 11.3))):  # arms in sleeves, hands at the sides
        arm = pts([(sx, 10.4), (sx + side * 0.2 - 1.4 * (side > 0) + 1.4 * (side < 0), 11), (hx + 0.7 * -side, 20.6), (hx - 0.6 * -side, 20.6)])
        shaded_poly(img, [arm[0], arm[1], arm[2], arm[3]], linen, 0.3, 0.4)
        d.ellipse([s(hx - 0.85), s(20.2), s(hx + 0.85), s(22.4)], fill=skin + (255,))
    d.rectangle([s(6.3), s(7.6), s(7.7), s(9.6)], fill=mix(skin, (150, 100, 80), 0.2) + (255,))  # neck
    d.ellipse([s(4.8), s(2.4), s(9.2), s(8.2)], fill=skin + (255,))
    d.chord([s(6.6), s(2.6), s(9.2), s(8.1)], 290, 70, fill=mix(skin, (150, 100, 80), 0.35) + (140,))  # shaded cheek
    d.pieslice([s(4.4), s(1.6), s(9.6), s(6.6)], 180, 360, fill=hair + (255,))
    d.polygon(pts([(4.4, 4.1), (5.2, 4.0), (5.0, 6.4), (4.5, 6.0)]), fill=hair + (255,))
    d.polygon(pts([(9.6, 4.1), (8.8, 4.0), (9.0, 6.4), (9.5, 6.0)]), fill=mix(hair, (120, 90, 40), 0.25) + (255,))
    for x in (5.2, 6.4, 7.6, 8.6):  # strands catching the light
        d.line(pts(curve((x, 2.0), (x - 0.4, 3.2), (x - 0.2, 4.2), 4)), fill=(250, 226, 160, 180), width=1)
    for i in range(8):  # braid over the right shoulder
        y = 6.0 + i * 1.9
        x = 9.4 + 0.35 * i ** 0.6
        w = 1.25 - i * 0.07
        d.ellipse([s(x - w), s(y), s(x + w), s(y + 2.2)], fill=mix(hair, (130, 96, 44), 0.12 + 0.12 * (i % 2)) + (255,))
        d.arc([s(x - w), s(y), s(x + w), s(y + 2.2)], 200, 290, fill=(252, 230, 170, 255), width=1)
    d.ellipse([s(8.9), s(21.2), s(10.4), s(22.4)], fill=(170, 40, 34, 255))  # ribbon
    for x in (5.9, 7.8):
        d.ellipse([s(x), s(4.9), s(x + 0.55), s(5.5)], fill=(54, 60, 80, 255))
        d.line(pts([(x - 0.2, 4.3), (x + 0.75, 4.2)]), fill=(170, 130, 70, 255), width=1)
    d.line(pts([(7.1, 5.6), (7.3, 6.5), (7.0, 6.6)]), fill=(196, 140, 112, 255), width=1)
    d.line(pts([(6.5, 7.15), (7.6, 7.15)]), fill=(178, 92, 80, 255), width=round(s(0.25)))
    d.ellipse([s(5.3), s(6.0), s(6.3), s(6.8)], fill=(232, 150, 128, 110))
    return img


def kyllikki():
    img, d = sprite(18, 48)
    rng = random.Random(22)
    skin, dress, shawl = (224, 184, 152), (62, 56, 76), (102, 96, 90)
    d.line(pts([(2.0, 17.0), (1.2, 48)]), fill=(112, 80, 48, 255), width=round(s(0.9)))  # walking stick
    d.ellipse([s(1.0), s(16.0), s(3.2), s(18.2)], fill=(132, 96, 58, 255))
    for x in (6.6, 9.8):
        d.ellipse([s(x), s(46.4), s(x + 2.6), s(48)], fill=(46, 36, 30, 255))
    skirt = (curve((6.0, 25), (3.8, 36), (2.6, 46.8)) + curve((2.6, 46.8), (9.4, 48.2), (16.2, 46.8))
             + curve((16.2, 46.8), (15.0, 36), (12.6, 25)))
    shaded_poly(img, pts(skirt), dress, 0.28, 0.45)
    folds(d, rng, [7.2, 8.6, 10.0, 11.4], [4.4, 7.6, 11.2, 14.4], 26, 46.8, dress)
    apron = curve((7.0, 25.5), (6.0, 35), (6.4, 44)) + curve((6.4, 44), (9.4, 45), (12.4, 44)) + curve((12.4, 44), (12.8, 35), (11.6, 25.5))
    shaded_poly(img, pts(apron), (166, 158, 140), 0.25, 0.35)
    folds(d, rng, [8.4, 10.2], [7.8, 11.0], 26.5, 43.6, (166, 158, 140))
    shaded_poly(img, pts([(5.0, 16.0), (7.0, 14.4), (11.6, 14.4), (13.6, 16.0), (13.0, 25.6), (5.6, 25.6)]), dress, 0.25, 0.45)
    # Knitted shawl over the shoulders, crossed in front.
    shaded_poly(img, pts([(4.2, 15.6), (6.6, 14.0), (12.0, 14.0), (14.4, 15.6), (13.6, 21.0), (9.3, 26.6), (5.0, 21.0)]),
                shawl, 0.35, 0.45)
    for i in range(7):
        y = 16 + i * 1.4
        d.line(pts([(5.2 + i * 0.45, y), (13.4 - i * 0.45, y)]), fill=mix(shawl, (40, 36, 34), 0.35) + (150,), width=1)
    d.line(pts([(4.6, 21), (9.3, 26.6), (13.8, 21)]), fill=(150, 144, 132, 255), width=round(s(0.4)))  # fringe edge
    for side, (sx, hx) in ((-1, (4.6, 3.2)), (1, (13.8, 15.0))):
        arm = pts([(sx, 15.8), (sx - side * 1.6, 16.6), (hx - side * 0.8, 29.6), (hx + side * 0.6, 29.6)])
        shaded_poly(img, arm, dress, 0.25, 0.45)
        d.ellipse([s(hx - 1.0), s(29.0), s(hx + 1.0), s(31.6)], fill=skin + (255,))
    d.ellipse([s(6.4), s(6.4), s(12.2), s(13.6)], fill=skin + (255,))
    d.chord([s(9.2), s(6.6), s(12.2), s(13.5)], 290, 70, fill=mix(skin, (120, 80, 70), 0.35) + (150,))
    scarf = (156, 38, 34)
    d.chord([s(5.6), s(4.6), s(13.0), s(12.6)], 160, 380, fill=scarf + (255,))
    d.polygon(pts([(5.8, 8.4), (6.9, 8.4), (7.4, 13.6), (6.0, 13.8)]), fill=scarf + (255,))
    d.polygon(pts([(12.8, 8.4), (11.7, 8.4), (11.2, 13.6), (12.6, 13.8)]), fill=mix(scarf, (20, 10, 10), 0.3) + (255,))
    d.polygon(pts([(8.7, 14.0), (9.3, 13.7), (9.9, 14.0), (9.6, 15.2), (9.0, 15.2)]), fill=mix(scarf, (20, 10, 10), 0.25) + (255,))
    d.chord([s(6.0), s(5.0), s(10.0), s(9.4)], 180, 300, fill=(206, 86, 66, 150))
    for x in (7.2, 9.2, 11.2):
        d.ellipse([s(x), s(6.4), s(x + 0.7), s(7.1)], fill=(236, 214, 150, 230))
    for x in (7.6, 10.2):  # eyes, a little hooded
        d.ellipse([s(x), s(9.6), s(x + 0.6), s(10.2)], fill=(40, 36, 36, 255))
        d.arc([s(x - 0.3), s(9.1), s(x + 0.9), s(9.9)], 200, 340, fill=(150, 104, 86, 255), width=1)
    for y in (11.4, 12.2):
        d.arc([s(7.0), s(y), s(8.4), s(y + 0.7)], 200, 340, fill=(160, 112, 92, 200), width=1)
        d.arc([s(10.4), s(y), s(11.8), s(y + 0.7)], 200, 340, fill=(140, 96, 80, 200), width=1)
    d.line(pts([(9.2, 10.4), (9.5, 11.6), (9.1, 11.7)]), fill=(180, 126, 104, 255), width=1)
    d.arc([s(8.2), s(12.0), s(10.4), s(13.0)], 20, 160, fill=(146, 84, 74, 255), width=round(s(0.25)))
    return img


def magpie():
    img, d = sprite(16, 12)
    d.polygon([(s(0), s(3.4)), (s(4.6), s(5.2)), (s(4.6), s(7.6)), (s(0.4), s(9))], fill=(30, 52, 72, 255))  # tail sheen
    d.line([(s(0.6), s(5)), (s(4), s(6.2))], fill=(70, 120, 120, 200), width=2)
    d.ellipse([s(3), s(3), s(11.4), s(9.6)], fill=(22, 22, 28, 255))
    d.ellipse([s(5.4), s(6), s(10), s(9.4)], fill=(236, 234, 226, 255))  # white belly
    d.ellipse([s(4), s(4), s(7.4), s(6.4)], fill=(220, 220, 214, 230))  # shoulder patch
    d.ellipse([s(9), s(1), s(13.6), s(5.8)], fill=(22, 22, 28, 255))
    d.ellipse([s(11.4), s(2.4), s(12.2), s(3.2)], fill=(200, 200, 200, 255))
    d.polygon([(s(13.4), s(3.2)), (s(15.4), s(3.8)), (s(13.4), s(4.4))], fill=(30, 30, 30, 255))
    d.line([(s(13.2), s(4.6)), (s(16), s(2.4))], fill=(196, 160, 104, 255), width=round(s(0.5)))  # spindle
    d.ellipse([s(14.6), s(2.6), s(15.8), s(3.8)], fill=(232, 226, 210, 255))
    for x in (s(6.6), s(8.6)):
        d.line([(x, s(9.4)), (x, s(12))], fill=(40, 40, 40, 255), width=2)
    return img


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
    painted_sprite(vilja, "chars/vilja.png", 11)
    painted_sprite(kyllikki, "chars/kyllikki.png", 12)
    painted_sprite(magpie, "chars/magpie.png", 13, 0.3)
    painted_sprite(skull, "objects/skull.png", 14, 0.3)
    shadow_sprite()
    items()
    print("art written to", ASSETS)
