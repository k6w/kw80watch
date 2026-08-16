#!/usr/bin/env python3
"""Build an animated low-poly cat watchface for the KW80.

    ../.venv/bin/python tools/wfcat.py cat.bin

Animation uses the `f20` element discovered in the vendor's own faces:

    f1{ f20{ f1=<frame indices>, f2={}, f3=<ms per frame>, f5=1 } }

The cat is genuine low-poly geometry — a triangle mesh, flat-shaded per face.
Frames animate the *light direction* sweeping across the mesh, which is the
characteristic low-poly shimmer, plus a slow pulse in the eyes.

Formats are the ones proven on the device:
    background / frames : cf=4  (raw RGB565)
    glyphs              : cf=5  (RGB565 + alpha)  <- must have real alpha
"""
import math
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import (DIGIT, SCREEN, THUMB, TRAILER, encode_pixels_alpha,  # noqa: E402
                     digit_group, make_font, msg, u)

FRAMES = 4
FRAME_MS = 250

# ---------------------------------------------------------------- geometry
# Low-poly cat head. Vertices in a 0..1 space, mapped onto the upper screen.
V = {
    "ear_l_tip": (0.16, 0.02), "ear_l_in": (0.32, 0.20), "ear_l_out": (0.10, 0.26),
    "ear_r_tip": (0.84, 0.02), "ear_r_in": (0.68, 0.20), "ear_r_out": (0.90, 0.26),
    "brow_l": (0.24, 0.28), "brow_r": (0.76, 0.28),
    "cheek_l": (0.09, 0.52), "cheek_r": (0.91, 0.52),
    "jaw_l": (0.26, 0.80), "jaw_r": (0.74, 0.80),
    "chin": (0.50, 0.92),
    "eye_l": (0.34, 0.44), "eye_r": (0.66, 0.44),
    "nose": (0.50, 0.60), "mouth": (0.50, 0.72),
    "fore": (0.50, 0.26), "mid": (0.50, 0.46),
    "muzz_l": (0.38, 0.70), "muzz_r": (0.62, 0.70),
}

# (v1, v2, v3, base colour) — ginger cat palette
TRIS = [
    ("ear_l_tip", "ear_l_in", "ear_l_out", (232, 128, 58)),
    ("ear_l_in", "ear_l_out", "brow_l", (206, 104, 44)),
    ("ear_l_in", "brow_l", "fore", (243, 152, 74)),
    ("ear_r_tip", "ear_r_in", "ear_r_out", (232, 128, 58)),
    ("ear_r_in", "ear_r_out", "brow_r", (206, 104, 44)),
    ("ear_r_in", "brow_r", "fore", (243, 152, 74)),
    ("brow_l", "fore", "mid", (250, 168, 88)),
    ("brow_r", "fore", "mid", (240, 156, 78)),
    ("brow_l", "mid", "eye_l", (236, 146, 70)),
    ("brow_r", "mid", "eye_r", (226, 136, 62)),
    ("brow_l", "eye_l", "cheek_l", (214, 118, 52)),
    ("brow_r", "eye_r", "cheek_r", (206, 110, 46)),
    ("eye_l", "cheek_l", "jaw_l", (228, 140, 66)),
    ("eye_r", "cheek_r", "jaw_r", (218, 130, 58)),
    ("eye_l", "mid", "nose", (246, 162, 84)),
    ("eye_r", "mid", "nose", (238, 152, 76)),
    ("eye_l", "nose", "muzz_l", (252, 186, 122)),
    ("eye_r", "nose", "muzz_r", (246, 178, 114)),
    ("eye_l", "muzz_l", "jaw_l", (232, 146, 74)),
    ("eye_r", "muzz_r", "jaw_r", (224, 138, 66)),
    ("nose", "muzz_l", "mouth", (255, 206, 152)),
    ("nose", "muzz_r", "mouth", (250, 198, 144)),
    ("muzz_l", "mouth", "chin", (238, 172, 110)),
    ("muzz_r", "mouth", "chin", (232, 164, 102)),
    ("muzz_l", "jaw_l", "chin", (220, 140, 72)),
    ("muzz_r", "jaw_r", "chin", (214, 132, 64)),
]

BOX = (44, 34, 324, 300)      # where the cat sits on screen


def pt(name):
    x, y = V[name]
    return (BOX[0] + x * (BOX[2] - BOX[0]), BOX[1] + y * (BOX[3] - BOX[1]))


def shade(colour, tri, light):
    """Flat-shade a face by its centroid against a moving light direction."""
    cx = sum(V[v][0] for v in tri) / 3
    cy = sum(V[v][1] for v in tri) / 3
    nx, ny = cx - 0.5, cy - 0.5
    n = math.hypot(nx, ny) or 1e-6
    d = (nx / n) * light[0] + (ny / n) * light[1]
    k = 0.74 + 0.34 * max(0.0, d)
    return tuple(min(255, int(c * k)) for c in colour)


def frame(i):
    img = Image.new("RGB", SCREEN, (10, 10, 16))
    dr = ImageDraw.Draw(img)

    for y in range(SCREEN[1]):                       # backdrop
        t = y / SCREEN[1]
        dr.line([(0, y), (SCREEN[0], y)],
                fill=(int(12 + 16 * t), int(10 + 10 * t), int(22 + 26 * t)))

    a = 2 * math.pi * i / FRAMES                     # light sweeps a full circle
    light = (math.cos(a), math.sin(a))

    for v1, v2, v3, col in TRIS:
        dr.polygon([pt(v1), pt(v2), pt(v3)], fill=shade(col, (v1, v2, v3), light))

    pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(a))  # eyes breathe
    for e, inner in (("eye_l", -6), ("eye_r", 6)):
        ex, ey = pt(e)
        dr.polygon([(ex - 17, ey), (ex, ey - 11), (ex + 17, ey), (ex, ey + 11)],
                   fill=(24, 30, 26))
        g = int(120 + 135 * pulse)
        dr.polygon([(ex - 7 + inner * 0.3, ey), (ex + inner * 0.3, ey - 8),
                    (ex + 7 + inner * 0.3, ey), (ex + inner * 0.3, ey + 8)],
                   fill=(int(60 * pulse), g, int(90 * pulse)))

    nx, ny = pt("nose")                              # nose + whiskers
    dr.polygon([(nx - 11, ny - 6), (nx + 11, ny - 6), (nx, ny + 8)], fill=(196, 96, 104))
    for s in (-1, 1):
        for k, dy in enumerate((-8, 0, 8)):
            dr.line([(nx + s * 20, ny + dy * 0.5),
                     (nx + s * 96, ny + dy * 2.0 - 6 + k)],
                    fill=(238, 214, 200), width=1)
    return img


def render_digits(w, h):
    font = make_font(int(h * 0.88))
    out = []
    for d in "0123456789":
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        box = dr.textbbox((0, 0), d, font=font)
        dr.text(((w - (box[2] - box[0])) / 2 - box[0],
                 (h - (box[3] - box[1])) / 2 - box[1]),
                d, font=font, fill=(255, 232, 210, 255))
        out.append(img)
    return out


def anim_group(indices, ms):
    return msg(1, msg(20, msg(1, bytes(indices)) + msg(2, b"")
                      + u(3, ms) + u(5, 1)))


def build():
    frames = [frame(i) for i in range(FRAMES)]
    digits = render_digits(*DIGIT)

    blobs = [lvgl_header(*SCREEN, cf=4) + encode_pixels(f, *SCREEN) for f in frames]
    for g in digits:
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))

    cnt = len(blobs) * 4
    table, body, cursor = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cursor)
        body += b
        cursor += len(b)
    section2 = bytes(table) + bytes(body)

    frame_idx = list(range(1, FRAMES + 1))                 # 1-based
    digit_idx = list(range(FRAMES + 1, FRAMES + 11))
    layout = (anim_group(frame_idx, FRAME_MS)
              + digit_group(digit_idx, 66, 322, 12, *DIGIT, f23=5)    # hour
              + digit_group(digit_idx, 194, 322, 13, *DIGIT, f23=5)   # minute
              + u(5, 1))

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(frames[0], *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    blob = (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)
    assert cnt <= 0x3F8 and len(layout) <= 0x800
    assert len(blob) == off3 + len(layout) + 8
    return blob, len(blobs), cnt, off3, len(layout)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "cat.bin"
    blob, nimg, cnt, off3, len3 = build()
    open(out, "wb").write(blob)
    print(f"wrote {out}  {len(blob):,} bytes")
    print(f"  {FRAMES} animation frames @ {FRAME_MS}ms  "
          f"({FRAMES * FRAME_MS / 1000:.1f}s loop) + 10 glyphs")
    print(f"  images={nimg} cnt={cnt} off3={off3} len3={len3}")
    print(f"  limits ok: cnt<=1016 {cnt <= 0x3F8}  len3<=2048 {len3 <= 0x800}")


if __name__ == "__main__":
    main()
