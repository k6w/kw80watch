#!/usr/bin/env python3
"""Modular-Ultra-style watchface for the KW80.

    ../.venv/bin/python tools/wfmodular.py modular.bin

Everything except the time is drawn into the background image; the hour and
minute are live, rendered as cf=5 alpha glyphs in SF Compact — the same family
watchOS uses, so the digits match closely.

The complications are static artwork. The protocol exposes no elements for
compass heading, altitude, or arbitrary gauges, so those are painted values.
"""
import math
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import TRAILER, encode_pixels_alpha, digit_group, msg, u  # noqa: E402

W, H = 368, 448
THUMB = (180, 219)
DIGIT = (66, 88)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
ORANGE = (255, 149, 0)
GREEN = (48, 209, 88)
YELLOW = (255, 214, 10)
GREY = (142, 142, 147)
DARK = (28, 28, 30)

SF = "/System/Library/Fonts/SFCompact.ttf"
SFR = "/System/Library/Fonts/SFCompactRounded.ttf"


def font(size, path=SF):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def ctext(dr, xy, s, f, fill, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, anchor=anchor)


def arc_gauge(dr, cx, cy, r, start, end, width, stops):
    """Multi-colour arc, stops = [(t0,t1,colour), ...] in 0..1 of the sweep."""
    for t0, t1, col in stops:
        dr.arc([cx - r, cy - r, cx + r, cy + r],
               start + (end - start) * t0, start + (end - start) * t1,
               fill=col, width=width)


def draw_background():
    img = Image.new("RGB", (W, H), BLACK)
    dr = ImageDraw.Draw(img)

    f_tiny = font(13)
    f_small = font(15)
    f_mid = font(19)
    f_big = font(30, SFR)

    # ---- edge tick scales -------------------------------------------------
    for i in range(34):
        y = 96 + i * 9
        long = i % 5 == 0
        dr.line([(6, y), (6 + (13 if long else 8), y)],
                fill=ORANGE if i > 6 else GREY, width=2)
        dr.line([(W - 6 - (13 if long else 8), y), (W - 6, y)],
                fill=ORANGE if i > 6 else GREY, width=2)
    ctext(dr, (14, 424), "FT", f_tiny, GREY, "lm")
    ctext(dr, (W - 14, 424), "MI", f_tiny, GREY, "rm")

    # ---- top left: arc gauge ---------------------------------------------
    cx, cy, r = 74, 92, 40
    arc_gauge(dr, cx, cy, r, 138, 402, 7,
              [(0.0, 0.35, GREEN), (0.35, 0.72, YELLOW), (0.72, 1.0, ORANGE)])
    ctext(dr, (cx, cy - 2), "77", font(34, SFR), WHITE)
    ctext(dr, (cx - 15, cy + 22), "57", f_small, GREEN)
    ctext(dr, (cx + 17, cy + 22), "77", f_small, ORANGE)
    ctext(dr, (34, 50), "500", f_tiny, GREY, "lm")

    # ---- top middle: compass rose ----------------------------------------
    cx, cy, r = 184, 92, 40
    for i in range(60):
        a = math.radians(i * 6)
        inner = r - (9 if i % 15 == 0 else 5)
        dr.line([(cx + inner * math.sin(a), cy - inner * math.cos(a)),
                 (cx + r * math.sin(a), cy - r * math.cos(a))],
                fill=GREY if i % 15 else WHITE, width=1)
    for lbl, a in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        ar = math.radians(a)
        ctext(dr, (cx + (r - 19) * math.sin(ar), cy - (r - 19) * math.cos(ar)),
              lbl, f_tiny, WHITE)
    dr.line([(cx - 11, cy), (cx + 11, cy)], fill=WHITE, width=2)
    dr.line([(cx, cy - 11), (cx, cy + 11)], fill=WHITE, width=2)

    # ---- top right: waypoint ---------------------------------------------
    cx, cy, r = 294, 92, 40
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DARK)
    dr.ellipse([cx - 17, cy - 20, cx + 17, cy + 14], outline=WHITE, width=3)
    dr.ellipse([cx - 6, cy - 9, cx + 6, cy + 3], fill=WHITE)
    dr.line([(cx, cy + 12), (cx, cy + 23)], fill=WHITE, width=3)
    ctext(dr, (W - 34, 50), "150", f_tiny, GREY, "rm")

    # ---- time colon (digits are live) ------------------------------------
    dr.ellipse([174, 178, 186, 190], fill=WHITE)
    dr.ellipse([174, 208, 186, 220], fill=WHITE)

    # ---- heading ----------------------------------------------------------
    ctext(dr, (26, 248), "304°", f_big, WHITE, "lm")
    ctext(dr, (92, 250), "NW", font(22), WHITE, "lm")

    # ---- compass strip ----------------------------------------------------
    for lbl, x in (("240", 44), ("270", 116), ("300", 190), ("330", 262), ("0", 330)):
        ctext(dr, (x, 272), lbl, f_tiny, ORANGE)
    for i in range(74):
        x = 20 + i * 4.5
        maj = i % 9 == 0
        dr.line([(x, 288), (x, 288 + (16 if maj else 8))],
                fill=WHITE if maj else GREY, width=1)
    dr.polygon([(200, 292), (208, 306), (192, 306)], fill=ORANGE)
    for lbl, x in (("W", 74), ("NW", 200), ("N", 300)):
        ctext(dr, (x, 316), lbl, f_tiny, WHITE)

    # ---- bottom complications --------------------------------------------
    cx, cy, r = 96, 372, 37                     # walkie-talkie
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DARK)
    dr.rounded_rectangle([cx - 15, cy - 17, cx + 15, cy + 19], radius=7,
                         outline=YELLOW, width=3)
    dr.line([(cx + 9, cy - 26), (cx + 9, cy - 18)], fill=YELLOW, width=3)
    dr.ellipse([cx - 8, cy - 9, cx + 8, cy + 7], outline=YELLOW, width=3)

    cx = 184                                     # sunrise
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DARK)
    dr.arc([cx - 15, cy - 8, cx + 15, cy + 22], 180, 360, fill=YELLOW, width=4)
    dr.line([(cx - 24, cy + 14), (cx + 24, cy + 14)], fill=WHITE, width=2)
    for k in (-1, 0, 1):
        dr.line([(cx + k * 15, cy - 20 + abs(k) * 5), (cx + k * 15, cy - 14 + abs(k) * 5)],
                fill=YELLOW, width=2)

    cx, r = 276, 39                              # UV-style rainbow gauge
    arc_gauge(dr, cx, cy, r, 130, 410, 7,
              [(0.0, 0.25, GREEN), (0.25, 0.5, YELLOW),
               (0.5, 0.75, ORANGE), (0.75, 1.0, (255, 69, 58))])
    ctext(dr, (cx + 2, cy - 4), "10", font(31, SFR), WHITE)
    dr.ellipse([cx - 5, cy + 16, cx + 5, cy + 26], outline=YELLOW, width=2)

    # ---- altitude ---------------------------------------------------------
    ctext(dr, (W // 2, 430), "~ 220 FT", font(18), ORANGE)
    return img


def render_digits():
    f = font(int(DIGIT[1] * 0.98), SF)
    out = []
    for d in "0123456789":
        img = Image.new("RGBA", DIGIT, (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.text((DIGIT[0] / 2, DIGIT[1] / 2), d, font=f, fill=(255, 255, 255, 255),
                anchor="mm")
        out.append(img)
    return out


def build():
    bg = draw_background()
    digits = render_digits()

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(bg, W, H)]
    for g in digits:
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    idx = list(range(2, 12))
    layout = (msg(1, msg(4, u(1, 1) + msg(2, b"")))
              + digit_group(idx, 30, 155, 12, *DIGIT, f23=5)    # hour  10
              + digit_group(idx, 194, 155, 13, *DIGIT, f23=5)   # minute 09
              + u(5, 1))

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8 and len(layout) <= 0x800
    return blob, len(blobs), cnt, len(layout)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "modular.bin"
    blob, n, cnt, len3 = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   images={n} cnt={cnt} len3={len3}")
    draw_background().save("/tmp/modular_preview.png")
    print("preview -> /tmp/modular_preview.png")


if __name__ == "__main__":
    main()
