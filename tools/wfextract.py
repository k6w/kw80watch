#!/usr/bin/env python3
"""Extract every decodable image out of a corpus of OLWF watchfaces.

    ../.venv/bin/python tools/wfextract.py artifacts/fam2/bins artifacts/vendor-art

The vendor's own store files are mostly cf=24/25 — their compressed formats,
still undecoded. But a minority are plain cf=4 (RGB565) and cf=5 (RGB565+A),
which the firmware's stock LVGL decoder handles and which we can therefore read
directly. Those are usable source artwork: analogue hands, sub-dial needles,
indicator glyphs.

Byte order is the KW80's: RGB565 **big-endian**, matching ImageUtil in the app
and tools/wfimage.py.
"""
import json
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from wfcensus import load, tree  # noqa: E402

DECODABLE = {4, 5}


def decode(cf, w, h, data):
    if cf == 4:
        need = w * h * 2
        if len(data) < need:
            return None
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                o = (y * w + x) * 2
                v = (data[o] << 8) | data[o + 1]          # big-endian
                px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2,
                            (v & 31) << 3)
        return img
    if cf == 5:
        need = w * h * 3
        if len(data) < need:
            return None
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                o = (y * w + x) * 3
                v = (data[o] << 8) | data[o + 1]          # big-endian
                px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2,
                            (v & 31) << 3, data[o + 2])
        return img
    return None


def roles(path):
    """Map image index -> the element role that references it."""
    face = load(path)
    out = {}
    ROLE = {8: "hand", 23: "vector", 20: "anim", 4: "image", 5: "set", 6: "digits"}
    for f, k, v, _ in tree(face["layout"]):
        if f != 1 or k != "msg":
            continue
        for vf, vk, vv, _ in v:
            if vk != "msg":
                continue
            name = ROLE.get(vf, f"f{vf}")
            src = None
            refs = []
            for sf, sk, sv, _ in vv:
                if sf == 1 and sk == "bytes":
                    refs = list(sv)
                elif sf == 1 and sk == "int":
                    refs = [sv]
                elif sf in (5, 6) and sk == "int" and vf in (5, 6, 8, 23):
                    src = sv
            for r in refs:
                out.setdefault(r, f"{name}" + (f"-src{src}" if src is not None else ""))
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "artifacts/fam2/bins"
    out = sys.argv[2] if len(sys.argv) > 2 else "artifacts/vendor-art"
    os.makedirs(out, exist_ok=True)
    manifest, n = [], 0

    for fn in sorted(os.listdir(src)):
        if not fn.endswith(".bin"):
            continue
        path = os.path.join(src, fn)
        face = load(path)
        if not any(im["cf"] in DECODABLE for im in face["images"]):
            continue
        blob = open(path, "rb").read()
        role = roles(path)
        table = sorted(im["off"] for im in face["images"])
        for im in face["images"]:
            if im["cf"] not in DECODABLE:
                continue
            nxt = next((o for o in table if o > im["off"]), len(blob))
            data = blob[im["off"] + 4:nxt]
            img = decode(im["cf"], im["w"], im["h"], data)
            if img is None:
                continue
            r = role.get(im["i"] + 1, "unref")
            name = f"{fn[:-4]}__{im['i']+1:03d}_{r}_cf{im['cf']}_{im['w']}x{im['h']}.png"
            img.save(os.path.join(out, name))
            manifest.append({"file": fn, "index": im["i"] + 1, "role": r,
                             "cf": im["cf"], "w": im["w"], "h": im["h"],
                             "png": name})
            n += 1
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"extracted {n} images -> {out}/")
    import collections
    print(dict(collections.Counter(m["role"] for m in manifest)))


if __name__ == "__main__":
    main()
