#!/usr/bin/env python3
"""Overlay decoded layout elements onto the vendor's own rendered preview.

    ../.venv/bin/python tools/wfoverlay.py WF46 WF44 WF12 …
    ../.venv/bin/python tools/wfoverlay.py --all

This is the decisive way to learn what each data-source code means: the
preview PNG shows what the watch actually draws, and the layout says where
each element sits and which code drives it. Line them up and the code reads
itself.

Output: /tmp/wfoverlay/<name>.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from wfcensus import load, tree  # noqa: E402

SRC = "artifacts/samples"
THUMBS = "artifacts/thumbs"
OUT = "/tmp/wfoverlay"
SCREEN = (368, 448)


def screen_of(face):
    """Screen size = the largest image in the table; models differ."""
    big = max(face["images"], key=lambda i: i["w"] * i["h"])
    return (big["w"], big["h"])

COLOURS = {8: (160, 160, 255), 4: (0, 200, 255), 5: (255, 90, 0), 6: (60, 255, 90),
           20: (255, 0, 220), 23: (255, 230, 0)}


def elements(face):
    out = []
    for f, k, v, _ in tree(face["layout"]):
        if f != 1 or k != "msg":
            continue
        for vf, vk, vv, _ in v:
            rec = {"variant": vf, "poly": [], "circ": []}
            if vk != "msg":
                out.append(rec)
                continue
            for sf, sk, sv, _ in vv:
                if vf == 23 and sf == 2 and sk == "msg":
                    d = {a: b for a, _, b, _ in sv}
                    rec["poly"].append((d.get(1, 0), d.get(2, 0)))
                elif vf == 23 and sf == 3 and sk == "msg":
                    d = {}
                    for a, ak, b, _ in sv:
                        if ak == "msg":
                            d["c"] = {x: y for x, _, y, _ in b}
                        else:
                            d[a] = b
                    rec["circ"].append(d)
                elif sk == "msg":
                    rec[f"f{sf}"] = {a: b for a, _, b, _ in sv}
                elif sk == "bytes":
                    rec[f"f{sf}"] = list(sv)
                else:
                    rec[f"f{sf}"] = sv
            out.append(rec)
    return out


def pos(e, key):
    """Position submessage, or an empty dict when the field is absent/empty."""
    v = e.get(key)
    return v if isinstance(v, dict) else {}


def render(name, src=None, thumbs=None):
    global SCREEN
    src, thumbs = src or SRC, thumbs or THUMBS
    face = load(os.path.join(src, name + ".bin"))
    dims = {im["i"] + 1: (im["w"], im["h"]) for im in face["images"]}
    SCREEN = screen_of(face)
    thumb = Image.open(os.path.join(thumbs, name + ".png")).convert("RGB")
    img = thumb.resize(SCREEN, Image.LANCZOS)
    canvas = Image.new("RGB", (SCREEN[0] * 2 + 30, SCREEN[1]), (18, 18, 20))
    canvas.paste(thumb.resize(SCREEN, Image.LANCZOS), (0, 0))
    canvas.paste(img, (SCREEN[0] + 30, 0))
    dr = ImageDraw.Draw(canvas)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    except Exception:
        f = ImageFont.load_default()
    ox = SCREEN[0] + 30

    for e in elements(face):
        v = e["variant"]
        col = COLOURS.get(v, (200, 200, 200))
        if v == 6:                                   # digit group
            p = pos(e, "f3")
            x, y = p.get(1, 0), p.get(2, 0)
            w, h = e.get("f21", 10), e.get("f22", 10)
            n = len(e.get("f1", []))
            dr.rectangle([ox + x, y, ox + x + w, y + h], outline=col, width=2)
            dr.text((ox + x, y - 16), f"f6 src={e.get('f5')} n={n} {w}x{h}",
                    fill=col, font=f)
        elif v == 5:                                 # indexed picture set
            p = pos(e, "f2")
            x, y = p.get(1, 0), p.get(2, 0)
            idx = e.get("f1", [])
            w, h = dims.get(idx[0], (20, 20)) if idx else (20, 20)
            dr.rectangle([ox + x, y, ox + x + w, y + h], outline=col, width=2)
            dr.text((ox + x, y - 16), f"f5 t={e.get('f3')} n={len(idx)} {w}x{h}",
                    fill=col, font=f)
        elif v == 4:                                 # plain image
            p = pos(e, "f2")
            x, y = p.get(1, 0), p.get(2, 0)
            i = e.get("f1")
            w, h = dims.get(i, (0, 0))
            if (w, h) != SCREEN:
                dr.rectangle([ox + x, y, ox + x + w, y + h], outline=col, width=2)
                dr.text((ox + x, y - 16), f"f4 img{i} {w}x{h}", fill=col, font=f)
        elif v == 20:                                # animation
            idx = e.get("f1", [])
            p = pos(e, "f2")
            dr.text((ox + 8, 8), f"ANIM {len(idx)} frames @ {e.get('f3')}ms "
                                 f"pos={p}", fill=col, font=f)
        elif v == 8:                                 # bitmap hand
            box = pos(e, "f2")
            piv = pos(e, "f3")
            i = e.get("f1")
            w, h = dims.get(i, (6, 40))
            bx, by = box.get(1, 0), box.get(2, 0)
            bw, bh = box.get(3, 0), box.get(4, 0)
            cx, cy = bx + bw / 2, by + bh / 2
            dr.rectangle([ox + bx, by, ox + bx + bw, by + bh], outline=(160, 160, 255))
            dr.rectangle([ox + cx - piv.get(1, 0), cy - piv.get(2, 0),
                          ox + cx - piv.get(1, 0) + w, cy - piv.get(2, 0) + h],
                         outline=(255, 255, 255), width=2)
            dr.text((ox + cx + 6, cy - piv.get(2, 0)), f"bmp hand f6={e.get('f6')}",
                    fill=(255, 255, 255), font=f)
        elif v == 23:                                # vector hand
            pts = [(ox + x, y) for x, y in e["poly"]]
            if len(pts) >= 3:
                dr.polygon(pts, outline=col)
            for c in e["circ"]:
                cx, cy = c["c"].get(1, 0), c["c"].get(2, 0)
                r = c.get(2, 3)
                dr.ellipse([ox + cx - r, cy - r, ox + cx + r, cy + r], outline=col)
            if pts:
                dr.text((pts[0][0] + 6, pts[0][1]), f"hand f6={e.get('f6')}",
                        fill=col, font=f)
    os.makedirs(OUT, exist_ok=True)
    canvas.save(os.path.join(OUT, name + ".png"))
    return os.path.join(OUT, name + ".png")


def main():
    names = sys.argv[1:]
    base = os.environ.get("WF_SRC", SRC)
    if not names or names[0] == "--all":
        names = [f[:-4] for f in sorted(os.listdir(base)) if f.endswith(".bin")]
    src = os.environ.get("WF_SRC")
    th = os.environ.get("WF_THUMBS")
    for n in names:
        try:
            print(render(n, src, th))
        except Exception as e:
            print(f"{n}: {e}")


if __name__ == "__main__":
    main()
