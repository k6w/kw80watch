#!/usr/bin/env python3
"""Extract LVGL images embedded in a firmware image and save them as PNGs.

    ../.venv/bin/python tools/fwimages.py artifacts/firmware/SWC01__*.bin out_dir

Uses the same lv_img_header_t layout recovered for watchfaces:

    cf:5  always_zero:3  reserved:2  w:11  h:11     (little-endian u32)

Only `cf = 4` (LV_IMG_CF_TRUE_COLOR, raw RGB565 big-endian) is decoded — that is
what the firmware's own UI assets use and what the stock LVGL decoder handles.
Compressed vendor formats (cf 24/25) are counted but skipped.

A naive header scan yields ~1 false positive per 50 words, so candidates must
also pass: the pixel block fits in the file, dimensions are UI-plausible, and
the decoded image is not near-uniform noise.
"""
import os
import struct
import sys
from collections import Counter

from PIL import Image


def parse_header(v):
    return (v & 0x1F, (v >> 5) & 7, (v >> 8) & 3, (v >> 10) & 0x7FF, (v >> 21) & 0x7FF)


def looks_like_image(px, w, h):
    """Reject noise: real UI art repeats colours heavily."""
    sample = px[::max(1, len(px) // 4000)]
    c = Counter(sample)
    if not c:
        return False
    top = c.most_common(1)[0][1] / len(sample)
    return top > 0.02 and len(c) < len(sample) * 0.9


def decode_rgb565_be(data, w, h):
    img = Image.new("RGB", (w, h))
    out = img.load()
    for y in range(h):
        row = (y * w) * 2
        for x in range(w):
            o = row + x * 2
            v = (data[o] << 8) | data[o + 1]
            out[x, y] = (((v >> 11) & 0x1F) << 3,
                         ((v >> 5) & 0x3F) << 2,
                         (v & 0x1F) << 3)
    return img


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    b = open(path, "rb").read()

    found, skipped_cf = 0, Counter()
    seen_spans = []
    for off in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, off)[0]
        cf, az, rsv, w, h = parse_header(v)
        if az or rsv or not (4 <= cf <= 27):
            continue
        if not (16 <= w <= 368 and 16 <= h <= 448):
            continue
        if cf != 4:
            skipped_cf[cf] += 1
            continue
        need = w * h * 2
        if off + 4 + need > len(b):
            continue
        px = b[off + 4: off + 4 + need]
        if not looks_like_image(px, w, h):
            continue
        if any(s <= off < e for s, e in seen_spans):
            continue
        try:
            img = decode_rgb565_be(px, w, h)
        except Exception:
            continue
        name = f"{off:08x}_{w}x{h}.png"
        img.save(os.path.join(outdir, name))
        seen_spans.append((off, off + 4 + need))
        found += 1
        print(f"  0x{off:08x}  {w}x{h}  -> {name}")
        if found >= 400:
            print("  (stopping at 400)")
            break

    print(f"\nextracted {found} images -> {outdir}")
    if skipped_cf:
        print(f"skipped compressed (cf: count): {dict(skipped_cf)}")


if __name__ == "__main__":
    main()
