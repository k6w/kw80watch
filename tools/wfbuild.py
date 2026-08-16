#!/usr/bin/env python3
"""Build an OLWF-format watchface with a custom bitmap font.

    ../.venv/bin/python tools/wfbuild.py out.bin

Container (see docs/07-binary-format.md), cloned from the structure of the
vendor's own WF01:

    0x00  header: off1, off2, cnt, off3, len3      (5 x u32 LE)
    off1  thumbnail   : lv_img_header_t + pixels
    off2  image table : cnt/4 x u32 offsets (relative to off2), then the images
    off3  protobuf layout
          8-byte trailer, last 4 bytes "OLWF"

Layout elements, matching WF01:

    f4{f1=<idx>}                                    background
    f6{f1=<10 indices>, f3={x,y}, f5=<type>,        digit group
       f21=w, f22=h, f23=25}
      f5: 12 = hour, 13 = minute, 17 = date

**Image indices in the layout are 1-based** (table index + 1).

Images are written as cf=4 (LV_IMG_CF_TRUE_COLOR, raw RGB565) rather than the
vendor's compressed cf=24/25, because the compressor is not decoded. Whether the
loader accepts cf=4 in an OLWF container is exactly what this tests.
"""
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header, DITHER_R, DITHER_G, DITHER_B  # noqa: E402


def encode_pixels_alpha(img, w, h):
    """cf=5 LV_IMG_CF_TRUE_COLOR_ALPHA: RGB565 big-endian + 1 alpha byte."""
    img = img.convert("RGBA").resize((w, h), Image.LANCZOS)
    px = img.load()
    out = bytearray(w * h * 3)
    for x in range(w):
        for y in range(h):
            r, g, b, a = px[x, y]
            d = ((y & 7) << 3) + (x & 7)
            v = ((min(b + DITHER_B[d], 255) >> 3)
                 | ((min(r + DITHER_R[d], 255) >> 3) << 11)
                 | ((min(g + DITHER_G[d], 255) >> 2) << 5))
            o = ((y * w) + x) * 3
            out[o] = (v >> 8) & 0xFF
            out[o + 1] = v & 0xFF
            out[o + 2] = a
    return bytes(out)

SCREEN = (368, 448)
THUMB = (180, 219)
DIGIT = (54, 76)          # same as WF01's hour/minute glyphs
TRAILER = bytes.fromhex("554350444f4c5746")   # "UCPDOLWF" — firmware checks last 4


# ---------- protobuf ----------

def varint(v):
    # A negative int would spin forever here: >>= converges to -1, never 0.
    # Every field in this format is unsigned, so reject it loudly instead.
    if v < 0:
        raise ValueError(f"varint got a negative value: {v}")
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def tag(field, wire):
    return varint((field << 3) | wire)


def msg(field, payload):
    return tag(field, 2) + varint(len(payload)) + payload


def u(field, value):
    return tag(field, 0) + varint(value)


def background(idx):
    return msg(1, msg(4, u(1, idx) + msg(2, b"")))


def digit_group(indices, x, y, kind, w, h, f23=25):
    inner = (msg(1, bytes(indices))
             + msg(3, u(1, x) + u(2, y))
             + u(5, kind) + u(21, w) + u(22, h) + u(23, f23))
    return msg(1, msg(6, inner))


# ---------- art ----------

def make_font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNS.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_digits(w, h, alpha=False):
    """Ten digit glyphs, our own typography."""
    font = make_font(int(h * 0.86))
    out = []
    for d in "0123456789":
        img = Image.new("RGBA" if alpha else "RGB", (w, h),
                        (0, 0, 0, 0) if alpha else (0, 0, 0))
        dr = ImageDraw.Draw(img)
        box = dr.textbbox((0, 0), d, font=font)
        dr.text(((w - (box[2] - box[0])) / 2 - box[0],
                 (h - (box[3] - box[1])) / 2 - box[1]),
                d, font=font, fill=(0, 240, 200, 255) if alpha else (0, 240, 200))
        out.append(img)
    return out


def render_background():
    img = Image.new("RGB", SCREEN, (0, 0, 0))
    dr = ImageDraw.Draw(img)
    for y in range(SCREEN[1]):                       # vertical gradient
        t = y / SCREEN[1]
        dr.line([(0, y), (SCREEN[0], y)],
                fill=(int(6 + 26 * t), int(8 + 14 * t), int(28 + 44 * t)))
    dr.rounded_rectangle([70, 80, 300, 280], radius=26, outline=(0, 240, 200), width=2)
    dr.line([(96, 182), (272, 182)], fill=(0, 120, 110), width=1)
    return img


# ---------- container ----------

def build():
    """A real watchface: custom bitmap font, hour and minute.

    Established by experiment on the device:
      * glyphs MUST be cf=5 (LV_IMG_CF_TRUE_COLOR_ALPHA) with a true alpha
        channel — cf=4 opaque glyphs are silently skipped
      * the layout's f23 must match, i.e. 5
      * background is fine as cf=4 (proven rendering)
    """
    bg = render_background()
    alpha = render_digits(*DIGIT, alpha=True)

    blobs = [lvgl_header(*SCREEN, cf=4) + encode_pixels(bg, *SCREEN)]
    for g in alpha:                                     # table 1-10 -> refs 2-11
        blobs.append(lvgl_header(*DIGIT, cf=5) + encode_pixels_alpha(g, *DIGIT))

    cnt = len(blobs) * 4
    table = bytearray()
    body = bytearray()
    cursor = cnt                                     # images start after the table
    for blob in blobs:
        table += struct.pack("<I", cursor)
        body += blob
        cursor += len(blob)
    section2 = bytes(table) + bytes(body)

    idx = list(range(2, 12))
    layout = (background(1)
              + digit_group(idx, 88, 96, 12, *DIGIT, f23=5)    # hour
              + digit_group(idx, 88, 186, 13, *DIGIT, f23=5)   # minute
              + u(5, 1))

    thumb = lvgl_header(*THUMB) + encode_pixels(bg, *THUMB)

    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    header = struct.pack("<5I", off1, off2, cnt, off3, len(layout))
    blob = header + thumb + section2 + layout + TRAILER

    assert len(blob) == off3 + len(layout) + 8
    assert cnt <= 0x3F8 and len(layout) <= 0x800, "firmware limits exceeded"
    return blob, len(blobs), off1, off2, cnt, off3, len(layout)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "custom_font_face.bin"
    blob, nimg, off1, off2, cnt, off3, len3 = build()
    with open(out, "wb") as fh:
        fh.write(blob)
    print(f"wrote {out}  {len(blob):,} bytes")
    print(f"  images   : {nimg}  (1 bg cf=4 + 10 glyphs cf=5 alpha)")
    print(f"  header   : off1={off1} off2={off2} cnt={cnt} off3={off3} len3={len3}")
    print(f"  limits   : cnt<=1016 {cnt <= 0x3F8}   len3<=2048 {len3 <= 0x800}")
    print(f"  invariant: off3+len3+8 == size  {off3 + len3 + 8 == len(blob)}")
    print(f"  trailer  : {blob[-8:].hex(' ')}  last4={blob[-4:].decode()}")


if __name__ == "__main__":
    main()
