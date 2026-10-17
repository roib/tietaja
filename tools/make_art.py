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


def sky(img, rng, top=SKY_TOP, haze=SKY_HAZE, horizon=0.75, clouds=6):
    d = ImageDraw.Draw(img)
    hz = int(H * horizon)
    for y in range(H):
        t = min(1.0, y / hz) ** 1.4
        d.line([(0, y), (W, y)], fill=mix(top, haze, t) + (255,))
    # Soft cumulus: bright tops, lavender-grey undersides.
    for _ in range(clouds):
        cx, cy = rng.uniform(0, W), rng.uniform(H * 0.05, H * 0.35)
        size = rng.uniform(40, 110)
        lay = new_layer()
        ld = ImageDraw.Draw(lay, "RGBA")
        for _ in range(26):
            x = cx + rng.gauss(0, size)
            y = cy + rng.gauss(0, size * 0.25)
            r = rng.uniform(size * 0.25, size * 0.55)
            ld.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(252, 246, 232, 90))
        for _ in range(12):
            x = cx + rng.gauss(0, size)
            y = cy + size * 0.3 + rng.gauss(0, size * 0.08)
            r = rng.uniform(size * 0.2, size * 0.4)
            ld.ellipse([x - r, y - r * 0.4, x + r, y + r * 0.4], fill=(176, 170, 182, 50))
        paint(img, lay, 8)


def treeline(img, rng, base_y, height, color, blur, fade, count=60):
    """Distant forest edge: a wall of small spruces, paler and bluer with distance."""
    lay = new_layer()
    ImageDraw.Draw(lay).rectangle([0, base_y - height * 0.15, W, H], fill=mix(color, SKY_HAZE, fade / 255) + (255,))
    paint(img, lay, blur)
    x = -s(4)
    while x < W + s(4):
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


def log_building(img, rng, x0, y0, x1, y1, roof_h, door=None, window=None):
    """Weathered log house, lit from the left, with a grey board roof."""
    lay = new_layer()
    d = Canvas(lay)
    log_h = s(2.6)
    y = y0
    while y < y1:
        for i in range(int(x1 - x0)):
            f = i / (x1 - x0)
            c = mix(mix(LOG, (176, 146, 104), 0.35), mix(LOG, (40, 30, 22), 0.4), f)
            d.line([(x0 + i, y), (x0 + i, y + log_h)], fill=vary(c, rng, 3))
        d.line([(x0, y + log_h - 1), (x1, y + log_h - 1)], fill=(40, 30, 22, 255), width=2)
        d.soft("line", [(x0, y + 2), (x1, y + 2)], fill=(196, 166, 120, 90), width=1)
        for cx in (x0 - 3, x1 + 3):  # log ends at the corners
            d.ellipse([cx - log_h * 0.55, y, cx + log_h * 0.55, y + log_h], fill=(150, 116, 80, 255))
            d.ellipse([cx - log_h * 0.25, y + log_h * 0.3, cx + log_h * 0.25, y + log_h * 0.7], fill=(120, 88, 58, 255))
        y += log_h
    for _ in range(int((x1 - x0) * (y1 - y0) / 60)):
        dab(d, rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(4, 12), rng.uniform(1, 2),
            vary(mix(LOG, (150, 120, 84), rng.random() * 0.5), rng, 12, 110), rng.uniform(-0.05, 0.05))
    if window:
        wx0, wy0, wx1, wy1 = window
        d.rectangle([wx0 - 3, wy0 - 3, wx1 + 3, wy1 + 3], fill=(150, 120, 80, 255))
        d.rectangle([wx0, wy0, wx1, wy1], fill=(40, 34, 30, 255))
        d.rectangle([wx0 + 2, wy0 + 2, (wx0 + wx1) / 2 - 1, wy1 - 2], fill=(110, 118, 120, 255))
    if door:
        dx0, dy0, dx1, dy1 = door
        d.rectangle([dx0 - 3, dy0 - 3, dx1 + 3, dy1], fill=(130, 100, 70, 255))
        d.rectangle([dx0, dy0, dx1, dy1], fill=(56, 40, 28, 255))
        for i in range(4):
            xx = dx0 + (dx1 - dx0) * (i + 0.5) / 4
            d.line([(xx, dy0), (xx, dy1)], fill=(40, 28, 20, 255), width=1)
    # Board roof: weathered grey planks, lighter on the left slope.
    peak = ((x0 + x1) / 2, y0 - roof_h)
    left, right = (x0 - s(5), y0 + 2), (x1 + s(5), y0 + 2)
    d.polygon([left, peak, right], fill=(98, 92, 82, 255))
    for i in range(160):
        f = rng.random()
        side = rng.random() < 0.5
        a, b = (left, peak) if side else (peak, right)
        x = a[0] + (b[0] - a[0]) * f
        ytop = a[1] + (b[1] - a[1]) * f
        col = (150, 142, 124) if side else (72, 68, 62)
        d.soft("line", [(x, ytop + 2), (x + rng.uniform(-2, 2), y0 + 1)], fill=vary(col, rng, 14, 150), width=2)
    d.line([left, peak, right], fill=(60, 54, 46, 255), width=3)
    d.flush()
    paint(img, lay, 0.6)


def finish(img, rng, warmth=0.06):
    """Unify like a varnished canvas: warm glaze, soft focus, faint texture, vignette."""
    glaze = Image.new("RGBA", (W, H), SUN + (int(255 * warmth),))
    img.alpha_composite(glaze)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    noise = Image.effect_noise((W, H), 18).convert("L")
    texture = Image.merge("RGBA", [noise, noise, noise, Image.new("L", (W, H), 14)])
    img.alpha_composite(texture)
    # Darken the edges and corners a little, like an old canvas.
    small = Image.new("L", (64, 29))
    for y in range(29):
        for x in range(64):
            dx, dy = (x - 31.5) / 32, (y - 14) / 14.5
            small.putpixel((x, y), clamp(80 * max(0.0, dx * dx + dy * dy - 0.35)))
    dark = Image.new("RGBA", (W, H), (24, 16, 8, 255))
    dark.putalpha(small.resize((W, H), Image.BILINEAR))
    img.alpha_composite(dark)
    return img.convert("RGB")


# ---------------------------------------------------------------- rooms


def village():
    rng = random.Random(1)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, horizon=0.62)
    treeline(img, rng, s(84), s(34), DISTANT, 2.2, 90)
    treeline(img, rng, s(92), s(30), (72, 92, 70), 1.2, 40, 80)
    for _ in range(10):  # forest behind the houses, softened by distance
        spruce(img, rng, rng.uniform(0, W), s(92), s(rng.uniform(36, 52)), s(rng.uniform(14, 20)), 0.7, 0.6, 1.4, fade=0.45)
    for x in (s(110), s(128), s(150), s(170)):
        spruce(img, rng, x + rng.uniform(-8, 8), s(96), s(rng.uniform(48, 60)), s(18), 0.8, 0.8, 0.9, fade=0.2)
    ground(img, rng, s(90))
    road(img, rng, [(0, s(110)), (W * 0.4, s(108)), (W, s(111)), (W, H), (0, H)], (190, 158, 108))
    lay = new_layer()
    d = ImageDraw.Draw(lay)
    for y0 in (s(124), s(133)):  # cart ruts
        pts = [(x, y0 + math.sin(x / s(30)) * s(1.2)) for x in range(0, W + 8, 8)]
        d.line(pts, fill=(150, 120, 80, 150), width=round(s(1)))
        d.line([(x, y + s(0.8)) for x, y in pts], fill=(218, 190, 140, 120), width=round(s(0.5)))
    for _ in range(700):  # grass creeping in from the edges
        x = rng.uniform(0, W)
        y = s(110) + abs(rng.gauss(0, s(2.5))) if rng.random() < 0.97 else rng.uniform(s(112), H)
        d.line([(x, y), (x + rng.uniform(-2, 2), y - rng.uniform(s(1), s(2.5)))], fill=vary(rng.choice(GRASS), rng, 10), width=2)
    paint(img, lay, 0.6)
    shadow(img, [(s(88), s(100)), (s(88), s(104)), (s(120), s(112)), (s(96), s(101))], 70)
    shadow(img, [(s(300), s(104)), (s(300), s(106)), (s(320), s(112)), (s(320), s(105))], 70)
    log_building(img, rng, s(18), s(54), s(88), s(100), s(14), door=(s(44), s(74), s(56), s(100)),
                 window=(s(66), s(64), s(76), s(71)))
    log_building(img, rng, s(184), s(50), s(300), s(104), s(22), door=(s(258), s(72), s(274), s(104)),
                 window=(s(198), s(64), s(214), s(76)))
    # Cold hearth: a ring of stones round grey ash and charred logs.
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    d.ellipse([s(132), s(103), s(172), s(119)], fill=(84, 80, 76, 255))
    for _ in range(80):
        dab(d, rng.uniform(s(138), s(166)), rng.uniform(s(106), s(116)), rng.uniform(3, 8), rng.uniform(2, 4),
            vary((138, 134, 128), rng, 20, 160), rng.uniform(0, 3))
    d.line([(s(142), s(109)), (s(161), s(113))], fill=(30, 24, 20, 255), width=round(s(2)))
    d.line([(s(144), s(114)), (s(162), s(107))], fill=(40, 30, 24, 255), width=round(s(2)))
    paint(img, lay, 0.6)
    for a in range(12):
        ang = 2 * math.pi * a / 12
        x = s(152) + math.cos(ang) * s(21)
        y = s(111) + math.sin(ang) * s(8)
        rock(img, rng, x - s(4), y - s(3), x + s(4), y + s(3), 0.1)
    # Stump for the bread.
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    for i in range(s(24)):
        f = i / s(24)
        d.line([(s(46) + i, s(104)), (s(46) + i, s(120))], fill=mix((140, 104, 70), (52, 38, 26), f) + (255,))
    for _ in range(40):
        x = rng.uniform(s(46), s(70))
        d.line([(x, s(105)), (x + rng.uniform(-2, 2), s(120))], fill=(44, 32, 22, 150), width=2)
    d.ellipse([s(46), s(101), s(70), s(108)], fill=(196, 160, 112, 255))
    for r in range(1, 6):
        d.ellipse([s(58) - r * s(2), s(104.5) - r * s(0.6), s(58) + r * s(2), s(104.5) + r * s(0.6)], outline=(150, 116, 78, 200))
    paint(img, lay, 0.6)
    shadow(img, [(s(66), s(117)), (s(70), s(120)), (s(86), s(121)), (s(82), s(117))], 80, 4)
    for x in (s(30), s(110), s(290)):
        rock(img, rng, x, s(122), x + s(rng.uniform(10, 16)), s(130), 0.6)
    light_shafts(img, rng, [(s(30), s(14)), (s(120), s(8))], 26)
    dapple(img, rng, s(112), 30, 40)
    save(finish(img, rng), "rooms/village.png")


def path():
    rng = random.Random(2)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(126, 156, 176), horizon=0.5, clouds=4)
    treeline(img, rng, s(100), s(70), DISTANT, 2.5, 110, 90)
    for _ in range(14):
        spruce(img, rng, rng.uniform(0, W), s(104), s(rng.uniform(70, 96)), s(rng.uniform(20, 28)), 0.7, 0.6, 1.4, fade=0.4)
    ground(img, rng, s(102))
    # Holmberg's road, winding off into the woods.
    road(img, rng, [(0, s(116)), (s(120), s(113)), (s(200), s(106)), (s(226), s(103)), (s(240), s(104)),
                    (s(222), s(110)), (W, s(114)), (W, H), (0, H)])
    for _ in range(8):
        x = rng.choice([rng.uniform(0, s(110)), rng.uniform(s(200), W)])
        spruce(img, rng, x, s(rng.uniform(112, 118)), s(rng.uniform(80, 120)), s(rng.uniform(26, 36)), 1.0, 1.0, 0.7)
    for x in (s(30), s(105), s(160), s(214), s(300)):
        shadow(img, [(x - s(3), s(114)), (x + s(3), s(114)), (x + s(40), s(140)), (x + s(24), s(140))], 60, 10)
    # The old spruce the magpie sits in, with a bare branch reaching right.
    spruce(img, rng, s(160), s(114), s(118), s(66), 1.25, 1.1, 0.5, 0.1)
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    d.line([(s(160), s(57)), (s(176), s(53)), (s(192), s(52))], fill=BARK + (255,), width=round(s(1.6)))
    paint(img, lay, 0.4)
    # Anthill: a heap of needles.
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    d.polygon([(s(228), s(122)), (s(240), s(104)), (s(250), s(99)), (s(260), s(104)), (s(272), s(122))], fill=(110, 82, 52, 255))
    for _ in range(900):
        x, y = rng.uniform(s(230), s(270)), rng.uniform(s(100), s(122))
        if abs(x - s(250)) < (y - s(99)) * 1.1:
            col = mix((150, 112, 70), (70, 50, 34), (x - s(230)) / s(40))
            d.line([(x, y), (x + rng.uniform(-3, 3), y + rng.uniform(-2, 2))], fill=vary(col, rng, 16, 230), width=1)
    paint(img, lay, 0.4)
    rock(img, rng, s(40), s(118), s(64), s(128), 0.8)
    light_shafts(img, rng, [(s(50), s(10)), (s(95), s(16)), (s(200), s(6))], 30)
    dapple(img, rng, s(110), 50, 55)
    save(finish(img, rng, 0.07), "rooms/path.png")


def grove():
    rng = random.Random(3)
    img = Image.new("RGBA", (W, H))
    sky(img, rng, top=(96, 128, 128), haze=(214, 222, 186), horizon=0.6, clouds=2)
    treeline(img, rng, s(104), s(80), (98, 122, 112), 3.0, 120, 90)
    for _ in range(16):
        spruce(img, rng, rng.uniform(0, W), s(106), s(rng.uniform(80, 110)), s(rng.uniform(20, 30)), 0.7, 0.5, 1.6, fade=0.45)
    ground(img, rng, s(104), [(66, 90, 46), (88, 112, 56), (52, 74, 40), (120, 140, 70)], 11000)
    pine_trunk(img, rng, s(252), s(262), -10, s(114))
    for x in (s(20), s(300)):
        spruce(img, rng, x, s(118), s(130), s(44), 1.1, 0.9, 0.6)
    birch(img, rng, s(194), s(224), -10, s(114), crown=False)
    leaves(img, rng, s(170), s(8), s(110), s(30), 900)
    shadow(img, [(s(194), s(114)), (s(224), s(114)), (s(276), s(144)), (s(236), s(144))], 70, 10)
    shadow(img, [(s(252), s(114)), (s(262), s(114)), (s(300), s(144)), (s(284), s(144))], 60, 8)
    # Offering stone with its worn cup hollow.
    rock(img, rng, s(98), s(98), s(142), s(122), 0.5)
    lay = new_layer()
    d = ImageDraw.Draw(lay, "RGBA")
    d.ellipse([s(113), s(102), s(125), s(107)], fill=(56, 54, 48, 255))
    d.arc([s(113), s(102), s(125), s(107)], 200, 340, fill=(190, 184, 166, 255), width=2)
    paint(img, lay, 0.5)
    for x, w in ((s(26), 18), (s(60), 14), (s(278), 20)):
        rock(img, rng, x, s(116), x + s(w), s(128), 1.2)
    light_shafts(img, rng, [(s(70), s(20)), (s(150), s(10))], 40)
    dapple(img, rng, s(108), 40, 50)
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


def vilja():
    img, d = sprite(14, 40)
    skin, hair = (236, 196, 160), (226, 192, 112)
    d.ellipse([s(3.5), s(38.6), s(6.6), s(40)], fill=(60, 40, 28, 255))  # shoes
    d.ellipse([s(7.6), s(38.6), s(10.7), s(40)], fill=(60, 40, 28, 255))
    shaded_poly(img, [(s(3.6), s(17)), (s(10.4), s(17)), (s(12.6), s(39)), (s(1.4), s(39))], (168, 46, 36))  # skirt
    for i in range(6):
        x = s(3 + i * 1.6)
        d.line([(x, s(20)), (x - s(0.6) + i * s(0.24), s(39))], fill=(120, 30, 26, 120), width=2)
    shaded_poly(img, [(s(4.6), s(18)), (s(9.4), s(18)), (s(10), s(35)), (s(4), s(35))], (222, 212, 186), 0.25, 0.3)  # apron
    shaded_poly(img, [(s(3.6), s(10.5)), (s(10.4), s(10.5)), (s(10.8), s(18.5)), (s(3.2), s(18.5))], (226, 218, 196))  # blouse
    d.polygon([(s(4.6), s(12.5)), (s(9.4), s(12.5)), (s(9.6), s(18.5)), (s(4.4), s(18.5))], fill=(140, 36, 30, 255))  # bodice
    for x0, x1 in ((s(1.6), s(3.6)), (s(10.4), s(12.4))):  # sleeves and hands
        shaded_poly(img, [(x0, s(11)), (x1, s(11)), (x1, s(21)), (x0, s(21))], (226, 218, 196), 0.2, 0.3)
        d.ellipse([x0, s(20.4), x1, s(22.6)], fill=skin + (255,))
    d.rectangle([s(6), s(9), s(8), s(11)], fill=mix(skin, (150, 100, 80), 0.25) + (255,))  # neck
    d.ellipse([s(3.8), s(2.4), s(10.2), s(10.2)], fill=skin + (255,))
    d.ellipse([s(7.4), s(3), s(10.2), s(10)], fill=mix(skin, (150, 100, 80), 0.25) + (120,))
    d.pieslice([s(3.4), s(1.6), s(10.6), s(8.4)], 180, 360, fill=hair + (255,))
    d.ellipse([s(3.4), s(3.4), s(4.8), s(7.2)], fill=hair + (255,))
    for i in range(7):  # braid over the right shoulder
        y = s(7 + i * 2.1)
        d.ellipse([s(9.2), y, s(11.4), y + s(2.4)], fill=mix(hair, (150, 110, 50), 0.15 + 0.1 * (i % 2)) + (255,))
    d.ellipse([s(5.2), s(5.6), s(5.9), s(6.4)], fill=(50, 50, 70, 255))
    d.ellipse([s(8.0), s(5.6), s(8.7), s(6.4)], fill=(50, 50, 70, 255))
    d.ellipse([s(4.6), s(7), s(5.8), s(7.8)], fill=(226, 140, 120, 120))
    d.line([(s(6.4), s(8.3)), (s(7.4), s(8.3))], fill=(170, 90, 80, 255), width=2)
    save(soften(img), "chars/vilja.png")


def kyllikki():
    img, d = sprite(18, 48)
    skin = (222, 182, 150)
    d.line([(s(1.4), s(20)), (s(0.8), s(48))], fill=(110, 78, 46, 255), width=round(s(1)))  # staff
    d.ellipse([s(0.2), s(18.6), s(2.6), s(21)], fill=(130, 94, 56, 255))
    shaded_poly(img, [(s(4.5), s(17)), (s(13.5), s(17)), (s(17), s(47.5)), (s(1.5), s(47.5))], (64, 58, 78))  # dress
    shaded_poly(img, [(s(6.5), s(19)), (s(11.5), s(19)), (s(12.5), s(44)), (s(5.5), s(44))], (168, 160, 140), 0.2, 0.3)
    for x0, x1 in ((s(2.4), s(5)), (s(13), s(15.6))):
        shaded_poly(img, [(x0, s(18)), (x1, s(18)), (x1, s(32)), (x0, s(32))], (64, 58, 78))
        d.ellipse([x0, s(31), x1, s(34)], fill=skin + (255,))
    d.ellipse([s(5.2), s(6), s(12.8), s(16.6)], fill=skin + (255,))
    d.ellipse([s(9.6), s(7), s(12.8), s(16)], fill=mix(skin, (120, 80, 70), 0.3) + (130,))
    for y in (11.2, 12.6):  # wrinkles
        d.arc([s(6), s(y), s(8.4), s(y + 1.2)], 200, 340, fill=(160, 110, 90, 200), width=1)
    scarf = (156, 38, 34)
    d.chord([s(4.2), s(4.4), s(13.8), s(14.4)], 160, 380, fill=scarf + (255,))  # over the crown
    d.polygon([(s(4.4), s(9)), (s(5.6), s(9)), (s(6.6), s(16.4)), (s(5), s(16.6))], fill=scarf + (255,))  # sides
    d.polygon([(s(13.6), s(9)), (s(12.4), s(9)), (s(11.4), s(16.4)), (s(13), s(16.6))], fill=mix(scarf, (20, 10, 10), 0.3) + (255,))
    d.polygon([(s(8.2), s(17)), (s(9), s(16.6)), (s(9.8), s(17)), (s(9.4), s(18.4)), (s(8.6), s(18.4))], fill=mix(scarf, (20, 10, 10), 0.25) + (255,))  # knot at the throat
    d.chord([s(4.6), s(4.8), s(10), s(10)], 180, 300, fill=(204, 84, 64, 150))  # sunlit fold
    for x in (6.2, 8.6, 11):  # a few printed flowers on the cloth
        d.ellipse([s(x), s(6.2), s(x + 0.8), s(7)], fill=(236, 214, 150, 220))
    d.ellipse([s(6.9), s(10.4), s(7.7), s(11.2)], fill=(40, 40, 40, 255))
    d.ellipse([s(10.1), s(10.4), s(10.9), s(11.2)], fill=(40, 40, 40, 255))
    d.arc([s(7.2), s(13.2), s(10.6), s(14.8)], 20, 160, fill=(150, 90, 80, 255), width=2)
    save(soften(img), "chars/kyllikki.png")


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
    save(soften(img, 0.5), "chars/magpie.png")


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
    save(soften(img, 0.5), "objects/skull.png")


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
    vilja()
    kyllikki()
    magpie()
    skull()
    items()
    print("art written to", ASSETS)
