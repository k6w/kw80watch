#!/usr/bin/env python3
"""Decompile a CMF Watch Pro / Pro 2 dial .bin into its layout tree and images.

    ../.venv/bin/python tools/cmfdecompile.py face.bin outdir

Format per the CMF BLE/dial spec section 9.6a:

    0x00  u32 LE  rawCRC32(header[0x04:0x24] + tree)   (init=0, no final inversion)
    0x04  u32 LE  format version: 1 = Pro 2, 0x02000001 = Pro 1
    0x08          dial name, NUL-terminated ASCII
    0x18  u32 LE  fileLength - 36
    0x1c  u32 LE  resource section length
    0x20  u32 LE  rawCRC32(resource section)
    0x24          TLV tree      (fileLen - 72 - resLen bytes)
    ...           resource section
    last 36 bytes == first 36 bytes

TLV node: tag(u8) len(u16 LE) value.  Root 0x20; screens 0x21 main / 0x22 AOD.
Resource block: lvglHdr(u32 LE) dataSize(u32 LE) data   — chained, no gaps.
lvglHdr is LVGL v8 lv_img_header_t: cf:5 | always_zero:3 | reserved:2 | w:11 | h:11
"""
import json
import os
import struct
import sys
import zlib

import lz4.block
from PIL import Image

CONTAINERS = {0x20, 0x21, 0x22, 0x28, 0x30, 0x60, 0x68, 0x70, 0x80, 0x81, 0x82, 0x85}
CF_NAMES = {1: "JPEG", 4: "RGB565", 5: "RGB565A8", 13: "ALPHA4", 24: "BGRA8888"}


def raw_crc32(data):
    return (~zlib.crc32(data, 0xFFFFFFFF)) & 0xFFFFFFFF


def parse_tlv(buf, depth=0):
    out, i = [], 0
    while i + 3 <= len(buf):
        tag = buf[i]
        ln = struct.unpack_from("<H", buf, i + 1)[0]
        val = buf[i + 3:i + 3 + ln]
        if len(val) < ln:
            break
        node = {"tag": f"0x{tag:02x}", "len": ln}
        if tag in CONTAINERS and ln >= 3:
            kids = parse_tlv(val, depth + 1)
            if kids:
                node["children"] = kids
            else:
                node["hex"] = val.hex()
        else:
            node["hex"] = val.hex()
            if tag == 0x86:
                node["name"] = val.split(b"\0")[0].decode("ascii", "replace")
        out.append(node)
        i += 3 + ln
    return out


def decode_image(cf, w, h, raw):
    """Return a PIL image, or None if the colour format isn't handled."""
    if cf == 1:
        import io
        return Image.open(io.BytesIO(raw)).convert("RGB")

    need = {4: w * h * 2, 5: w * h * 3, 13: (w * h + 1) // 2, 24: w * h * 4}.get(cf)
    if need is None:
        return None
    data = raw if len(raw) == need else lz4.block.decompress(raw, uncompressed_size=need)

    if cf == 4:
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                v = struct.unpack_from("<H", data, (y * w + x) * 2)[0]
                px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3)
        return img
    if cf == 5:
        # LVGL TRUE_COLOR_ALPHA is INTERLEAVED: [rgb565 lo, hi, alpha] per pixel
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                o = (y * w + x) * 3
                v = data[o] | (data[o + 1] << 8)
                px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2,
                            (v & 31) << 3, data[o + 2])
        return img
    if cf == 13:
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                i = y * w + x
                a = data[i // 2]
                a = (a & 0x0F) if i % 2 == 0 else (a >> 4)
                px[x, y] = (255, 255, 255, a * 17)
        return img
    if cf == 24:
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                o = (y * w + x) * 4
                px[x, y] = (data[o + 2], data[o + 1], data[o], data[o + 3])
        return img
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    b = open(path, "rb").read()
    N = len(b)

    crc_hdr, ver = struct.unpack_from("<II", b, 0)
    name = b[8:b.index(b"\0", 8)].decode()
    foot_off, res_len, res_crc = struct.unpack_from("<III", b, 0x18)
    tree_len = N - 72 - res_len
    tree = b[0x24:0x24 + tree_len]
    res_off = 0x24 + tree_len
    res = b[res_off:res_off + res_len]

    print(f"name       : {name}")
    print(f"version    : 0x{ver:08x}  ({'Pro 2' if ver == 1 else 'Pro 1'})")
    print(f"tree       : {tree_len:,} bytes @ 0x{0x24:x}")
    print(f"resources  : {res_len:,} bytes @ 0x{res_off:x}")
    print(f"header CRC : {'PASS' if raw_crc32(b[4:0x24] + tree) == crc_hdr else 'FAIL'}")
    print(f"res CRC    : {'PASS' if raw_crc32(res) == res_crc else 'FAIL'}")

    nodes = parse_tlv(tree)
    json.dump({"name": name, "version": ver, "tree": nodes},
              open(os.path.join(outdir, "tree.json"), "w"), indent=1)

    print("\n=== resources ===")
    i, n = 0, 0
    manifest = []
    while i + 8 <= len(res):
        hdr, size = struct.unpack_from("<II", res, i)
        cf = hdr & 0x1F
        az = (hdr >> 5) & 7
        w = (hdr >> 10) & 0x7FF
        hh = (hdr >> 21) & 0x7FF
        if az != 0 or not (0 < w <= 2047 and 0 < hh <= 2047) or size == 0:
            break
        raw = res[i + 8:i + 8 + size]
        try:
            img = decode_image(cf, w, hh, raw)
        except Exception as e:
            img = None
            print(f"  [{n:3d}] cf={cf:<2} {w}x{hh} — decode failed: {e}")
        if img is not None:
            fn = f"{n:03d}_cf{cf}_{w}x{hh}.png"
            img.save(os.path.join(outdir, fn))
            manifest.append({"index": n, "cf": cf, "fmt": CF_NAMES.get(cf, "?"),
                             "w": w, "h": hh, "offset": res_off + i,
                             "stored": size, "file": fn})
            print(f"  [{n:3d}] cf={cf:<2} {CF_NAMES.get(cf,'?'):<9} {w:>4}x{hh:<4} "
                  f"stored {size:>7,}  -> {fn}")
        i += 8 + size
        n += 1
    json.dump(manifest, open(os.path.join(outdir, "resources.json"), "w"), indent=1)
    print(f"\n{n} resources -> {outdir}/")


if __name__ == "__main__":
    main()
