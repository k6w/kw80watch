#!/usr/bin/env python3
"""A KW80 watchface built entirely out of moving arc bands.

    ../.venv/bin/python tools/wfhalo.py halo.bin
    ../.venv/bin/python tools/wfupload.py --raw halo.bin --send

Two concentric bands sweep around the dial, one on the minute and one on the
hour, plus a dot orbiting on the second. Everything moves with the real clock —
no frame animation, no timer. The whole moving layer is vector, so it costs
about 700 bytes of layout and not one image.

How an arc band is made (docs/10-watchface-capabilities.md §4.6):

  * f23's circle primitive draws a **filled pie sector**, 0° = east, sweeping
    counter-clockwise, with no stroke width.
  * So a band = an outer sector in the accent colour, then a separate f23 with
    a smaller full disc in the background colour drawn over it as a mask.
  * Both elements carry the same rotation source, so they turn together.
  * A shape must be authored pointing up to read as "zero". A band whose
    leading edge sits at 12 o'clock and runs W degrees clockwise is
    start = 90 - W, end = 90.
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
CX, CY = W // 2, H // 2
DIGIT = (72, 96)
DAY = (22, 30)

BG = (7, 8, 11)
MINUTE_COL = (0, 208, 255)
HOUR_COL = (255, 92, 128)
SECOND_COL = (255, 190, 60)

SF = "/System/Library/Fonts/SFCompact.ttf"

# band geometry: (outer r, inner r, sweep degrees, colour, rotation source)
BANDS = [(174, 158, 100, MINUTE_COL, 153),
         (150, 134, 70, HOUR_COL, 150)]

# --fast rebinds every moving element to the second hand, so a full revolution
# takes 60 s instead of an hour or half a day. For verifying motion, not wear.
FAST = "--fast" in sys.argv
SECOND_SRC = 154


def moving(source):
    return SECOND_SRC if FAST else source


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


def angle(a):
    """Wrap to 0..360. 360 is kept as-is — it means a full circle, not zero."""
    a = int(a)
    return 360 if a and a % 360 == 0 else a % 360


def sector(x, y, r, start, end):
    inner = msg(1, u(1, int(x)) + u(2, int(y))) + u(2, int(r))
    if start is not None and angle(start):
        inner += u(3, angle(start))
    return msg(3, inner + u(4, angle(end)))


def span(x, y, r, lead, sweep):
    """A sector of width `sweep` whose leading edge sits at `lead` degrees.

    **The renderer will not draw a sector whose start exceeds its end** — that
    is, one that crosses 0°/360°. Proven on device: an authored 350°->90° band
    rendered as nothing while a 240°->310° band on the same face worked. So a
    wrapped span is emitted as two sectors meeting at 0°. Both go in the same
    element, which keeps them one colour and one rotation.
    """
    lead = angle(lead) % 360
    start = lead - sweep
    if start >= 0:
        return sector(x, y, r, start, lead)
    parts = b""
    if lead > 0:
        parts += sector(x, y, r, 0, lead)
    return parts + sector(x, y, r, start + 360, 360)


def vector(source, shapes, colour):
    body = msg(1, u(3, W) + u(4, H)) + shapes + u(5, 360) + u(6, source)
    return msg(1, msg(23, body + msg(7, rgb(*colour)) + msg(8, rgb(*colour))))


def band(outer, inner, sweep, colour, source, phase=0):
    """Outer sector then a background-coloured disc over it — two elements.

    A full ring is `sweep >= 360`; it must be authored as a plain 0..360 disc,
    not as a sector, because 90-360 wraps back to 90 and would draw nothing.
    `phase` moves the leading edge clockwise from 12 o'clock.
    """
    if sweep >= 360:
        head = sector(CX, CY, outer, None, 360)
    else:
        head = span(CX, CY, outer, 90 - phase, sweep)
    return (vector(source, head, colour)
            + vector(source, sector(CX, CY, inner, None, 360), BG))


def dot(x, y, r, colour):
    return vector(255, sector(x, y, r, None, 360), colour)


def poly_bar(half_w, top, bottom):
    """A vertical bar as polygon points — rotates about the canvas centre."""
    pts = [(CX - half_w, top), (CX - half_w, bottom),
           (CX + half_w, bottom), (CX + half_w, top)]
    return b"".join(msg(2, u(1, int(x)) + u(2, int(y))) for x, y in pts)


def orbit(r, dot_r, colour, source):
    """A dot parked `r` above the centre, rotated by `source`."""
    return vector(source, sector(CX, CY - r, dot_r, None, 360), colour)


def faint(col):
    return tuple(int(c * 0.20) for c in col)


def ring_stack():
    """Every ring, in draw order, as vector elements.

    A mask disc wipes everything already drawn inside its radius, so the tracks
    cannot live in the background bitmap — the outer band's mask would erase the
    inner track. Interleaving track and band per ring, outermost first, is the
    only ordering that survives.
    """
    out = b""
    for i, (outer, inner, sweep, col, source) in enumerate(BANDS):
        # In fast mode both bands share one source, so offset the inner one —
        # otherwise they lock together and only read as a single moving edge.
        phase = 140 * i if FAST else 0
        out += band(outer, inner, 360, faint(col), 255)                # track
        out += band(outer, inner, sweep, col, moving(source), phase)   # sweep
    return out


# ------------------------------------------------------------------ artwork
def background():
    """Only what sits outside the innermost mask: the tick ring."""
    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)
    for k in range(12):
        a = math.radians(k * 30 - 90)
        r0, r1 = 180, 180 + (12 if k % 3 == 0 else 7)
        dr.line([(CX + r0 * math.cos(a), CY + r0 * math.sin(a)),
                 (CX + r1 * math.cos(a), CY + r1 * math.sin(a))],
                fill=(120, 126, 140) if k % 3 == 0 else (46, 50, 60),
                width=3 if k % 3 == 0 else 2)
    return img


def glyphs(size, weight, colour):
    w, h = size
    f = sf(int(h * 0.88), weight)
    out = []
    for d in "0123456789":
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((w / 2, h / 2), d, font=f,
                               fill=colour + (255,), anchor="mm")
        out.append(g)
    return out


# ------------------------------------------------------------------ build
def build():
    bg = background()
    big = glyphs(DIGIT, 260, (240, 243, 250))
    small = glyphs(DAY, 520, (150, 156, 170))

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(bg, W, H)]
    for g in big:
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))
    for g in small:
        blobs.append(lvgl_header(*DAY, cf=5) + encode_pixels_alpha(g, *DAY))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    dw, dh = DIGIT
    sw, sh = DAY
    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))          # background
    layout += ring_stack()                                   # tracks + sweeps
    for dy in (-24, 24):                                     # colon
        layout += dot(CX, CY + dy, 5, (90, 96, 110))
    layout += orbit(196, 5, SECOND_COL, SECOND_SRC)          # orbiting dot
    if FAST:
        # a rotating capsule too, so polygon rotation is exercised alongside
        # the sectors, and a number that visibly ticks every second
        layout += vector(SECOND_SRC, poly_bar(3, CY - 118, CY - 40),
                         (255, 255, 255))
    layout += digit_group(list(range(2, 12)), CX - 2 * dw - 14, CY - dh // 2,
                          12, dw, dh, f23=5)                 # hour
    layout += digit_group(list(range(2, 12)), CX + 14, CY - dh // 2,
                          13, dw, dh, f23=5)                 # minute
    layout += digit_group(list(range(12, 22)), CX - sw, CY + 130,
                          14 if FAST else 17, sw, sh, f23=5)  # seconds / day
    layout += u(5, 1)

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    assert cnt <= 0x3F8, f"too many images: {cnt // 4}"
    assert len(layout) <= 0x800, f"layout {len(layout)} > 2048"
    return (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER), len(layout), bg, big, small


def preview(bg, big, small, path, hh=10, mm=41, ss=27):
    """Draw what the watch will show. Sectors are pies; mask discs go over."""
    img = bg.convert("RGBA")
    dr = ImageDraw.Draw(img)

    def pie(r, a0, a1, col):
        # PIL: 0 deg = east, clockwise. Device: 0 deg = east, counter-clockwise.
        dr.pieslice([CX - r, CY - r, CX + r, CY + r], -a1, -a0, fill=col)

    turns = (mm * 6, (hh % 12 + mm / 60) * 30)
    for (outer, inner, sweep, col, src), turn in zip(BANDS, turns):
        pie(outer, 0, 360, faint(col))                 # unlit track
        pie(inner, 0, 360, BG)
        pie(outer, 90 - sweep - turn, 90 - turn, col)  # lit sweep
        pie(inner, 0, 360, BG)

    for dy in (-24, 24):
        dr.ellipse([CX - 5, CY + dy - 5, CX + 5, CY + dy + 5], fill=(90, 96, 110))

    a = math.radians(ss * 6 - 90)
    x, y = CX + 196 * math.cos(a), CY + 196 * math.sin(a)
    dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=SECOND_COL)

    dw, dh = DIGIT
    for i, d in enumerate(f"{hh:02d}"):
        img.alpha_composite(big[int(d)], (CX - 2 * dw - 14 + i * dw, CY - dh // 2))
    for i, d in enumerate(f"{mm:02d}"):
        img.alpha_composite(big[int(d)], (CX + 14 + i * dw, CY - dh // 2))
    sw, sh = DAY
    for i, d in enumerate("08"):
        img.alpha_composite(small[int(d)], (CX - sw + i * sw, CY + 130))
    img.convert("RGB").save(path)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "halo.bin"
    blob, layout_len, bg, big, small = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   layout {layout_len}/2048 B")
    preview(bg, big, small, "/tmp/halo_preview.png")
    print("preview -> /tmp/halo_preview.png  (drawn at 10:41:27)")


if __name__ == "__main__":
    main()
