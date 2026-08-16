#!/usr/bin/env python3
"""Exactograph — an Apple-Watch-Series-11-style precision analogue for the KW80.

    ../.venv/bin/python tools/wfexactograph.py exactograph.bin
    ../.venv/bin/python tools/wfupload.py --raw exactograph.bin --send

The KW80's panel is 368x448, which is exactly Apple Watch 44 mm, so the dial
geometry is authored 1:1 rather than rescaled.

Everything on this face is live:

    hour / minute / second   f23 vector hands, sources 150 / 153 / 154
    weekday name             f5  picture set, type 52 (7 states, Sunday first)
    day of month             f6  digits, source 17
    heart rate               f6  digits, source 2
    battery                  f6  digits, source 9, with a '%' suffix glyph

Nothing is painted-on except the dial furniture. See
docs/10-watchface-capabilities.md for the element schema and the data-source
registry.

This is a lookalike for personal use on your own hardware. Apple's watch faces
are protected designs — don't ship this one to a marketplace.
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import TRAILER, encode_pixels_alpha, msg, u  # noqa: E402

W, H = 368, 448
THUMB = (180, 219)
CX, CY = W // 2, H // 2          # rotation pivot: the canvas centre

GLYPH = (19, 28)                 # one digit set, shared by all three readouts
DAY_BOX = (58, 20)               # weekday name graphics

BLACK = (0, 0, 0)
HAIRLINE = (44, 45, 50)
MINUTE_TICK = (116, 119, 128)
HOUR_TICK = (238, 240, 245)
NUMERAL = (238, 240, 245)
LABEL = (132, 136, 146)
HAND = (245, 246, 250)
ACCENT = (255, 149, 0)           # Apple system orange
RED = (255, 59, 48)              # Apple system red

SF = "/System/Library/Fonts/SFCompact.ttf"

R_OUTER = 176                    # hairline graduation ring
R_FINE = 168
R_MIN_IN = 157                   # minute ticks
R_HOUR_IN = 150                  # 5-minute ticks
R_NUMERAL = 130


def sf(size, weight=400):
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([19, 400, weight])
    except Exception:
        pass
    return f


# ------------------------------------------------------------------ protobuf
def rgb(r, g, b):
    return (u(1, r) if r else b"") + (u(2, g) if g else b"") + (u(3, b) if b else b"")


def disc(x, y, r):
    return msg(3, msg(1, u(1, int(x)) + u(2, int(y))) + u(2, int(r)) + u(4, 360))


def poly(pts):
    return b"".join(msg(2, u(1, int(x)) + u(2, int(y))) for x, y in pts)


def vector(source, shapes, colour):
    body = msg(1, u(3, W) + u(4, H)) + shapes + u(5, 360) + u(6, source)
    return msg(1, msg(23, body + msg(7, rgb(*colour)) + msg(8, rgb(*colour))))


def blade(source, tip_len, tail, half_base, half_tip, colour):
    """A tapered baton hand, authored pointing up.

    Four polygon points give the taper and a disc rounds the tip. There is
    deliberately **no disc at the base**: one there reads as a blob, and the
    tail is kept shorter than the centre cap so the cap hides the cut end.
    """
    top, bottom = CY - tip_len, CY + tail
    return vector(source,
                  poly([(CX - half_base, bottom), (CX - half_tip, top),
                        (CX + half_tip, top), (CX + half_base, bottom)])
                  + disc(CX, top, half_tip),
                  colour)


def digits(indices, cx, y, source, box, suffix=None, align=1):
    """f6 Digits. align=1 centres the number on `cx` (class B, from the corpus)."""
    w, h = box
    inner = msg(1, bytes(indices)) + msg(3, u(1, int(cx)) + u(2, int(y)))
    if align:
        inner += u(4, align)
    if source:
        inner += u(5, source)
    if suffix:
        inner += u(6, suffix)
    inner += u(21, w) + u(22, h) + u(23, 5)          # f23 = the glyphs' cf
    return msg(1, msg(6, inner))


def picture_set(indices, x, y, type_):
    return msg(1, msg(5, msg(1, bytes(indices))
                      + msg(2, u(1, int(x)) + u(2, int(y))) + u(3, type_)))


# ------------------------------------------------------------------ dial
def dial():
    img = Image.new("RGB", (W, H), BLACK)
    dr = ImageDraw.Draw(img)

    def ray(deg, r0, r1, col, width):
        a = math.radians(deg - 90)
        dr.line([(CX + r0 * math.cos(a), CY + r0 * math.sin(a)),
                 (CX + r1 * math.cos(a), CY + r1 * math.sin(a))],
                fill=col, width=width)

    # outermost hairline graduation: 240 marks = quarter-minute, the detail that
    # makes a chronometer dial read as an instrument rather than a clock
    for k in range(240):
        ray(k * 1.5, R_FINE, R_OUTER, HAIRLINE, 1)
    dr.ellipse([CX - R_OUTER, CY - R_OUTER, CX + R_OUTER, CY + R_OUTER],
               outline=HAIRLINE, width=1)

    # minute ticks, with every fifth longer and bright
    for k in range(60):
        if k % 5 == 0:
            ray(k * 6, R_HOUR_IN, R_FINE, HOUR_TICK, 3)
        else:
            ray(k * 6, R_MIN_IN, R_FINE, MINUTE_TICK, 2)

    # 12 / 3 / 6 / 9
    f = sf(34, 560)
    for deg, lbl in ((0, "12"), (90, "3"), (180, "6"), (270, "9")):
        a = math.radians(deg - 90)
        dr.text((CX + R_NUMERAL * math.cos(a), CY + R_NUMERAL * math.sin(a)),
                lbl, font=f, fill=NUMERAL, anchor="mm")

    # complication wells, inside the minute track so the hands sweep over them
    for x in (128, 242):
        dr.ellipse([x - 40, 300 - 40, x + 40, 300 + 40],
                   outline=(34, 35, 40), width=2)

    # heart glyph beside the heart-rate readout
    hx, hy, s = 128, 283, 7
    dr.ellipse([hx - s - 3, hy - s, hx + 3 - s + s, hy + s], fill=RED)
    dr.ellipse([hx - 3 + s - s, hy - s, hx + s + 3, hy + s], fill=RED)
    dr.polygon([(hx - s - 3, hy + 1), (hx + s + 3, hy + 1), (hx, hy + s + 7)],
               fill=RED)

    # 'BATT' label under the battery well
    dr.text((242, 283), "BATT", font=sf(11, 640), fill=LABEL, anchor="mm")
    return img


def glyph_set(box, weight, colour, chars="0123456789"):
    w, h = box
    f = sf(int(h * 0.84), weight)
    out = []
    for ch in chars:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((w / 2, h / 2), ch, font=f,
                               fill=colour + (255,), anchor="mm")
        out.append(g)
    return out


def weekday_set():
    w, h = DAY_BOX
    f = sf(17, 620)
    out = []
    for name in ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"):
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(g)
        x = 2
        for ch in name:                                  # letterspaced, Apple-ish
            dr.text((x, h / 2), ch, font=f, fill=LABEL + (255,), anchor="lm")
            x += dr.textlength(ch, font=f) + 3
        out.append(g)
    return out


# ------------------------------------------------------------------ build
def build():
    bg = dial()
    nums = glyph_set(GLYPH, 480, (240, 242, 248))
    pct = glyph_set(GLYPH, 480, LABEL, "%")
    days = weekday_set()

    images = [("o", bg, (W, H))]
    images += [("a", g, GLYPH) for g in nums]            # 2..11  digits 0-9
    images += [("a", g, GLYPH) for g in pct]             # 12     '%'
    images += [("a", g, DAY_BOX) for g in days]          # 13..19 SUN..SAT

    blobs = []
    for kind, img, size in images:
        enc = encode_pixels_alpha if kind == "a" else encode_pixels
        blobs.append(lvgl_header(*size, cf=5 if kind == "a" else 4)
                     + enc(img, *size))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    DIG = list(range(2, 12))
    gh = GLYPH[1]
    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))                  # dial

    # --- readouts, drawn under the hands the way Apple stacks them -----------
    layout += picture_set(list(range(13, 20)), 148, 132, 52)         # weekday
    layout += digits(DIG, 224, 130, 17, GLYPH)                       # day
    layout += digits(DIG, 128, 300 - gh // 2 + 7, 2, GLYPH)          # heart rate
    layout += digits(DIG, 242, 300 - gh // 2 + 7, 9, GLYPH, suffix=12)  # battery

    # --- hands, on top the way Apple stacks them ----------------------------
    layout += blade(150, 100, 8, 7, 4, HAND)                         # hour
    layout += blade(153, 150, 8, 5, 3, HAND)                         # minute
    layout += vector(154, poly([(CX - 2, CY + 38), (CX - 2, CY - 162),
                                (CX + 2, CY - 162), (CX + 2, CY + 38)])
                     + disc(CX, CY - 162, 2) + disc(CX, CY + 38, 6),
                     ACCENT)                                        # second
    layout += vector(255, disc(CX, CY, 9), HAND)                     # cap
    layout += vector(255, disc(CX, CY, 4), BLACK)
    layout += u(5, 1)

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    assert cnt <= 0x3F8, f"too many images: {cnt // 4}"
    assert len(layout) <= 0x800, f"layout {len(layout)} > 2048"
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    return blob, len(layout), bg, nums, pct, days


def preview(bg, nums, pct, days, path, hh=10, mm=41, ss=27, hr=82, batt=86):
    img = bg.convert("RGBA")
    dr = ImageDraw.Draw(img)
    gw, gh = GLYPH

    img.alpha_composite(days[6], (148, 132))                         # SAT
    for i, d in enumerate("08"):
        img.alpha_composite(nums[int(d)], (224 - gw + i * gw, 130))
    y = 300 - gh // 2 + 7
    s = f"{hr}"
    for i, d in enumerate(s):
        img.alpha_composite(nums[int(d)], (128 - len(s) * gw // 2 + i * gw, y))
    s = f"{batt}"
    tot = (len(s) + 1) * gw
    for i, d in enumerate(s):
        img.alpha_composite(nums[int(d)], (242 - tot // 2 + i * gw, y))
    img.alpha_composite(pct[0], (242 - tot // 2 + len(s) * gw, y))

    def rot(pts, ang):
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        return [((x - CX) * ca - (y - CY) * sa + CX,
                 (x - CX) * sa + (y - CY) * ca + CY) for x, y in pts]

    def hand(ang, tip, tail, hb, ht, col):
        top, bot = CY - tip, CY + tail
        dr.polygon(rot([(CX - hb, bot), (CX - ht, top),
                        (CX + ht, top), (CX + hb, bot)], ang), fill=col)
        for yy, r in ((top, ht), (bot, hb)):
            p = rot([(CX, yy)], ang)[0]
            dr.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    hand((hh % 12 + mm / 60) * 30, 100, 8, 7, 4, HAND)
    hand((mm + ss / 60) * 6, 150, 8, 5, 3, HAND)
    hand(ss * 6, 162, 38, 2, 2, ACCENT)
    p = rot([(CX, CY + 38)], ss * 6)[0]
    dr.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=ACCENT)
    dr.ellipse([CX - 9, CY - 9, CX + 9, CY + 9], fill=HAND)
    dr.ellipse([CX - 4, CY - 4, CX + 4, CY + 4], fill=BLACK)
    img.convert("RGB").save(path)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "exactograph.bin"
    blob, layout_len, bg, nums, pct, days = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   layout {layout_len}/2048 B")
    preview(bg, nums, pct, days, "/tmp/exacto_preview.png")
    print("preview -> /tmp/exacto_preview.png  (10:41:27, HR 82, batt 86%)")


if __name__ == "__main__":
    main()
