#!/usr/bin/env python3
"""An analogue KW80 watchface whose hands track the real time.

    ../.venv/bin/python tools/wfhands.py hands.bin
    ../.venv/bin/python tools/wfupload.py --raw hands.bin --send

Unlike the f20 animation element — which cycles frames on a free-running timer
and knows nothing about the clock — the f23 vector element is bound to a data
source and rotates about the centre of its canvas. Sources 150/153/154 are
hour, minute and second. This is what the vendor's own WF03/WF04/WF05 use.

See docs/10-watchface-capabilities.md §4.6 for the element schema.

Cost: the entire hand set is ~500 bytes of layout and zero images. Everything
that is not a hand lives in one background bitmap.
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import TRAILER, encode_pixels_alpha, digit_group, msg, u  # noqa: E402

W, H = 368, 448
THUMB = (180, 219)
CX, CY = W // 2, H // 2          # rotation centre — the canvas centre
DIGIT = (26, 36)

SF = "/System/Library/Fonts/SFCompact.ttf"
ACCENT = (255, 176, 46)
DIM = (58, 62, 72)
FAINT = (30, 33, 40)


def sf(size, weight=400):
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([19, 400, weight])
    except Exception:
        pass
    return f


# ------------------------------------------------------------------ protobuf
def point(x, y):
    return msg(2, u(1, int(x)) + u(2, int(y)))


def circle(x, y, r, start=None, end=360):
    body = msg(1, u(1, int(x)) + u(2, int(y))) + u(2, int(r))
    if start:
        body += u(3, int(start))
    return msg(3, body + u(4, int(end)))


def rgb(r, g, b):
    out = b""
    if r:
        out += u(1, r)
    if g:
        out += u(2, g)
    if b:
        out += u(3, b)
    return out


def capsule(source, half_w, top, bottom, colour):
    """A rounded hand: rectangle plus a circle at each end, as the vendor does.

    `top`/`bottom` are absolute y in canvas space; the pivot is the canvas
    centre, so a bottom past CY gives a counterweight tail.
    """
    body = msg(1, u(3, W) + u(4, H))
    body += (point(CX - half_w, top) + point(CX - half_w, bottom)
             + point(CX + half_w, bottom) + point(CX + half_w, top))
    body += circle(CX, top, half_w) + circle(CX, bottom, half_w)
    body += u(5, 360) + u(6, source)
    body += msg(7, rgb(*colour)) + msg(8, rgb(*colour))
    return msg(1, msg(23, body))


def dot(r, colour):
    body = msg(1, u(3, W) + u(4, H)) + circle(CX, CY, r)
    body += u(5, 360) + u(6, 255)                    # 255 = static, no rotation
    body += msg(7, rgb(*colour)) + msg(8, rgb(*colour))
    return msg(1, msg(23, body))


# ------------------------------------------------------------------ artwork
def background():
    img = Image.new("RGB", (W, H), (8, 9, 12))
    dr = ImageDraw.Draw(img)
    r = 176

    # minute track
    for k in range(60):
        a = math.radians(k * 6 - 90)
        if k % 5 == 0:
            continue
        x, y = CX + r * math.cos(a), CY + r * math.sin(a)
        dr.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=FAINT)

    # hour markers, 12/3/6/9 longer and brighter
    for k in range(12):
        a = math.radians(k * 30 - 90)
        cardinal = k % 3 == 0
        inner = r - (26 if cardinal else 14)
        dr.line([(CX + inner * math.cos(a), CY + inner * math.sin(a)),
                 (CX + r * math.cos(a), CY + r * math.sin(a))],
                fill=(230, 232, 238) if cardinal else DIM,
                width=4 if cardinal else 3)

    # hour numerals just inside the markers
    f = sf(23, 500)
    for k, lbl in ((1, "1"), (2, "2"), (4, "4"), (5, "5"),
                   (7, "7"), (8, "8"), (10, "10"), (11, "11")):
        a = math.radians(k * 30 - 90)
        rr = r - 44
        dr.text((CX + rr * math.cos(a), CY + rr * math.sin(a)), lbl,
                font=f, fill=(126, 130, 140), anchor="mm")

    # date well, bottom — the day number is drawn live over this
    dr.rounded_rectangle([CX - 34, CY + 74, CX + 34, CY + 118], radius=10,
                         outline=(46, 49, 58), width=2)

    # brand line, top
    f = sf(15, 620)
    label = "KW80"
    total = sum(dr.textlength(c, font=f) + 6 for c in label) - 6
    x = CX - total / 2
    for c in label:
        dr.text((x, CY - 116), c, font=f, fill=ACCENT, anchor="lm")
        x += dr.textlength(c, font=f) + 6
    return img


def digits():
    f = sf(int(DIGIT[1] * 0.82), 420)
    out = []
    for d in "0123456789":
        g = Image.new("RGBA", DIGIT, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((DIGIT[0] / 2, DIGIT[1] / 2), d, font=f,
                               fill=(236, 238, 244, 255), anchor="mm")
        out.append(g)
    return out


# ------------------------------------------------------------------ build
def build():
    bg = background()
    glyphs = digits()

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(bg, W, H)]
    for g in glyphs:
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    dw, dh = DIGIT
    layout = (
        msg(1, msg(4, u(1, 1) + msg(2, b"")))                      # background
        + digit_group(list(range(2, 12)), CX - dw, CY + 78, 17,    # day of month
                      dw, dh, f23=5)
        + capsule(150, 7, CY - 108, CY - 18, (236, 238, 244))      # hour
        + capsule(153, 5, CY - 156, CY - 18, (236, 238, 244))      # minute
        + capsule(154, 2, CY - 164, CY + 40, ACCENT)               # second + tail
        + dot(9, (236, 238, 244))
        + dot(4, (8, 9, 12))
        + u(5, 1)
    )

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8, f"too many images: {cnt}"
    assert len(layout) <= 0x800, f"layout too big: {len(layout)}"
    return blob, len(layout), bg, glyphs


def preview(bg, glyphs, path, hh=10, mm=9, ss=37):
    """Render what the watch will show, hands included."""
    img = bg.convert("RGBA")
    dr = ImageDraw.Draw(img)

    def hand(angle, half_w, top, bottom, colour):
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(CX - half_w, top), (CX - half_w, bottom),
               (CX + half_w, bottom), (CX + half_w, top)]
        rot = [((x - CX) * ca - (y - CY) * sa + CX,
                (x - CX) * sa + (y - CY) * ca + CY) for x, y in pts]
        dr.polygon(rot, fill=colour)
        for _, y in ((0, top), (0, bottom)):
            px = CX + (0) * ca - (y - CY) * sa
            py = CY + (0) * sa + (y - CY) * ca
            dr.ellipse([px - half_w, py - half_w, px + half_w, py + half_w],
                       fill=colour)

    hand((hh % 12 + mm / 60) * 30, 7, CY - 108, CY - 18, (236, 238, 244))
    hand((mm + ss / 60) * 6, 5, CY - 156, CY - 18, (236, 238, 244))
    hand(ss * 6, 2, CY - 164, CY + 40, ACCENT)
    dr.ellipse([CX - 9, CY - 9, CX + 9, CY + 9], fill=(236, 238, 244))
    dr.ellipse([CX - 4, CY - 4, CX + 4, CY + 4], fill=(8, 9, 12))

    dw, dh = DIGIT
    for i, d in enumerate("07"):
        img.alpha_composite(glyphs[int(d)], (CX - dw + i * dw, CY + 78))
    img.convert("RGB").save(path)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "hands.bin"
    blob, layout_len, bg, glyphs = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   layout {layout_len}/2048 B")
    preview(bg, glyphs, "/tmp/hands_preview.png")
    print("preview -> /tmp/hands_preview.png  (hands drawn at 10:09:37)")


if __name__ == "__main__":
    main()
