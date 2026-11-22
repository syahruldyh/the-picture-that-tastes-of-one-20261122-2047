#!/usr/bin/env python3
"""One glossy ripe strawberry, drawn procedurally.

Python 3 standard library only, no network, fully deterministic.
Run:  python3 main.py        -> writes /output/entry.png (900x900)
"""
import math
import os
import struct
import zlib

SIZE = 900
OUT = "/output/entry.png"

CX = 450.0
CY = 460.0
SCALE = 20.0

buf = bytearray(SIZE * SIZE * 3)
mask = bytearray(SIZE * SIZE)


def put(x, y, r, g, b):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        i = (y * SIZE + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    if 0 <= x < SIZE and 0 <= y < SIZE and a > 0.0:
        i = (y * SIZE + x) * 3
        if a >= 1.0:
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
        else:
            buf[i] = int(buf[i] + (r - buf[i]) * a + 0.5)
            buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a + 0.5)
            buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a + 0.5)


def clamp255(v):
    if v < 0:
        return 0
    if v > 255:
        return 255
    return int(v)


# ---------------------------------------------------------------- background
def paint_background():
    half = SIZE * 0.5
    for y in range(SIZE):
        dy = (y - half) / half
        row = y * SIZE * 3
        for x in range(SIZE):
            dx = (x - half) / half
            t = (dx * dx + dy * dy) * 0.5
            if t > 1.0:
                t = 1.0
            i = row + x * 3
            buf[i] = int(253 - 24 * t)
            buf[i + 1] = int(244 - 32 * t)
            buf[i + 2] = int(227 - 40 * t)


# ---------------------------------------------------------------- soft shadow
def paint_shadow():
    scx, scy, srx, sry = 450.0, 806.0, 270.0, 46.0
    for y in range(int(scy - sry - 8), int(scy + sry + 9)):
        for x in range(int(scx - srx - 8), int(scx + srx + 9)):
            ex = (x - scx) / srx
            ey = (y - scy) / sry
            q = ex * ex + ey * ey
            if q < 1.0:
                a = 0.30 * (1.0 - q) * (1.0 - q)
                blend(x, y, 96, 62, 42, a)


# ---------------------------------------------------------------- polygon fill
def fill_polygon(pts, shade):
    ys = [p[1] for p in pts]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(SIZE - 1, int(math.ceil(max(ys))))
    n = len(pts)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            x1, ya = pts[i]
            x2, yb = pts[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(x1 + (yc - ya) * (x2 - x1) / (yb - ya))
        if len(xs) < 2:
            continue
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = int(math.ceil(xs[k]))
            xb = int(math.floor(xs[k + 1]))
            if xa < 0:
                xa = 0
            if xb > SIZE - 1:
                xb = SIZE - 1
            for x in range(xa, xb + 1):
                shade(x, y)


# ---------------------------------------------------------------- strawberry
def berry_outline():
    pts = []
    n = 720
    for i in range(n):
        t = 2.0 * math.pi * i / n
        hx = 16.0 * math.sin(t) ** 3
        hy = (13.0 * math.cos(t) - 5.0 * math.cos(2.0 * t)
              - 2.0 * math.cos(3.0 * t) - math.cos(4.0 * t))
        # soften the deep heart notch at the top so the calyx can sit in it
        hy += 5.0 * math.exp(-((hx / 8.0) ** 2))
        sx = CX + hx * SCALE
        sy = CY - hy * SCALE
        # fatten the lower half so the fruit reads as a berry, not a drip
        if sy > CY:
            sx = CX + (sx - CX) * (1.0 + 0.35 * (sy - CY) / 340.0)
        # shorten and round the bottom tip
        if sy > CY + 200.0:
            sy = CY + 200.0 + (sy - CY - 200.0) * 0.75
        pts.append((sx, sy))
    return pts


def berry_shade(x, y):
    nx = (x - CX) / 320.0
    ny = (y - CY) / 286.0
    d = -0.55 * nx - 0.83 * ny
    bright = 0.80 + 0.44 * d
    r2 = nx * nx + ny * ny
    if r2 > 1.0:
        r2 = 1.0
    edge = 1.0 - 0.24 * r2 ** 1.5
    # gentle vertical grooves, keyed to x so there is no centre pinwheel
    rib = 1.0 + 0.04 * math.sin(nx * 24.0)
    deep = 1.0 - 0.07 * (ny if ny > 0.0 else 0.0)
    f = bright * edge * rib * deep
    if f > 1.18:
        f = 1.18
    elif f < 0.40:
        f = 0.40
    i = (y * SIZE + x) * 3
    buf[i] = clamp255(218 * f)
    buf[i + 1] = clamp255(44 * f)
    buf[i + 2] = clamp255(54 * f)
    mask[y * SIZE + x] = 1


# ---------------------------------------------------------------- seeds
def draw_seed(sx, sy):
    # soft contact shadow under the seed
    for dy in range(-11, 12):
        for dx in range(-8, 9):
            q = (dx / 6.0) ** 2 + ((dy - 1) / 9.5) ** 2
            if q < 1.0 and mask[(sy + dy) * SIZE + sx + dx]:
                blend(sx + dx, sy + dy, 120, 18, 26, 0.30 * (1.0 - q))
    # pale seed body with a darker rim
    for dy in range(-9, 10):
        for dx in range(-6, 7):
            q = (dx / 5.0) ** 2 + (dy / 8.5) ** 2
            if q < 1.0 and mask[(sy + dy) * SIZE + sx + dx]:
                if q > 0.62:
                    blend(sx + dx, sy + dy, 214, 178, 116, 0.95)
                else:
                    blend(sx + dx, sy + dy, 248, 232, 176, 0.95)
    # tiny bright cap on the seed
    blend(sx - 1, sy - 4, 255, 250, 220, 0.7)
    blend(sx - 2, sy - 3, 255, 250, 220, 0.5)


def paint_seeds():
    for row in range(9):
        sy = 300 + row * 52
        off = 29 if row % 2 else 0
        for col in range(-5, 6):
            sx = 450 + off + col * 58
            if sx < 40 or sx >= SIZE - 40:
                continue
            # thin the grid a little so the seeds stop looking stamped on
            if (row * 7 + col * 3) % 11 == 0:
                continue
            if not (mask[sy * SIZE + sx] and mask[sy * SIZE + sx - 12]
                    and mask[sy * SIZE + sx + 12]):
                continue
            draw_seed(sx, sy)


# ---------------------------------------------------------------- gloss
def paint_highlight(cx0, cy0, rx, ry, angle_deg, amax):
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    x0 = int(cx0 - rx - 4)
    x1 = int(cx0 + rx + 5)
    y0 = int(cy0 - ry - 4)
    y1 = int(cy0 + ry + 5)
    for y in range(max(0, y0), min(SIZE - 1, y1) + 1):
        for x in range(max(0, x0), min(SIZE - 1, x1) + 1):
            if not mask[y * SIZE + x]:
                continue
            dx = x - cx0
            dy = y - cy0
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            q = (u / rx) ** 2 + (v / ry) ** 2
            if q < 1.0:
                a = amax * (1.0 - q) * (1.0 - q)
                blend(x, y, 255, 245, 240, a)


def paint_droplet(dx0, dy0, r):
    for y in range(dy0 - r - 2, dy0 + r + 3):
        for x in range(dx0 - r - 2, dx0 + r + 3):
            if not (0 <= x < SIZE and 0 <= y < SIZE):
                continue
            if not mask[y * SIZE + x]:
                continue
            q = ((x - dx0) / r) ** 2 + ((y - dy0) / r) ** 2
            if q < 1.0:
                blend(x, y, 255, 138, 122, 0.42 * (1.0 - q))
    # sparkle on the droplet
    sx, sy = dx0 - int(r * 0.35), dy0 - int(r * 0.35)
    for y in range(sy - 3, sy + 4):
        for x in range(sx - 3, sx + 4):
            q = ((x - sx) / 3.0) ** 2 + ((y - sy) / 3.0) ** 2
            if q < 1.0:
                blend(x, y, 255, 255, 255, 0.8 * (1.0 - q))


# ---------------------------------------------------------------- calyx
def leaf_polygon(bx, by, angle_deg, length, width):
    ang = math.radians(angle_deg)
    dx, dy = math.sin(ang), -math.cos(ang)  # 0 deg = straight up
    px, py = math.cos(ang), math.sin(ang)   # perpendicular
    left, right = [], []
    steps = 14
    for s_i in range(steps + 1):
        s = s_i / steps
        bend = 10.0 * s * s
        mx = bx + dx * length * s + px * bend
        my = by + dy * length * s + py * bend
        hw = width * 0.5 * math.sin(math.pi * (s ** 0.8)) * (1.0 - 0.22 * s)
        left.append((mx - px * hw, my - py * hw))
        right.append((mx + px * hw, my + py * hw))
    return left + right[::-1]


def paint_leaf(bx, by, angle_deg, length, width):
    ang = math.radians(angle_deg)
    dx, dy = math.sin(ang), -math.cos(ang)
    pts = leaf_polygon(bx, by, angle_deg, length, width)

    def shade(x, y):
        s = ((x - bx) * dx + (y - by) * dy) / length
        if s < 0.0:
            s = 0.0
        elif s > 1.0:
            s = 1.0
        put(x, y, int(58 + 62 * s), int(128 + 58 * s), int(46 + 30 * s))

    fill_polygon(pts, shade)
    # pale centre vein
    for i in range(13):
        s = i / 12.0
        vx = bx + dx * length * s + math.cos(ang) * 10.0 * s * s
        vy = by + dy * length * s + math.sin(ang) * 10.0 * s * s
        for yy in range(int(vy) - 2, int(vy) + 3):
            for xx in range(int(vx) - 2, int(vx) + 3):
                blend(xx, yy, 150, 205, 110, 0.55)


def paint_calyx_cap():
    for y in range(238, 287):
        for x in range(392, 509):
            if not mask[y * SIZE + x]:
                continue
            q = ((x - 450) / 58.0) ** 2 + ((y - 262) / 24.0) ** 2
            if q < 1.0:
                blend(x, y, 64, 132, 52, 0.95)


def paint_stem():
    # gentle curve up and to the right, poking out above the calyx
    for i in range(30):
        s = i / 29.0
        x = 450 + 34 * s * s
        y = 248 - 158 * s
        for yy in range(int(y) - 7, int(y) + 8):
            for xx in range(int(x) - 7, int(x) + 8):
                q = ((xx - x) / 7.0) ** 2 + ((yy - y) / 7.0) ** 2
                if q < 1.0:
                    blend(xx, yy, 94, 118, 58, 0.95)


# ---------------------------------------------------------------- PNG encode
def write_png():
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        raw += buf[y * SIZE * 3:(y + 1) * SIZE * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, payload):
        out = struct.pack(">I", len(payload)) + kind + payload
        out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint_background()
    paint_shadow()
    fill_polygon(berry_outline(), berry_shade)
    paint_seeds()
    paint_highlight(322, 332, 135, 72, -28, 0.46)
    paint_highlight(296, 288, 58, 30, -28, 0.60)
    for dx0, dy0, r in ((560, 420, 13), (380, 520, 11), (520, 620, 9)):
        paint_droplet(dx0, dy0, r)
    paint_calyx_cap()
    for ang, ln, wd in ((-72, 150, 34), (-44, 168, 38), (-16, 158, 36),
                        (12, 162, 36), (40, 170, 38), (68, 148, 34)):
        paint_leaf(450, 255, ang, ln, wd)
    paint_stem()
    n = write_png()
    print("wrote %s (%d bytes)" % (OUT, n))


if __name__ == "__main__":
    main()
