#!/usr/bin/env python3
"""Generate transport_depot.png — 128×160 RGBA isometric building placeholder."""
import struct, zlib

W, H = 128, 160
img = bytearray(W * H * 4)   # RGBA flat array, all transparent

def px(x, y, r, g, b, a=255):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 4
        img[i], img[i+1], img[i+2], img[i+3] = r, g, b, a

def fill_poly(pts, r, g, b, a=255):
    """Scanline fill a convex polygon."""
    if len(pts) < 3:
        return
    miny = max(0, min(p[1] for p in pts))
    maxy = min(H - 1, max(p[1] for p in pts))
    n = len(pts)
    for y in range(miny, maxy + 1):
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                t = (y - ay) / (by - ay)
                xs.append(int(ax + t * (bx - ax)))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(xs[k], xs[k + 1] + 1):
                px(x, y, r, g, b, a)

def rect(x1, y1, x2, y2, r, g, b, a=255):
    for y in range(max(0, y1), min(H, y2 + 1)):
        for x in range(max(0, x1), min(W, x2 + 1)):
            px(x, y, r, g, b, a)

def line(x1, y1, x2, y2, r, g, b, a=255):
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    err = dx - dy
    cx, cy = x1, y1
    while True:
        px(cx, cy, r, g, b, a)
        if cx == x2 and cy == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; cx += sx
        if e2 < dx:
            err += dx; cy += sy

# ── Geometry ────────────────────────────────────────────────────────────────
# Isometric 2×2 building viewed from the south-east.
# Roof diamond vertices (top face):
N  = (64, 26)    # back peak
E  = (108, 48)   # right peak
S  = (64, 70)    # front peak  (player-facing corner)
Wv = (20, 48)    # left peak

GROUND = 144     # y-coordinate of ground level

# Ground projections of the three visible base corners:
gS = (S[0],  GROUND)
gE = (E[0],  GROUND)
gW = (Wv[0], GROUND)

# Chimney sits above N, slightly right (visible over roofline)
CHX, CHY_TOP, CHY_BOT = 80, 5, N[1] + 6
CHW = 7   # half-width

# ── Colours ─────────────────────────────────────────────────────────────────
SMOKE_C  = (215, 213, 220)
CHIMNEY_L = (65,  62,  68)   # chimney left face (shadow)
CHIMNEY_R = (88,  85,  92)   # chimney right face (lit)
ROOF_C   = (145, 140, 152)   # main roof
ROOF_DRK = (112, 108, 118)   # roof shadow strip
WALL_L   = (82,  76,  84)    # left  wall (SW face, shadow)
WALL_R   = (118, 110, 118)   # right wall (SE face, lit)
WIN_C    = (155, 205, 232, 210)
WIN_F    = (45,  40,  48)    # window frame
DOOR_C   = (50,  37,  34)
SIGN_C   = (200, 75,  60)    # small sign / marker
OUTLINE  = (30,  26,  36)

# ── Draw ─────────────────────────────────────────────────────────────────────

# 1. Smoke drifting upward from chimney
for yi in range(0, 16):
    alpha = max(0, 130 - yi * 9)
    spread = yi // 3
    for xi in range(CHX - 3 - spread, CHX + 4 + spread):
        px(xi, yi, *SMOKE_C, alpha)

# 2. Chimney body (left face slightly darker)
rect(CHX - CHW, CHY_TOP, CHX,          CHY_BOT, *CHIMNEY_L)
rect(CHX,       CHY_TOP, CHX + CHW - 1, CHY_BOT, *CHIMNEY_R)

# 3. Left wall (SW face): Wv → S → gS → gW
fill_poly([Wv, S, gS, gW], *WALL_L)

# 4. Right wall (SE face): S → E → gE → gS
fill_poly([S, E, gE, gS], *WALL_R)

# 5. Roof diamond (drawn after walls so it sits on top)
fill_poly([N, E, S, Wv], *ROOF_C)

# Darker strip along the N→W edge (shadow under chimney)
for yi in range(N[1], Wv[1] + 1):
    t = (yi - N[1]) / max(1, Wv[1] - N[1])
    xr = int(N[0] + t * (Wv[0] - N[0]))
    xl = xr - 6
    for xi in range(xl, xr + 1):
        px(xi, yi, *ROOF_DRK)

# 6. Windows on left wall — two small panes
for wi in range(2):
    wx = 26 + wi * 22
    wy = 80 + wi * 5       # slight downward slope for iso look
    rect(wx, wy, wx + 11, wy + 16, *WIN_C)
    for dx in range(12):
        px(wx + dx, wy, *WIN_F)
        px(wx + dx, wy + 16, *WIN_F)
    for dy in range(17):
        px(wx, wy + dy, *WIN_F)
        px(wx + 11, wy + dy, *WIN_F)
    px(wx + 5, wy, *WIN_F)           # centre cross
    px(wx + 5, wy + 16, *WIN_F)
    for dy in range(17):
        px(wx + 5, wy + dy, *WIN_F)
    for dx in range(12):
        px(wx + dx, wy + 8, *WIN_F)

# 7. Windows on right wall — two small panes
for wi in range(2):
    wx = 71 + wi * 20
    wy = 86 - wi * 5
    rect(wx, wy, wx + 11, wy + 16, *WIN_C)
    for dx in range(12):
        px(wx + dx, wy, *WIN_F)
        px(wx + dx, wy + 16, *WIN_F)
    for dy in range(17):
        px(wx, wy + dy, *WIN_F)
        px(wx + 11, wy + dy, *WIN_F)
    for dy in range(17):
        px(wx + 5, wy + dy, *WIN_F)
    for dx in range(12):
        px(wx + dx, wy + 8, *WIN_F)

# 8. Loading door on right wall
rect(74, 112, 84, GROUND, *DOOR_C)
rect(75, 113, 83, GROUND - 1, 62, 48, 44)   # door interior

# 9. Small red emergency/service sign on left wall
rect(36, 95, 48, 102, *SIGN_C)
for dx in range(13):
    px(36 + dx, 95,  *OUTLINE)
    px(36 + dx, 102, *OUTLINE)
for dy in range(8):
    px(36, 95 + dy, *OUTLINE)
    px(48, 95 + dy, *OUTLINE)

# 10. Outline all edges
line(*N,  *E,  *OUTLINE)
line(*E,  *S,  *OUTLINE)
line(*S,  *Wv, *OUTLINE)
line(*Wv, *N,  *OUTLINE)
line(*S,  *gS, *OUTLINE)
line(*E,  *gE, *OUTLINE)
line(*Wv, *gW, *OUTLINE)
line(*gW, *gS, *OUTLINE)
line(*gS, *gE, *OUTLINE)

# ── Write PNG ────────────────────────────────────────────────────────────────

def chunk(tag, data):
    c = tag + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

raw = bytearray()
for y in range(H):
    raw += b"\x00"                  # filter = None
    for x in range(W):
        i = (y * W + x) * 4
        raw += img[i: i + 4]

ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)   # 8-bit RGBA

png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", ihdr)
    + chunk(b"IDAT", zlib.compress(bytes(raw)))
    + chunk(b"IEND", b"")
)

import os
out = os.path.join(os.path.dirname(__file__), "transport_depot.png")
with open(out, "wb") as f:
    f.write(png)
print(f"Generated {out}  ({W}x{H} RGBA, {len(png)} bytes)")
