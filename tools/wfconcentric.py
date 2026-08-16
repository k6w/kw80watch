#!/usr/bin/env python3
"""Port the CMF 'Concentric Halo' dial to the KW80.

    ../.venv/bin/python tools/wfconcentric.py concentric.bin

Source is a 466x466 round Watch Pro 2 dial, decompiled by tools/cmfdecompile.py.
Target is 368x448 rectangular, so the concentric rings are scaled to fit the
width and the layout is re-flowed vertically.

Real assets are reused: the ring artwork and the big digit glyphs come straight
out of the original file, so the typography is the original's, not a lookalike.
The glyphs are proportional-width in the source; the KW80's f6 element needs a
fixed box, so each is padded and centred.
"""
import glob
import os
import struct
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import TRAILER, encode_pixels_alpha, digit_group, msg, u  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "..", "artifacts", "concentric")
W, H = 368, 448
THUMB = (180, 219)
DIGIT_IDX = list(range(25, 35))          # the big 0-9 set
RING_IDX = [1, 2, 92]                    # ring / halo layers, drawn back to front
YELLOW = (255, 214, 10)


def load(idx):
    hits = glob.glob(os.path.join(SRC, f"{idx:03d}_*.png"))
    if not hits:
        raise SystemExit(f"missing resource {idx} — run tools/cmfdecompile.py first")
    return Image.open(hits[0]).convert("RGBA")


def build_digits():
    """Pad the proportional source glyphs into one uniform box."""
    glyphs = [load(i) for i in DIGIT_IDX]
    bw = max(g.width for g in glyphs)
    bh = max(g.height for g in glyphs)
    out = []
    for g in glyphs:
        canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        canvas.alpha_composite(g, ((bw - g.width) // 2, (bh - g.height) // 2))
        out.append(canvas)
    return out, (bw, bh)


def build_background(digit_box):
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # Rings: every layer scales by the SAME factor so their relative sizes are
    # preserved — the 312px inner ring must stay inner, not blow up to match
    # the 466px outer one.
    ring_d = 330
    scale = ring_d / 466.0
    cx, cy = W // 2, 178
    for i in RING_IDX:
        try:
            layer = load(i)
        except SystemExit:
            continue
        nw, nh = max(1, round(layer.width * scale)), max(1, round(layer.height * scale))
        layer = layer.resize((nw, nh), Image.LANCZOS)
        bg.alpha_composite(layer, (cx - nw // 2, cy - nh // 2))

    dr = ImageDraw.Draw(bg)
    bw, bh = digit_box

    # colon between hour and minute, matching the original's dot scale
    for dy in (-16, 16):
        dr.ellipse([cx - 5, cy + dy - 5, cx + 5, cy + dy + 5], fill=(255, 255, 255, 255))

    # complication wells, clear of the ring
    for x in (100, 268):
        dr.ellipse([x - 40, 396 - 40, x + 40, 396 + 40],
                   outline=(70, 70, 74, 255), width=3)
    dr.ellipse([268 - 40, 396 - 40, 268 + 40, 396 + 40],
               outline=YELLOW + (255,), width=3)
    return bg.convert("RGB")


def build():
    digits, box = build_digits()
    bg = build_background(box)

    blobs = [lvgl_header(W, H, cf=4) + encode_pixels(bg, W, H)]
    for g in digits:
        blobs.append(lvgl_header(*box, cf=5) + encode_pixels_alpha(g, *box))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    bw, bh = box
    y = 178 - bh // 2
    idx = list(range(2, 12))
    layout = (msg(1, msg(4, u(1, 1) + msg(2, b"")))
              + digit_group(idx, 184 - 22 - 2 * bw, y, 12, bw, bh, f23=5)   # hour
              + digit_group(idx, 184 + 22, y, 13, bw, bh, f23=5)            # minute
              + u(5, 1))

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(bg, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8 and len(layout) <= 0x800
    return blob, box, bg, digits


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "concentric.bin"
    blob, box, bg, digits = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes   glyph box {box[0]}x{box[1]}")

    prev = bg.convert("RGBA")
    bw, bh = box
    y = 178 - bh // 2
    for i, d in enumerate("10"):
        prev.alpha_composite(digits[int(d)], (184 - 22 - 2 * bw + i * bw, y))
    for i, d in enumerate("09"):
        prev.alpha_composite(digits[int(d)], (184 + 22 + i * bw, y))
    prev.convert("RGB").save("/tmp/concentric_preview.png")
    print("preview -> /tmp/concentric_preview.png")


if __name__ == "__main__":
    main()
