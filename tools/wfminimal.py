#!/usr/bin/env python3
"""A minimal, Apple-Watch-flavoured watchface for the KW80.

    ../.venv/bin/python tools/wfminimal.py minimal.bin

Design notes:
  * SF Compact is a variable font (Weight axis 1-1000) — the time is set in a
    genuine Ultralight, which is what gives Apple's faces their look.
  * Deep black, one accent colour, generous negative space.
  * Icons are drawn in SF Symbols style: uniform stroke, rounded caps.
    (SF Symbols itself is not installed, so they are hand-built paths.)

Formats proven on the device: background cf=4, glyphs cf=5 with real alpha.
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
DIGIT = (104, 132)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (120, 120, 128)
ACCENT = (255, 149, 0)          # Apple system orange
ACCENT2 = (255, 214, 10)

SF = "/System/Library/Fonts/SFCompact.ttf"


def sf(size, weight=400):
    """SF Compact at an arbitrary variable weight."""
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([19, 400, weight])   # optical size, GRAD, weight
    except Exception:
        pass
    return f


def tracked(dr, xy, text, f, fill, tracking=6, anchor_left=True):
    """Letterspaced text — Apple sets small caps labels with generous tracking."""
    x, y = xy
    if not anchor_left:
        total = sum(dr.textlength(c, font=f) + tracking for c in text) - tracking
        x -= total / 2
    for c in text:
        dr.text((x, y), c, font=f, fill=fill, anchor="lm")
        x += dr.textlength(c, font=f) + tracking


def icon_heart(dr, cx, cy, s, col, w=3):
    r = s * 0.30
    dr.arc([cx - s * 0.62, cy - s * 0.55, cx - s * 0.62 + 2 * r, cy - s * 0.55 + 2 * r],
           160, 350, fill=col, width=w)
    dr.arc([cx + s * 0.62 - 2 * r, cy - s * 0.55, cx + s * 0.62, cy - s * 0.55 + 2 * r],
           190, 20, fill=col, width=w)
    dr.line([(cx - s * 0.60, cy - s * 0.12), (cx, cy + s * 0.60)], fill=col, width=w)
    dr.line([(cx + s * 0.60, cy - s * 0.12), (cx, cy + s * 0.60)], fill=col, width=w)


def icon_flame(dr, cx, cy, s, col, w=3):
    """SF-Symbols-ish flame: one teardrop outline with an inner tick."""
    dr.line([(cx, cy - s * 0.85), (cx + s * 0.52, cy - s * 0.05)], fill=col, width=w)
    dr.line([(cx, cy - s * 0.85), (cx - s * 0.40, cy - s * 0.10)], fill=col, width=w)
    dr.arc([cx - s * 0.58, cy - s * 0.35, cx + s * 0.58, cy + s * 0.80],
           10, 170, fill=col, width=w)
    dr.arc([cx - s * 0.26, cy + s * 0.05, cx + s * 0.26, cy + s * 0.72],
           200, 340, fill=col, width=w)


def rounded_rect_point(box, r, t):
    """Point at fraction t (0..1) along a rounded-rectangle perimeter."""
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) - 2 * r, (y1 - y0) - 2 * r
    arc = math.pi * r / 2
    segs = [w, arc, h, arc, w, arc, h, arc]
    total = sum(segs)
    d = (t % 1.0) * total
    for i, L in enumerate(segs):
        if d <= L:
            u_ = d / L
            if i == 0: return (x0 + r + w * u_, y0)
            if i == 1:
                a = -math.pi / 2 + u_ * math.pi / 2
                return (x1 - r + r * math.cos(a), y0 + r + r * math.sin(a))
            if i == 2: return (x1, y0 + r + h * u_)
            if i == 3:
                a = u_ * math.pi / 2
                return (x1 - r + r * math.cos(a), y1 - r + r * math.sin(a))
            if i == 4: return (x1 - r - w * u_, y1)
            if i == 5:
                a = math.pi / 2 + u_ * math.pi / 2
                return (x0 + r + r * math.cos(a), y1 - r + r * math.sin(a))
            if i == 6: return (x0, y1 - r - h * u_)
            a = math.pi + u_ * math.pi / 2
            return (x0 + r + r * math.cos(a), y0 + r + r * math.sin(a))
        d -= L
    return (x0, y0)


def draw_background():
    img = Image.new("RGB", (W, H), BLACK)
    dr = ImageDraw.Draw(img)

    # --- progress border tracing the screen's own rounded-rect geometry ----
    pad = 8
    box = (pad, pad, W - pad, H - pad)
    radius = 52                                 # KW80 corner radius is 55
    start, sweep = 0.505, 0.74                  # begin bottom-centre, sweep CCW
    N = 1100
    for i in range(N):
        t = i / (N - 1)
        col = tuple(int(ACCENT[k] + (ACCENT2[k] - ACCENT[k]) * t) for k in range(3))
        x, y = rounded_rect_point(box, radius, start - t * sweep)
        dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=col)

    # --- date, letterspaced caps -------------------------------------------
    tracked(dr, (W / 2, 66), "WEDNESDAY 7", sf(21, 620), GREY, 5, anchor_left=False)

    # --- hairline under the time block -------------------------------------
    dr.line([(46, 372), (322, 372)], fill=(38, 38, 42), width=1)

    # --- metrics -----------------------------------------------------------
    icon_heart(dr, 96, 404, 17, ACCENT, 3)
    dr.text((124, 404), "72", font=sf(30, 320), fill=WHITE, anchor="lm")

    icon_flame(dr, 238, 404, 16, ACCENT, 3)
    dr.text((266, 404), "486", font=sf(30, 320), fill=WHITE, anchor="lm")

    return img


def render_digits():
    f = sf(int(DIGIT[1] * 1.06), 150)          # Ultralight
    out = []
    for d in "0123456789":
        img = Image.new("RGBA", DIGIT, (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.text((DIGIT[0] / 2, DIGIT[1] / 2 - 2), d, font=f,
                fill=(255, 255, 255, 255), anchor="mm")
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
              + digit_group(idx, 80, 100, 12, *DIGIT, f23=5)    # hour
              + digit_group(idx, 80, 232, 13, *DIGIT, f23=5)    # minute
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
    out = sys.argv[1] if len(sys.argv) > 1 else "minimal.bin"
    blob, n, cnt, len3 = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   images={n} cnt={cnt} len3={len3}")

    # preview with the digits composited in, so we can judge the real look
    bg = draw_background().convert("RGBA")
    digs = render_digits()
    for i, d in enumerate("10"):
        bg.alpha_composite(digs[int(d)], (80 + i * DIGIT[0], 100))
    for i, d in enumerate("09"):
        bg.alpha_composite(digs[int(d)], (80 + i * DIGIT[0], 232))
    bg.convert("RGB").save("/tmp/minimal_preview.png")
    print("preview (with digits) -> /tmp/minimal_preview.png")


if __name__ == "__main__":
    main()
