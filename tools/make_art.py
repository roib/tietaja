#!/usr/bin/env python3
"""Draws the placeholder pixel art in assets/. Replace any PNG with real art.

Rooms are 320x144. Hotspot rectangles in assets/story.txt use the same
top-left pixel coordinates, so keep them in sync if you move things.

Usage: python3 tools/make_art.py
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
W, H = 320, 144


def save(img, path):
    out = ASSETS / path
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def sky(d, top, bottom, y0, y1):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        d.line([(0, y), (W, y)], fill=c)


def spruce(d, cx, base, height, width, color):
    # Stacked triangles give the jagged pixel-art spruce look.
    tiers = max(3, height // 10)
    for i in range(tiers):
        t = i / tiers
        top = base - height + int(height * t * 0.9)
        half = int(width / 2 * (0.3 + 0.7 * (i + 1) / tiers))
        d.polygon([(cx, top), (cx - half, top + height // tiers + 6), (cx + half, top + height // tiers + 6)], fill=color)
    d.rectangle([cx - 1, base - 4, cx + 1, base], fill=(40, 28, 20))


def tree_line(d, rng, y, color, count, hmin, hmax):
    for _ in range(count):
        spruce(d, rng.randint(-10, W + 10), y, rng.randint(hmin, hmax), rng.randint(14, 26), color)


def grass_noise(d, rng, y0, y1, colors, n):
    for _ in range(n):
        x, y = rng.randint(0, W), rng.randint(y0, y1)
        d.point((x, y), fill=rng.choice(colors))


def log_building(d, x0, y0, x1, y1, roof_h):
    d.rectangle([x0, y0, x1, y1], fill=(92, 62, 38))
    for y in range(y0 + 3, y1, 5):
        d.line([(x0, y), (x1, y)], fill=(64, 42, 26))
    d.polygon([(x0 - 6, y0), ((x0 + x1) // 2, y0 - roof_h), (x1 + 6, y0)], fill=(58, 48, 40))
    d.line([(x0 - 6, y0), ((x0 + x1) // 2, y0 - roof_h), (x1 + 6, y0)], fill=(80, 70, 60))


def village():
    rng = random.Random(1)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    sky(d, (52, 62, 92), (196, 176, 168), 0, 80)
    tree_line(d, rng, 92, (38, 54, 52), 40, 30, 50)
    tree_line(d, rng, 96, (28, 42, 36), 30, 20, 40)
    d.rectangle([0, 90, W, H], fill=(62, 84, 46))
    grass_noise(d, rng, 90, H, [(74, 98, 54), (52, 72, 40)], 900)
    # Dirt yard where you can walk.
    d.rectangle([0, 112, W, H], fill=(112, 92, 64))
    grass_noise(d, rng, 112, H, [(96, 78, 54), (124, 104, 74)], 500)
    # Sauna on the left, house on the right.
    log_building(d, 18, 54, 88, 100, 14)
    d.rectangle([44, 76, 56, 100], fill=(40, 26, 18))
    d.rectangle([66, 66, 74, 72], fill=(24, 18, 14))
    log_building(d, 184, 50, 300, 104, 20)
    d.rectangle([258, 72, 274, 104], fill=(44, 30, 20))
    d.rectangle([200, 66, 212, 76], fill=(220, 190, 120))
    # Cold hearth: ring of stones, ash, charred logs.
    d.ellipse([130, 100, 174, 120], fill=(96, 94, 92))
    d.ellipse([136, 104, 168, 116], fill=(70, 68, 66))
    for sx in range(132, 172, 7):
        d.ellipse([sx, 99 + (sx % 3), sx + 6, 104 + (sx % 3)], fill=(128, 126, 122))
    d.line([(142, 108), (160, 112)], fill=(30, 26, 24), width=2)
    d.line([(144, 113), (162, 106)], fill=(36, 30, 26), width=2)
    # Stump the bread sits on.
    d.rectangle([46, 104, 70, 120], fill=(96, 70, 44))
    d.ellipse([46, 101, 70, 108], fill=(150, 120, 84))
    save(img, "rooms/village.png")


def path():
    rng = random.Random(2)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    sky(d, (60, 86, 82), (120, 140, 110), 0, 110)
    tree_line(d, rng, 112, (44, 70, 58), 40, 50, 90)
    tree_line(d, rng, 114, (30, 50, 40), 30, 60, 110)
    d.rectangle([0, 104, W, H], fill=(48, 70, 40))
    grass_noise(d, rng, 104, H, [(62, 88, 50), (36, 56, 32), (110, 120, 60)], 1200)
    d.polygon([(0, 116), (W, 112), (W, H), (0, H)], fill=(98, 82, 58))
    grass_noise(d, rng, 116, H, [(84, 70, 50), (114, 96, 70)], 400)
    # The old spruce the magpie sits in.
    spruce(d, 160, 112, 112, 64, (22, 40, 30))
    d.rectangle([156, 70, 164, 112], fill=(56, 40, 30))
    d.line([(164, 56), (190, 52)], fill=(56, 40, 30), width=2)
    # Anthill.
    d.polygon([(230, 122), (250, 100), (270, 122)], fill=(120, 90, 56))
    grass_noise(d, rng, 100, 122, [(90, 66, 40)], 0)
    for _ in range(80):
        x, y = rng.randint(236, 264), rng.randint(104, 121)
        if abs(x - 250) < (y - 100):
            d.point((x, y), fill=(84, 60, 36))
    # Light shafts.
    for x in (60, 90, 220):
        for y in range(0, 110, 2):
            if rng.random() < 0.3:
                d.point((x + y // 4, y), fill=(170, 180, 130))
    save(img, "rooms/path.png")


def grove():
    rng = random.Random(3)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    sky(d, (40, 64, 70), (110, 150, 130), 0, 110)
    tree_line(d, rng, 110, (34, 58, 52), 30, 70, 110)
    d.rectangle([0, 104, W, H], fill=(56, 84, 52))
    grass_noise(d, rng, 104, H, [(80, 120, 70), (44, 70, 44), (140, 160, 90)], 1600)
    # Bear-skull pine on the right.
    d.rectangle([252, 0, 262, 112], fill=(82, 56, 40))
    # The ancient birch, white with dark marks.
    d.rectangle([194, 0, 224, 114], fill=(214, 210, 196))
    for _ in range(60):
        x, y = rng.randint(194, 222), rng.randint(0, 112)
        d.rectangle([x, y, x + rng.randint(2, 5), y + 1], fill=(40, 38, 36))
    d.polygon([(186, 114), (194, 100), (194, 114)], fill=(190, 186, 170))
    d.polygon([(224, 100), (232, 114), (224, 114)], fill=(190, 186, 170))
    # Offering stone with its cup hollow.
    d.ellipse([98, 98, 142, 122], fill=(118, 120, 116))
    d.ellipse([104, 100, 136, 112], fill=(140, 142, 136))
    d.ellipse([114, 103, 124, 108], fill=(76, 78, 74))
    # Mossy rocks and a glowing haze.
    for x in (30, 60, 280):
        d.ellipse([x, 116, x + 18, 128], fill=(92, 110, 80))
    for _ in range(40):
        x, y = rng.randint(0, W), rng.randint(20, 100)
        d.point((x, y), fill=(200, 230, 170))
    save(img, "rooms/grove.png")


def figure(w, h, parts):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for shape, box, color in parts:
        getattr(d, shape)(box, fill=color)
    return img


def characters():
    skin = (232, 196, 160)
    save(figure(14, 40, [
        ("rectangle", [3, 14, 10, 34], (150, 50, 40)),          # dress
        ("rectangle", [4, 15, 9, 30], (196, 186, 160)),          # apron
        ("rectangle", [4, 34, 5, 39], (70, 50, 36)),             # legs
        ("rectangle", [8, 34, 9, 39], (70, 50, 36)),
        ("rectangle", [1, 15, 2, 26], skin),                     # arms
        ("rectangle", [11, 15, 12, 26], skin),
        ("ellipse", [3, 3, 10, 13], skin),                       # head
        ("rectangle", [3, 2, 10, 5], (230, 200, 110)),           # hair
        ("rectangle", [10, 4, 11, 22], (230, 200, 110)),         # braid
        ("point", [5, 8], (40, 40, 60)),
        ("point", [8, 8], (40, 40, 60)),
    ]), "chars/vilja.png")
    save(figure(18, 48, [
        ("polygon", [(4, 18), (14, 18), (17, 46), (1, 46)], (60, 50, 70)),   # long dress
        ("rectangle", [6, 20, 12, 42], (170, 160, 140)),                    # apron
        ("rectangle", [2, 19, 4, 32], (60, 50, 70)),
        ("rectangle", [14, 19, 16, 32], (60, 50, 70)),
        ("rectangle", [2, 32, 4, 34], skin),
        ("ellipse", [5, 6, 13, 17], skin),
        ("polygon", [(3, 10), (9, 2), (15, 10), (14, 13), (4, 13)], (150, 40, 40)),  # kerchief
        ("point", [7, 12], (40, 40, 40)),
        ("point", [11, 12], (40, 40, 40)),
        ("rectangle", [7, 15, 11, 15], (170, 110, 100)),
        ("rectangle", [0, 30, 1, 47], (110, 80, 50)),                       # walking stick
    ]), "chars/kyllikki.png")
    save(figure(16, 12, [
        ("ellipse", [3, 3, 11, 9], (20, 20, 24)),
        ("rectangle", [5, 6, 9, 8], (236, 236, 236)),            # white belly
        ("ellipse", [9, 1, 14, 6], (20, 20, 24)),                # head
        ("point", [12, 3], (240, 240, 240)),
        ("polygon", [(0, 4), (4, 5), (4, 7), (0, 8)], (30, 40, 70)),   # tail
        ("rectangle", [13, 4, 15, 5], (190, 160, 110)),          # spindle in beak
        ("rectangle", [6, 9, 6, 11], (60, 60, 60)),
        ("rectangle", [9, 9, 9, 11], (60, 60, 60)),
    ]), "chars/magpie.png")
    save(figure(14, 12, [
        ("ellipse", [1, 0, 12, 9], (222, 214, 196)),
        ("rectangle", [3, 8, 10, 11], (208, 200, 182)),
        ("ellipse", [3, 3, 5, 5], (30, 26, 24)),
        ("ellipse", [8, 3, 10, 5], (30, 26, 24)),
        ("rectangle", [4, 9, 4, 11], (30, 26, 24)),
        ("rectangle", [7, 9, 7, 11], (30, 26, 24)),
    ]), "objects/skull.png")


def items():
    bread = [("ellipse", [1, 4, 14, 12], (110, 70, 40)), ("ellipse", [3, 5, 12, 9], (140, 96, 58)),
             ("line", [4, 7, 6, 6], (90, 56, 30)), ("line", [8, 7, 10, 6], (90, 56, 30))]
    button = [("ellipse", [3, 3, 12, 12], (190, 130, 60)), ("ellipse", [5, 5, 10, 10], (226, 176, 96)),
              ("point", [6, 7], (90, 60, 30)), ("point", [9, 7], (90, 60, 30))]
    spindle = [("line", [2, 13, 13, 2], (180, 150, 100)), ("ellipse", [8, 4, 12, 8], (130, 90, 60)),
               ("line", [4, 9, 9, 4], (230, 225, 210))]
    tinder = [("polygon", [(1, 8), (8, 3), (15, 8), (14, 11), (2, 11)], (124, 100, 76)),
              ("line", [2, 9, 14, 9], (90, 72, 54)), ("line", [3, 11, 13, 11], (70, 56, 44))]
    for name, parts in [("bread", bread), ("button", button), ("spindle", spindle), ("tinder", tinder)]:
        save(figure(16, 16, parts), f"items/{name}.png")
    # Smaller versions drawn inside rooms.
    save(figure(16, 16, bread).crop((0, 3, 16, 13)).resize((14, 8)), "objects/bread.png")
    save(figure(16, 16, button).crop((2, 2, 14, 14)).resize((6, 6)), "objects/button.png")
    save(figure(16, 16, tinder).crop((0, 2, 16, 12)).resize((14, 8)), "objects/tinder.png")
    save(figure(30, 22, [
        ("polygon", [(2, 21), (6, 8), (10, 14), (15, 0), (20, 13), (24, 6), (28, 21)], (220, 90, 30)),
        ("polygon", [(7, 21), (11, 12), (15, 5), (19, 12), (23, 21)], (250, 170, 50)),
        ("polygon", [(11, 21), (15, 11), (19, 21)], (255, 236, 150)),
    ]), "objects/fire.png")


if __name__ == "__main__":
    village()
    path()
    grove()
    characters()
    items()
    print("art written to", ASSETS)
