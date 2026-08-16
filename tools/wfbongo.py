#!/usr/bin/env python3
"""Bongo Cat watchface for the KW80.

    ../.venv/bin/python tools/wfbongo.py bongo.bin

Layout (368x448 portrait, top-to-bottom):
  * Bongo cat GIF — keyed off its white background so the line-art body
    renders WHITE, while the pink paws / dark-red details keep their colour.
    Placed at the top. The source GIF ships 4 frames but only 2 are unique
    (0-2 = paws up, 3 = paws down); the f20 animation alternates them.
  * Time — SF Compact Rounded, weight 800 (heavy), tight digit pitch, with
    a colon. Live hour/minute.
  * Day-of-week (PictureSet type 52, SUN-first) + day-of-month (digits 17).
  * Two lucide icons with live values: paw-print = steps, heart = heart rate.

Cat frames are cf=4 opaque with a baked-in black background — proven for f20
animation on the KW80, and visually identical to transparency on a black face.
Icons are the real lucide SVGs (paw-print, heart) rendered via rsvg-convert.
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
from collections import deque

from PIL import Image, ImageDraw, ImageFont, ImageSequence

sys.path.insert(0, os.path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import (TRAILER, encode_pixels_alpha,  # noqa: E402
                     digit_group, msg, u)

W, H = 368, 448
THUMB = (180, 219)

BIG = (52, 82)            # time digit cells
SMALL = (24, 32)          # steps / temp digits (bigger, heavier)
AMPM_W, AMPM_H = 64, 30   # AM / PM label images (bigger)
WICON = 52                # weather icon display size

# vertical layout constants
CAT_W = 292                # display width of the cat (centred)
CAT_TOP = 38               # cat y — upper-centre

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
ACCENT = (255, 178, 96)   # warm amber — weekday label
PINK = (255, 140, 175)    # paw icon — matches the cat's pink paws

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIF = next((f for f in os.listdir(ROOT)
            if f.lower().endswith(".gif") and "bongo" in f.lower()), None)
FRAME_MS = 160

SF = "/System/Library/Fonts/SFCompactRounded.ttf"

# Real lucide SVG bodies (lucide-icons/lucide, 24x24 viewBox).
PAW_SVG = ('<circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/>'
           '<circle cx="20" cy="16" r="2"/>'
           '<path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045'
           'Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z"/>')
HEART_SVG = ('<path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0'
             'A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313'
             'a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/>')


def font(size, weight=800):
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([weight])      # SF Compact Rounded: 1 axis
    except Exception:
        pass
    return f


# --------------------------------------------------------------------------- #
#  Real lucide icons via rsvg-convert
# --------------------------------------------------------------------------- #

def lucide_icon(svg_body, color, stroke_w, px):
    r, g, b = color
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" '
           f'viewBox="0 0 24 24" fill="none" stroke="rgb({r},{g},{b})" '
           f'stroke-width="{stroke_w}" stroke-linecap="round" '
           f'stroke-linejoin="round">{svg_body}</svg>')
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as sf:
        sf.write(svg.encode()); svg_path = sf.name
    png_path = svg_path.replace(".svg", ".png")
    subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px),
                    svg_path, "-o", png_path], check=True)
    return Image.open(png_path).convert("RGBA")


def paint_icon(canvas, icon, cx, cy, size):
    s = icon.resize((size, size), Image.LANCZOS)
    canvas.alpha_composite(s, (cx - size // 2, cy - size // 2))


# --------------------------------------------------------------------------- #
#  GIF processing — colour-preserving key
# --------------------------------------------------------------------------- #


def load_cat_frames():
    """Return (list[RGB frames], cat_pos, cat_size).

    The source cat is black line-art on white. A naive invert turns the
    enclosed interior black (→ "black cat, white outline"). Instead we
    flood-fill from the frame border to find the enclosed interior, then:

      * outside      -> black (the watchface background)
      * interior     -> white  (a white-filled cat)
      * outline / dark features (eyes, mouth) -> kept dark, visible on white
      * coloured pixels (pink paws, dark-red details) -> kept as-is
    """
    im = Image.open(os.path.join(ROOT, GIF))
    raw = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
    frames = [raw[0]]
    for f in raw[1:]:
        if f.tobytes() != frames[-1].tobytes():
            frames.append(f)

    fw, fh = frames[0].size
    xs, ys = [], []
    for f in frames:
        px = f.load()
        for x in range(fw):
            for y in range(fh):
                r, g, b = px[x, y]
                if not (r > 240 and g > 240 and b > 240):
                    xs.append(x); ys.append(y)
    box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    cw, ch = box[2] - box[0], box[3] - box[1]

    target_h = max(1, round(CAT_W * ch / cw))
    pos_x = (W - CAT_W) // 2

    out = []
    for f in frames:
        c = f.crop(box)
        px = c.load()

        # 1. classify pixels + build a blocker mask (blocks flood-fill)
        blocker = bytearray(cw * ch)      # 1 = line/colour/edge (not bg-white)
        coloured = bytearray(cw * ch)
        lum = bytearray(cw * ch)
        for y in range(ch):
            for x in range(cw):
                r, g, b = px[x, y]
                i = y * cw + x
                sat = max(r, g, b) - min(r, g, b)
                lum[i] = (r + g + b) // 3
                if sat >= 22:
                    coloured[i] = 1
                    blocker[i] = 1
                elif lum[i] <= 238:
                    blocker[i] = 1

        # 2. dilate blockers by 1px to close hairline gaps in the outline
        dil = bytearray(blocker)
        for y in range(ch):
            for x in range(cw):
                i = y * cw + x
                if blocker[i]:
                    continue
                if ((x > 0 and blocker[i - 1]) or
                        (x < cw - 1 and blocker[i + 1]) or
                        (y > 0 and blocker[i - cw]) or
                        (y < ch - 1 and blocker[i + cw])):
                    dil[i] = 1

        # 3. flood-fill from every border pixel -> mark "outside"
        outside = bytearray(cw * ch)
        q = deque()
        for x in range(cw):
            for y in (0, ch - 1):
                j = y * cw + x
                if not dil[j] and not outside[j]:
                    outside[j] = 1; q.append(j)
        for y in range(ch):
            for x in (0, cw - 1):
                j = y * cw + x
                if not dil[j] and not outside[j]:
                    outside[j] = 1; q.append(j)
        while q:
            i = q.popleft()
            x, y = i % cw, i // cw
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < cw and 0 <= ny < ch:
                    j = ny * cw + nx
                    if not dil[j] and not outside[j]:
                        outside[j] = 1; q.append(j)

        # 4. render: outside=black, dark/colour kept, interior+edges=white
        img = Image.new("RGB", (cw, ch), BLACK)
        op = img.load()
        for i in range(cw * ch):
            if outside[i]:
                continue
            x, y = i % cw, i // cw
            if coloured[i] or lum[i] < 80:
                op[x, y] = px[x, y]          # pink paws, dark-red, outline, eyes
            else:
                op[x, y] = WHITE             # white-filled body

        out.append(img.resize((CAT_W, target_h), Image.LANCZOS))
    return out, (pos_x, CAT_TOP), (CAT_W, target_h)


# --------------------------------------------------------------------------- #
#  Rendered artwork
# --------------------------------------------------------------------------- #

SCREEN_R = 55    # KW80 actual corner radius — must match so ticks stay visible


def _border_point(angle, cx, cy):
    """Where a ray from (cx,cy) at `angle` (radians, 0=right, CCW positive)
    crosses the rounded-rectangle screen border.

    Returns (x, y, nx, ny) — border point + inward-pointing unit normal.
    Handles straight edges and the four R-radius corner arcs."""
    R = SCREEN_R
    dx, dy = math.cos(angle), math.sin(angle)

    # parametric exit from the bounding box [0,W] x [0,H]
    if abs(dx) < 1e-12:
        tx = float('inf')
    elif dx > 0:
        tx = (W - cx) / dx
    else:
        tx = -cx / dx
    if abs(dy) < 1e-12:
        ty = float('inf')
    elif dy > 0:
        ty = (H - cy) / dy
    else:
        ty = -cy / dy

    t = min(tx, ty)
    ex, ey = cx + t * dx, cy + t * dy

    # if the box-exit falls in a corner strip, the ray actually left
    # through the quarter-arc — solve |P - corner_centre| = R
    in_cx = ex < R or ex > W - R
    in_cy = ey < R or ey > H - R
    if in_cx and in_cy:
        ccx = R if ex < W / 2 else W - R
        ccy = R if ey < H / 2 else H - R
        u, v = cx - ccx, cy - ccy
        half_b = u * dx + v * dy
        c_val = u * u + v * v - R * R
        disc = half_b * half_b - c_val
        if disc >= 0:
            t_arc = -half_b + math.sqrt(disc)    # outer (exit) root
            ax = cx + t_arc * dx
            ay = cy + t_arc * dy
            return ax, ay, (ccx - ax) / R, (ccy - ay) / R

    # straight edge — normal points inward
    if t == tx:                 # left or right edge
        return ex, ey, (-1 if dx > 0 else 1), 0
    else:                       # top or bottom edge
        return ex, ey, 0, (-1 if dy > 0 else 1)


def draw_clock_ticks(dr):
    """60 tick marks at equal 6-degree angular intervals around the rounded
    border — proper clock geometry. Every 5th (hour) is longer and brighter.
    Tick 0 = 12 o'clock (top centre), increases clockwise."""
    cx, cy = W / 2, H / 2
    margin = 3
    for i in range(60):
        angle = -math.pi / 2 + i * math.pi / 30   # 12 o'clock = -pi/2, CW
        x, y, nx, ny = _border_point(angle, cx, cy)
        is_hour = (i % 5 == 0)
        ln = 9 if is_hour else 4
        wd = 2 if is_hour else 1
        col = (120, 120, 130) if is_hour else (60, 60, 68)
        dr.line([(x + nx * margin, y + ny * margin),
                 (x + nx * (margin + ln), y + ny * (margin + ln))],
                fill=col, width=wd)


def draw_background(time_y, paw_cx, icon_cy,
                    cat_frame=None, cat_pos=None):
    """Pure black + clock ticks + painted colon + paw icon."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dr = ImageDraw.Draw(img)

    if cat_frame is not None and cat_pos is not None:
        img.paste(cat_frame, cat_pos)

    for dy in (-15, 15):
        dr.ellipse([184 - 5, time_y + 41 + dy - 5,
                    184 + 5, time_y + 41 + dy + 5], fill=WHITE)

    paw = lucide_icon(PAW_SVG, PINK, 2.8, 200)
    paint_icon(img, paw, paw_cx, icon_cy, 48)

    # clock ticks drawn directly (solid dim colours survive RGB565 dithering)
    draw_clock_ticks(dr)

    return img.convert("RGB")


def render_digits(size, weight, fill):
    f = font(int(size[1] * 0.90), weight)
    out = []
    for d in "0123456789":
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.text((size[0] / 2, size[1] / 2 - 1), d, font=f,
                fill=fill, anchor="mm")
        out.append(img)
    return out


def measure_weekday_width():
    """Measure the widest full day name so the cell fits it without clipping."""
    f = font(int(WEEK_H * 0.68), 700)
    names = ["Sunday", "Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday"]
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    return int(max(tmp.textlength(n, font=f) for n in names) + 10)


def render_weekday(week_w):
    """Seven full weekday-name images, Sunday-first."""
    names = ["Sunday", "Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday"]
    f = font(int(WEEK_H * 0.68), 700)
    out = []
    for nm in names:
        img = Image.new("RGBA", (week_w, WEEK_H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.text((week_w / 2, WEEK_H / 2), nm, font=f,
                fill=PINK, anchor="mm")
        out.append(img)
    return out


def render_ampm():
    """AM / PM / blank images for PictureSet type 50 (3 states: AM, PM, 24H)."""
    f = font(int(AMPM_H * 0.72), 700)
    out = []
    for label in ("AM", "PM", ""):
        img = Image.new("RGBA", (AMPM_W, AMPM_H), (0, 0, 0, 0))
        if label:
            dr = ImageDraw.Draw(img)
            dr.text((AMPM_W / 2, AMPM_H / 2), label, font=f,
                    fill=WHITE, anchor="mm")
        out.append(img)
    return out


# ---- weather ----

_WDATA = json.load(open(os.path.join(os.path.dirname(__file__), "weather_data.json")))
_WSVGS = _WDATA["svgs"]
_WSTATES = _WDATA["states"]
WCOLOR = (160, 195, 235)   # soft blue — distinguishes weather from warm cat theme


def render_weather_icons():
    """24 weather icons for PictureSet type 248, rendered from lucide SVGs."""
    out = []
    for icon_name in _WSTATES:
        body = _WSVGS.get(icon_name, _WSVGS["cloud"])
        icon = lucide_icon(body, WCOLOR, 2, 200)
        out.append(icon.resize((WICON, WICON), Image.LANCZOS))
    return out


def render_degree():
    """Degree ° suffix glyph matching SMALL digit height."""
    f = font(int(DEG_H * 0.55), 700)
    img = Image.new("RGBA", (DEG_W, DEG_H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.text((DEG_W / 2, DEG_H / 2 - 2), "\u00b0", font=f,
            fill=WHITE, anchor="mm")
    return img


def digit_group_suffix(indices, suffix, x, y, kind, w, h, f23=5):
    """f6 Digits with a suffix glyph (field 6) — e.g. the ° after temperature."""
    inner = (msg(1, bytes(indices))
             + msg(3, u(1, x) + u(2, y))
             + u(5, kind)
             + u(6, suffix)
             + u(21, w) + u(22, h) + u(23, f23))
    return msg(1, msg(6, inner))


# --------------------------------------------------------------------------- #
#  Protobuf element helpers
# --------------------------------------------------------------------------- #

def picture_set(indices, x, y, type_):
    inner = msg(1, bytes(indices)) + msg(2, u(1, x) + u(2, y)) + u(3, type_)
    return msg(1, msg(5, inner))


def digit_group_centre(indices, x, y, kind, w, h, f23=5, suffix=0):
    """f6 Digits with align=1 (centre). If suffix is set, a suffix glyph (e.g.
    the paw icon) is drawn after the number and INCLUDED in the centring —
    so the whole [number🐾] component stays centred at any digit count."""
    inner = (msg(1, bytes(indices))
             + msg(3, u(1, x) + u(2, y))
             + u(4, 1)
             + u(5, kind)
             + (u(6, suffix) if suffix else b"")
             + u(21, w) + u(22, h) + u(23, f23))
    return msg(1, msg(6, inner))


def anim(frames, ms, x, y):
    pos = msg(2, u(1, x) + u(2, y))
    return msg(1, msg(20, msg(1, bytes(frames)) + pos + u(3, ms) + u(5, 1)))


def background(idx):
    return msg(1, msg(4, u(1, idx) + msg(2, b"")))


# --------------------------------------------------------------------------- #
#  Build
# --------------------------------------------------------------------------- #

def build(animated=True):
    cat_frames, cat_pos, cat_size = load_cat_frames()
    bw, bh = BIG
    sw, sh = SMALL

    # ---- centred section: cat, time ----
    cat_bottom = cat_pos[1] + cat_size[1]
    time_y = cat_bottom + 8
    total = 4 * bw + 16
    hour_x = (W - total) // 2
    min_x = hour_x + 2 * bw + 16
    ampm_x = min_x + 2 * bw               # touching the minute digits
    ampm_y = time_y + bh - AMPM_H - 10

    # ---- bottom row: vertical icon-over-number, two columns ----
    comp_y = time_y + bh + 30
    icon_cy = comp_y + 20
    digits_y = comp_y + 64
    paw_cx = 100
    wx_cx = 285
    wicon_x = wx_cx - WICON // 2
    wicon_y = icon_cy - WICON // 2
    degc_x = wx_cx + 2 * sw // 2 + 4    # °C right after 2-digit temp

    if animated:
        bg = draw_background(time_y, paw_cx, icon_cy)
    else:
        bg = draw_background(time_y, paw_cx, icon_cy, cat_frames[0], cat_pos)
    big = render_digits(BIG, 800, WHITE + (255,))
    small = render_digits(SMALL, 800, WHITE + (255,))
    ampm = render_ampm()
    weather = render_weather_icons()

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(bg, W, H)]
    if animated:
        for f in cat_frames:
            blobs.append(lvgl_header(*cat_size, cf=4) + encode_pixels(f, *cat_size))
    for g in big:
        blobs.append(lvgl_header(*BIG, cf=5) + encode_pixels_alpha(g, *BIG))
    for g in small:
        blobs.append(lvgl_header(*SMALL, cf=5) + encode_pixels_alpha(g, *SMALL))
    for g in ampm:
        blobs.append(lvgl_header(AMPM_W, AMPM_H, cf=5)
                     + encode_pixels_alpha(g, AMPM_W, AMPM_H))
    for g in weather:
        blobs.append(lvgl_header(WICON, WICON, cf=5)
                     + encode_pixels_alpha(g, WICON, WICON))

    n_cat = len(cat_frames) if animated else 0
    i_bg = 1
    i_cat0 = i_bg + 1
    i_big0 = i_cat0 + n_cat
    i_sm0 = i_big0 + 10
    i_ap0 = i_sm0 + 10
    i_wx0 = i_ap0 + 3

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    big_refs = list(range(i_big0, i_big0 + 10))
    sm_refs = list(range(i_sm0, i_sm0 + 10))
    ap_refs = list(range(i_ap0, i_ap0 + 3))
    wx_refs = list(range(i_wx0, i_wx0 + 24))
    cat_refs = list(range(i_cat0, i_cat0 + n_cat))

    layout = background(i_bg)
    if animated:
        layout += anim(cat_refs, FRAME_MS, cat_pos[0], cat_pos[1])
    layout += (
        digit_group(big_refs, hour_x, time_y, 12, bw, bh, f23=5)
        + digit_group(big_refs, min_x, time_y, 13, bw, bh, f23=5)
        + picture_set(ap_refs, ampm_x, ampm_y, 50)
        + digit_group_centre(sm_refs, paw_cx, digits_y, 0, sw, sh, f23=5)
        + picture_set(wx_refs, wicon_x, wicon_y, 248)
        + digit_group_centre(sm_refs, wx_cx, digits_y, 4, sw, sh, f23=5)
        + u(5, 1)
    )

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8, f"image count {cnt} exceeds firmware limit 0x3F8"
    assert len(layout) <= 0x800, f"layout {len(layout)} exceeds 0x800"
    pos = dict(time_y=time_y, digits_y=digits_y, icon_cy=icon_cy,
               hour_x=hour_x, min_x=min_x, ampm_x=ampm_x, ampm_y=ampm_y,
               paw_cx=paw_cx, wicon_x=wicon_x, wicon_y=wicon_y,
               wx_cx=wx_cx, degc_x=degc_x)
    return blob, dict(n=len(blobs), cnt=cnt, len3=len(layout), animated=animated,
                      cat_size=cat_size, cat_pos=cat_pos, pos=pos,
                      big=big, small=small, ampm=ampm,
                      weather=weather, bg=bg,
                      cat=cat_frames if animated else None)


def preview(info):
    bg = info["bg"].convert("RGBA")
    p = info["pos"]
    for i, d in enumerate("10"):
        bg.alpha_composite(info["big"][int(d)], (p["hour_x"] + i * BIG[0], p["time_y"]))
    for i, d in enumerate("08"):
        bg.alpha_composite(info["big"][int(d)], (p["min_x"] + i * BIG[0], p["time_y"]))
    bg.alpha_composite(info["ampm"][1], (p["ampm_x"], p["ampm_y"]))
    # steps (paw in bg, digits centred below)
    dy = p["digits_y"]
    for i, d in enumerate("604"):
        bg.alpha_composite(info["small"][int(d)],
                           (p["paw_cx"] - 3 * SMALL[0] // 2 + i * SMALL[0], dy))
    # weather (icon + temp, °C in bg)
    bg.alpha_composite(info["weather"][0], (p["wicon_x"], p["wicon_y"]))
    for i, d in enumerate("72"):
        bg.alpha_composite(info["small"][int(d)],
                           (p["wx_cx"] - 2 * SMALL[0] // 2 + i * SMALL[0], dy))
    if info.get("animated") and info.get("cat"):
        bg.alpha_composite(info["cat"][0].convert("RGBA"), info["cat_pos"])
    bg.convert("RGB").save("/tmp/bongo_preview.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="bongo.bin")
    ap.add_argument("--static", action="store_true",
                    help="disable animation (bake cat into background)")
    args = ap.parse_args()

    blob, info = build(animated=not args.static)
    open(args.out, "wb").write(blob)
    mode = "ANIMATED" if info["animated"] else "STATIC"
    print(f"wrote {args.out}  {len(blob):,} bytes   [{mode}]")
    print(f"  images   : {info['n']}   cnt={info['cnt']}   len3={info['len3']}")
    print(f"  cat      : {info['cat_size']} @ {info['cat_pos']}")
    print(f"  limits   : cnt<=1016 {info['cnt'] <= 0x3F8}   "
          f"len3<=2048 {info['len3'] <= 0x800}")
    preview(info)
    print("preview -> /tmp/bongo_preview.png")


if __name__ == "__main__":
    main()
