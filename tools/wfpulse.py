#!/usr/bin/env python3
"""A simple animated watchface for the KW80.

    ../.venv/bin/python tools/wfpulse.py pulse.bin

A fine tick ring with a soft gradient arc sweeping around it, and a large
SF Compact time in the middle.

Animation uses the f20 element: frames cycle on a fixed timer (f3 = ms per
frame). It is NOT bound to the clock — the KW80's format has no time-driven
rotation element, unlike CMF's tag 0x70.

Budget: full-screen cf=4 frames are 329,732 B each, so frame count is the main
cost. 4 frames + a glyph set lands around 1.5 MB, which fits the picture slot.
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
DIGIT = (96, 122)
FRAMES = 4
FRAME_MS = 200

SF = "/System/Library/Fonts/SFCompact.ttf"
ACCENT = (0, 210, 255)
DIM = (26, 30, 38)


def sf(size, weight=400):
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([19, 400, weight])
    except Exception:
        pass
    return f


def frame(i):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx, cy, r = W / 2, 196, 158

    # static tick ring — 60 marks, every 5th longer
    for k in range(60):
        a = math.radians(k * 6 - 90)
        inner = r - (15 if k % 5 == 0 else 8)
        dr.line([(cx + inner * math.cos(a), cy + inner * math.sin(a)),
                 (cx + r * math.cos(a), cy + r * math.sin(a))],
                fill=DIM, width=3 if k % 5 == 0 else 2)

    # sweeping arc — 120 degrees wide, advancing 90 degrees per frame, so the
    # bright head always overlaps the previous frame's tail and reads as motion
    head = -90 + i * (360 / FRAMES)
    for k in range(60):
        a = math.radians(k * 6 - 90)
        delta = ((k * 6 - 90) - head) % 360
        if delta > 120:
            continue
        t = 1.0 - delta / 120.0                    # 1 at the head, 0 at the tail
        col = tuple(int(DIM[j] + (ACCENT[j] - DIM[j]) * (t ** 1.6)) for j in range(3))
        inner = r - (15 if k % 5 == 0 else 8)
        dr.line([(cx + inner * math.cos(a), cy + inner * math.sin(a)),
                 (cx + r * math.cos(a), cy + r * math.sin(a))],
                fill=col, width=3 if k % 5 == 0 else 2)

    # date, letterspaced
    f = sf(19, 600)
    label = "WED 7"
    total = sum(dr.textlength(c, font=f) + 5 for c in label) - 5
    x = cx - total / 2
    for c in label:
        dr.text((x, 372), c, font=f, fill=(120, 122, 130), anchor="lm")
        x += dr.textlength(c, font=f) + 5

    # colon
    for dy in (-26, 26):
        dr.ellipse([cx - 5, cy + dy - 5, cx + 5, cy + dy + 5], fill=(255, 255, 255))
    return img


def render_digits():
    f = sf(int(DIGIT[1] * 1.02), 300)
    out = []
    for d in "0123456789":
        img = Image.new("RGBA", DIGIT, (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.text((DIGIT[0] / 2, DIGIT[1] / 2), d, font=f,
                fill=(255, 255, 255, 255), anchor="mm")
        out.append(img)
    return out


def anim_group(indices, ms):
    return msg(1, msg(20, msg(1, bytes(indices)) + msg(2, b"") + u(3, ms) + u(5, 1)))


def build():
    frames = [frame(i) for i in range(FRAMES)]
    digits = render_digits()

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(f, W, H) for f in frames]
    for g in digits:
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    bw, bh = DIGIT
    y = 196 - bh // 2
    layout = (anim_group(list(range(1, FRAMES + 1)), FRAME_MS)
              + digit_group(list(range(FRAMES + 1, FRAMES + 11)),
                            int(W / 2) - 26 - 2 * bw, y, 12, bw, bh, f23=5)
              + digit_group(list(range(FRAMES + 1, FRAMES + 11)),
                            int(W / 2) + 26, y, 13, bw, bh, f23=5)
              + u(5, 1))

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(frames[0], *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8 and len(layout) <= 0x800
    return blob, frames, digits


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "pulse.bin"
    blob, frames, digits = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   "
          f"{FRAMES} frames @ {FRAME_MS}ms ({FRAMES * FRAME_MS / 1000:.1f}s loop)")

    bw, bh = DIGIT
    y = 196 - bh // 2
    prev = frames[0].convert("RGBA")
    for i, d in enumerate("10"):
        prev.alpha_composite(digits[int(d)], (W // 2 - 26 - 2 * bw + i * bw, y))
    for i, d in enumerate("09"):
        prev.alpha_composite(digits[int(d)], (W // 2 + 26 + i * bw, y))
    prev.convert("RGB").save("/tmp/pulse_preview.png")
    print("preview -> /tmp/pulse_preview.png")


if __name__ == "__main__":
    main()
