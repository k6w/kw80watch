#!/usr/bin/env python3
"""Capability probes for the KW80 — one upload answers one open question.

    ../.venv/bin/python tools/wfprobe.py arcs    /tmp/p1.bin
    ../.venv/bin/python tools/wfprobe.py rot     /tmp/p2.bin
    ../.venv/bin/python tools/wfprobe.py sources /tmp/p3.bin
    ../.venv/bin/python tools/wfprobe.py bmphand /tmp/p4.bin

    ../.venv/bin/python tools/wfupload.py --raw /tmp/p1.bin --send

Each probe paints its own legend into the background, so the answer can be read
straight off a photo of the watch. Unsupported features are expected to render
as nothing — that is how cf=4 glyphs behaved (docs/07-binary-format.md), and it
is the assumption these probes are built on.

Open questions addressed — docs/10-watchface-capabilities.md §8:

  arcs     Does Circle.start/end accept angles other than 0/360?
           If yes, f23 becomes a progress-ring primitive.
  rot      Which rotation sources exist beyond 150/153/154?
           Tests 151,152,155,156,157,158,159,160,161,162,163.
  rot2     The same question, one source per concentric ring so overlapping
           needles cannot be confused. Prefer this one.
  sources  Which Digits sources exist beyond the 10 known ones?
           Tests 3,5,6,7,8,10,11,15,16,18,19,20.
  bmphand  Does the f8 bitmap-hand element work on the KW80 at all?
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from wfimage import encode_pixels, lvgl_header  # noqa: E402
from wfbuild import TRAILER, encode_pixels_alpha, digit_group, msg, u  # noqa: E402

W, H = 368, 448
THUMB = (180, 219)
CX, CY = W // 2, H // 2
SF = "/System/Library/Fonts/SFCompact.ttf"


def sf(size, weight=400):
    f = ImageFont.truetype(SF, size)
    try:
        f.set_variation_by_axes([19, 400, weight])
    except Exception:
        pass
    return f


# ------------------------------------------------------------------ protobuf
def rgb(r, g, b):
    return (u(1, r) if r else b"") + (u(2, g) if g else b"") + (u(3, b) if b else b"")


def vector(source, shapes, colour, canvas=None):
    """One f23 element. `canvas` = (x, y, w, h); default is the full screen."""
    x, y, w, h = canvas or (0, 0, W, H)
    box = (u(1, x) if x else b"") + (u(2, y) if y else b"") + u(3, w) + u(4, h)
    body = msg(1, box) + shapes + u(5, 360) + u(6, source)
    body += msg(7, rgb(*colour)) + msg(8, rgb(*colour))
    return msg(1, msg(23, body))


def poly(pts):
    return b"".join(msg(2, u(1, int(px)) + u(2, int(py))) for px, py in pts)


def arc(x, y, r, start, end):
    inner = msg(1, u(1, int(x)) + u(2, int(y))) + u(2, int(r))
    if start:
        inner += u(3, int(start))
    return msg(3, inner + u(4, int(end)))


def bar(cx, top, bottom, half_w):
    return poly([(cx - half_w, top), (cx - half_w, bottom),
                 (cx + half_w, bottom), (cx + half_w, top)])


def bitmap_hand(index, box, pivot, source):
    x, y, w, h = box
    body = u(1, index)
    body += msg(2, u(1, x) + u(2, y) + u(3, w) + u(4, h))
    body += msg(3, u(1, pivot[0]) + u(2, pivot[1]))
    body += u(5, 360) + u(6, source)
    return msg(1, msg(8, body))


# ------------------------------------------------------------------ container
def container(images, layout, thumb_src):
    blobs = []
    for kind, img, size in images:
        cf = 5 if kind == "a" else 4
        enc = encode_pixels_alpha if kind == "a" else encode_pixels
        blobs.append(lvgl_header(*size, cf=cf) + enc(img, *size))

    cnt = len(blobs) * 4
    table, body, cur = bytearray(), bytearray(), cnt
    for b in blobs:
        table += struct.pack("<I", cur)
        body += b
        cur += len(b)
    section2 = bytes(table) + bytes(body)

    thumb = lvgl_header(*THUMB, cf=4) + encode_pixels(thumb_src, *THUMB)
    off1 = 20
    off2 = off1 + len(thumb)
    off3 = off2 + len(section2)
    assert cnt <= 0x3F8, f"too many images: {cnt // 4}"
    assert len(layout) <= 0x800, f"layout {len(layout)} > 2048"
    return (struct.pack("<5I", off1, off2, cnt, off3, len(layout))
            + thumb + section2 + layout + TRAILER)


def sheet(title, lines, marks=()):
    """Dark background with a title and a legend, plus optional ring guides."""
    img = Image.new("RGB", (W, H), (6, 7, 10))
    dr = ImageDraw.Draw(img)
    dr.text((W / 2, 22), title, font=sf(21, 640), fill=(255, 176, 46), anchor="mm")
    f = sf(15, 460)
    for i, (text, col) in enumerate(lines):
        y = 52 + i * 21
        dr.rectangle([16, y - 6, 28, y + 6], fill=col)
        dr.text((36, y), text, font=f, fill=(190, 194, 204), anchor="lm")
    for cx, cy, r in marks:
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 43, 52), width=1)
        dr.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(70, 74, 84))
    return img


# ------------------------------------------------------------------ probes
def probe_arcs():
    """Four arcs with different start/end. Full rings mean start/end is ignored."""
    tests = [(84, 300, 40, None, 90, (255, 92, 92)),
             (184, 300, 40, None, 180, (92, 220, 120)),
             (284, 300, 40, None, 270, (92, 170, 255)),
             (184, 392, 34, 90, 270, (255, 214, 64))]
    bg = sheet("ARC PROBE", [
        ("red   end=90    quarter?", (255, 92, 92)),
        ("green end=180   half?", (92, 220, 120)),
        ("blue  end=270   3/4?", (92, 170, 255)),
        ("amber 90..270   bottom half?", (255, 214, 64)),
        ("full discs = start/end IGNORED", (150, 150, 160)),
    ], marks=[(t[0], t[1], t[2]) for t in tests])

    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))
    for x, y, r, s, e, col in tests:
        layout += vector(255, arc(x, y, r, s, e), col)
    layout += u(5, 1)
    return [("o", bg, (W, H))], layout, bg


def probe_rot():
    """One capsule per candidate rotation source, each a different length.

    A hand that appears and sits at an angle => the source exists. A hand stuck
    straight up => the source resolves to 0. No hand => unsupported.
    """
    cands = [(151, (255, 92, 92)), (152, (255, 150, 60)), (155, (255, 214, 64)),
             (156, (170, 230, 80)), (157, (92, 220, 120)), (158, (80, 220, 200)),
             (159, (92, 170, 255)), (160, (150, 130, 255)), (161, (220, 110, 240)),
             (162, (255, 110, 180)), (163, (200, 200, 210))]
    bg = sheet("ROTATION SOURCE PROBE", [
        ("longest = 151, shortest = 163", (150, 150, 160)),
        ("angled  -> source exists", (92, 220, 120)),
        ("straight up -> value is 0", (255, 214, 64)),
        ("missing -> unsupported", (255, 92, 92)),
    ], marks=[(CX, CY, 150)])

    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))
    for i, (src, col) in enumerate(cands):
        top = CY - 150 + i * 11                       # each shorter than the last
        layout += vector(src, bar(CX, top, CY - 12, 2), col)
    layout += vector(255, arc(CX, CY, 6, None, 360), (240, 240, 245))
    layout += u(5, 1)
    return [("o", bg, (W, H))], layout, bg


ROT_CANDS = [151, 152, 155, 156, 157, 158, 159, 160, 161, 162, 163]
ROT_COLS = [(255, 92, 92), (255, 150, 60), (255, 214, 64), (170, 230, 80),
            (92, 220, 120), (80, 220, 200), (92, 170, 255), (150, 130, 255),
            (220, 110, 240), (255, 110, 180), (225, 225, 235)]


def probe_rot2():
    """One source per concentric ring — no overlap, so nothing to disentangle.

    `probe_rot` stacked eleven needles on a shared centre. On a photo of a
    glossy screen the overlapping segments could not be told apart. Here each
    source gets its own 11 px ring: innermost is 151, outermost 163, each ring
    labelled at 6 o'clock, each with a faint full track so an empty ring is
    still visible.

    Reading it: a segment on a ring means that source exists. Its angle is the
    value. A ring with only the faint track means the source is unsupported.
    """
    R0, STEP, THICK = 44, 12, 10
    bg = Image.new("RGB", (W, H), (6, 7, 10))
    dr = ImageDraw.Draw(bg)
    dr.text((W / 2, 18), "ROTATION RINGS  151 in -> 163 out", font=sf(17, 640),
            fill=(255, 176, 46), anchor="mm")
    dr.text((W / 2, 36), "segment = source exists;  bare ring = unsupported",
            font=sf(12, 420), fill=(140, 144, 154), anchor="mm")

    f = sf(11, 640)
    for i, src in enumerate(ROT_CANDS):
        r = R0 + i * STEP
        mid = r + THICK / 2
        dr.ellipse([CX - mid, CY - mid, CX + mid, CY + mid],
                   outline=tuple(int(c * 0.22) for c in ROT_COLS[i]), width=THICK)
        dr.text((CX, CY + r + THICK / 2), str(src)[-2:], font=f,
                fill=(150, 154, 164), anchor="mm")
    dr.text((CX, CY - 8), "12", font=sf(13, 620), fill=(90, 94, 104), anchor="mm")

    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))
    for i, src in enumerate(ROT_CANDS):
        r = R0 + i * STEP
        # a chunky segment sitting in this ring only, authored pointing up
        layout += vector(src, bar(CX, CY - r - THICK, CY - r, 6), ROT_COLS[i])
    layout += u(5, 1)
    return [("o", bg, (W, H))], layout, bg


def probe_sources():
    """Digit groups on unclaimed source IDs. Whichever draw a number, exist."""
    cands = [3, 5, 6, 7, 8, 10, 11, 15, 16, 18, 19, 20]
    dw, dh = 22, 30
    f = sf(int(dh * 0.86), 420)
    glyphs = []
    for d in "0123456789":
        g = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((dw / 2, dh / 2), d, font=f,
                               fill=(120, 255, 160, 255), anchor="mm")
        glyphs.append(g)

    bg = Image.new("RGB", (W, H), (6, 7, 10))
    dr = ImageDraw.Draw(bg)
    dr.text((W / 2, 20), "DIGIT SOURCE PROBE", font=sf(19, 640),
            fill=(255, 176, 46), anchor="mm")
    dr.text((W / 2, 40), "a number appearing = that source exists",
            font=sf(13, 420), fill=(140, 144, 154), anchor="mm")
    for i, s in enumerate(cands):
        col, row = i % 2, i // 2
        x, y = 24 + col * 172, 62 + row * 62
        dr.text((x, y + dh / 2), f"{s:>3}", font=sf(17, 620),
                fill=(190, 194, 204), anchor="lm")
        dr.rectangle([x + 40, y, x + 40 + 3 * dw, y + dh],
                     outline=(34, 37, 45), width=1)

    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))
    for i, s in enumerate(cands):
        col, row = i % 2, i // 2
        x, y = 24 + col * 172, 62 + row * 62
        layout += digit_group(list(range(2, 12)), x + 40, y, s, dw, dh, f23=5)
    layout += u(5, 1)

    images = [("o", bg, (W, H))] + [("a", g, (dw, dh)) for g in glyphs]
    return images, layout, bg


def probe_bmphand():
    """Does f8 render at all? A single sprite bound to the minute hand."""
    sw, sh = 12, 150
    sprite = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(sprite)
    d.rounded_rectangle([1, 1, sw - 2, sh - 2], radius=5,
                        fill=(255, 176, 46, 255))
    d.ellipse([2, sh - 26, sw - 3, sh - 4], fill=(120, 60, 0, 255))

    bg = sheet("BITMAP HAND PROBE  (f8)", [
        ("amber bar = f8 works, src=153", (255, 176, 46)),
        ("white bar = f23 control, src=153", (240, 240, 245)),
        ("only white -> f8 unsupported", (150, 150, 160)),
    ], marks=[(CX, CY, 140)])

    # pivot 120 px down the sprite, so 30 px of tail
    box = (CX - 120, CY - 120, 240, 240)
    layout = msg(1, msg(4, u(1, 1) + msg(2, b"")))
    layout += vector(153, bar(CX, CY - 100, CY - 20, 4), (240, 240, 245))
    layout += bitmap_hand(2, box, (sw // 2, 120), 153)
    layout += vector(255, arc(CX, CY, 7, None, 360), (240, 240, 245))
    layout += u(5, 1)
    return [("o", bg, (W, H)), ("a", sprite, (sw, sh))], layout, bg


PROBES = {"arcs": probe_arcs, "rot": probe_rot, "rot2": probe_rot2,
          "sources": probe_sources, "bmphand": probe_bmphand}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PROBES:
        sys.exit(f"usage: wfprobe.py {{{'|'.join(PROBES)}}} [out.bin]")
    name = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else f"probe-{name}.bin"
    images, layout, bg = PROBES[name]()
    blob = container(images, layout, bg)
    open(out, "wb").write(blob)
    bg.save(f"/tmp/probe_{name}.png")
    print(f"wrote {out}  {len(blob):,} bytes   "
          f"{len(images)} images, layout {len(layout)}/2048 B")
    print(f"legend -> /tmp/probe_{name}.png")


if __name__ == "__main__":
    main()
