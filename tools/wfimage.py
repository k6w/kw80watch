#!/usr/bin/env python3
"""Encode an image into the KW80 custom-watchface format.

    ../.venv/bin/python tools/wfimage.py input.png out.bin

Port of com.huawo.sdk.bluetoothsdk.interfaces.utils.ImageUtil, specifically
`rgb888ToRGB555Ex` (misnamed — it emits RGB565) and `getHead`.

Layout produced (matches ImageUtil lines 115-122):

    [4-byte LVGL header, main ][ main pixels  ]
    [4-byte LVGL header, thumb][ thumb pixels ]
    [3-byte crc/id + "UFACE"]                    <- 8-byte trailer

LVGL header:  (w << 10) | (h << 21) | 4     little-endian u32
              cf = 4 = LV_IMG_CF_TRUE_COLOR

Pixels: RGB565, **big-endian**, 2 bytes each, ordered-dithered per channel
with the 8x8 matrices lifted verbatim from the app.
"""
import struct
import sys

from PIL import Image

SCREEN_W, SCREEN_H = 368, 448
THUMB_W, THUMB_H = 180, 219

# 8x8 ordered-dither matrices, verbatim from ImageUtil.rgb888ToRGB555Ex
DITHER_R = [1, 7, 3, 5, 0, 8, 2, 6, 7, 1, 5, 3, 8, 0, 6, 2,
            3, 5, 0, 8, 2, 6, 1, 7, 5, 3, 8, 0, 6, 2, 7, 1,
            0, 8, 2, 6, 1, 7, 3, 5, 8, 0, 6, 2, 7, 1, 5, 3,
            2, 6, 1, 7, 3, 5, 0, 8, 6, 2, 7, 1, 5, 3, 8, 0]
DITHER_G = [1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
            3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4,
            1, 3, 2, 2, 3, 1, 2, 2, 2, 2, 0, 4, 2, 2, 4, 0,
            3, 1, 2, 2, 1, 3, 2, 2, 2, 2, 4, 0, 2, 2, 0, 4]
DITHER_B = [5, 3, 8, 0, 6, 2, 7, 1, 3, 5, 0, 8, 2, 6, 1, 7,
            8, 0, 6, 2, 7, 1, 5, 3, 0, 8, 2, 6, 1, 7, 3, 5,
            6, 2, 7, 1, 5, 3, 8, 0, 2, 6, 1, 7, 3, 5, 0, 8,
            7, 1, 5, 3, 8, 0, 6, 2, 1, 7, 3, 5, 0, 8, 2, 6]


def lvgl_header(w, h, cf=4):  # cf overridable for format probes
    return struct.pack("<I", ((w << 10) | (h << 21)) + cf)


def encode_pixels(img, w, h):
    """RGB565 big-endian with ordered dithering. Mirrors the app's inner loop."""
    img = img.convert("RGB").resize((w, h), Image.LANCZOS)
    px = img.load()
    out = bytearray(w * h * 2)
    for x in range(w):
        for y in range(h):
            r, g, b = px[x, y]
            d = ((y & 7) << 3) + (x & 7)
            v = ((min(b + DITHER_B[d], 255) >> 3)
                 | ((min(r + DITHER_R[d], 255) >> 3) << 11)
                 | ((min(g + DITHER_G[d], 255) >> 2) << 5))
            o = ((y * w) + x) * 2
            out[o] = (v >> 8) & 0xFF          # big-endian
            out[o + 1] = v & 0xFF
    return bytes(out)


def huawo_crc(data):
    """Port of BytesUtils.crc16 / crc32 — they are the SAME algorithm.

    Not standard CCITT. `crc32` returns this identical 16-bit value zero-padded
    to 4 bytes, because the accumulator is masked to 0xFFFF on every step.
    """
    i = 0xFFFF
    for b in data:
        b &= 0xFF
        i2 = (((i << 8) | ((i >> 8) & 0xFF)) & 0xFFFF) ^ b
        i3 = i2 ^ (((i2 & 0xFF) >> 4) & 0xFFFF)
        i4 = i3 ^ ((i3 << 12) & 0xFFFF)
        i = i4 ^ (((i4 & 0xFF) << 5) & 0xFFFF)
    return i


def crc16(data):
    return huawo_crc(data)


def crc32_bytes(data):
    v = huawo_crc(data)
    return bytes([v & 0xFF, (v >> 8) & 0xFF, 0, 0])


def build(path, wf_id=0):
    img = Image.open(path)
    main = encode_pixels(img, SCREEN_W, SCREEN_H)
    thumb = encode_pixels(img, THUMB_W, THUMB_H)

    blob = (lvgl_header(SCREEN_W, SCREEN_H) + main
            + lvgl_header(THUMB_W, THUMB_H) + thumb)

    c = crc16(main)
    trailer = bytes([c & 0xFF, (c >> 8) & 0xFF, wf_id & 0xFF]) + b"UFACE"
    return blob + trailer


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = build(sys.argv[1])
    with open(sys.argv[2], "wb") as fh:
        fh.write(out)

    hdr = struct.unpack("<I", out[:4])[0]
    print(f"wrote {sys.argv[2]}  {len(out):,} bytes")
    print(f"  main  header 0x{hdr:08x} -> cf={hdr & 0x1f} "
          f"w={(hdr >> 10) & 0x7ff} h={(hdr >> 21) & 0x7ff}")
    off = 4 + SCREEN_W * SCREEN_H * 2
    h2 = struct.unpack("<I", out[off:off + 4])[0]
    print(f"  thumb header 0x{h2:08x} -> cf={h2 & 0x1f} "
          f"w={(h2 >> 10) & 0x7ff} h={(h2 >> 21) & 0x7ff}")
    print(f"  trailer {out[-8:].hex(' ')}  = ...{out[-5:].decode()}")
    expect = 4 + SCREEN_W * SCREEN_H * 2 + 4 + THUMB_W * THUMB_H * 2 + 8
    print(f"  size check: {len(out):,} == {expect:,}  {len(out) == expect}")


if __name__ == "__main__":
    main()
