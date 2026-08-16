#!/usr/bin/env python3
"""Census every element, field and value across all 49 vendor KW80 watchfaces.

    ../.venv/bin/python tools/wfcensus.py artifacts/samples

Parses the section-3 protobuf layout of each face into a generic tree, then
aggregates:
  * which Element variants (the oneof field number) exist and how often
  * every sub-field of every variant, with its observed value range
  * every f5 (data source) value, with the image-group size it is paired with
  * the image table, so group sizes can be matched to element declarations

Nothing here is inferred — it is a straight count over the vendor's own files,
which is the strongest evidence class available short of running on hardware.
"""
import collections
import json
import os
import struct
import sys

MAGIC_TAIL = b"OLWF"


# ------------------------------------------------------------------ protobuf
def varint(b, i):
    shift = val = 0
    while True:
        c = b[i]
        val |= (c & 0x7F) << shift
        i += 1
        shift += 7
        if not c & 0x80:
            return val, i


def parse(b, depth=0):
    """Return [(field, wiretype, value)] where value is bytes or int."""
    out, i = [], 0
    while i < len(b):
        try:
            key, i = varint(b, i)
        except IndexError:
            break
        f, wt = key >> 3, key & 7
        if f == 0:
            raise ValueError("field 0")
        if wt == 0:
            v, i = varint(b, i)
        elif wt == 2:
            ln, i = varint(b, i)
            if i + ln > len(b):
                raise ValueError("truncated")
            v, i = b[i:i + ln], i + ln
        elif wt == 5:
            v, i = struct.unpack_from("<I", b, i)[0], i + 4
        elif wt == 1:
            v, i = struct.unpack_from("<Q", b, i)[0], i + 8
        else:
            raise ValueError(f"wiretype {wt}")
        out.append((f, wt, v))
    return out


def looks_like_message(b):
    if not b:
        return False
    try:
        items = parse(b)
    except Exception:
        return False
    return bool(items)


def tree(b, depth=0):
    """Recursively decode, treating any parsable submessage as a message."""
    node = []
    for f, wt, v in parse(b):
        if wt == 2 and depth < 6 and looks_like_message(v):
            node.append((f, "msg", tree(v, depth + 1), v))
        elif wt == 2:
            node.append((f, "bytes", v, v))
        else:
            node.append((f, "int", v, v))
    return node


# ------------------------------------------------------------------ container
def load(path):
    b = open(path, "rb").read()
    if b[-4:] != MAGIC_TAIL:
        raise ValueError("not OLWF")
    off1, off2, cnt, off3, len3 = struct.unpack_from("<5I", b, 0)
    layout = b[off3:off3 + len3]
    n = cnt // 4
    table = [struct.unpack_from("<I", b, off2 + 4 * k)[0] for k in range(n)]
    images = []
    for k, rel in enumerate(table):
        hdr = struct.unpack_from("<I", b, off2 + rel)[0]
        images.append({
            "i": k,
            "cf": hdr & 0x1F,
            "w": (hdr >> 10) & 0x7FF,
            "h": (hdr >> 21) & 0x7FF,
            "off": off2 + rel,
        })
    return {"file": os.path.basename(path), "size": len(b), "cnt": cnt,
            "len3": len3, "layout": layout, "images": images}


# ------------------------------------------------------------------ reporting
def fmt(v, limit=42):
    if isinstance(v, int):
        return str(v)
    h = v.hex()
    return h if len(h) <= limit else h[:limit] + f"…({len(v)}B)"


def show(node, indent=2, out=None):
    for f, kind, val, raw in node:
        pad = " " * indent
        if kind == "msg":
            out.append(f"{pad}f{f} {{   ({len(raw)}B)")
            show(val, indent + 2, out)
            out.append(f"{pad}}}")
        else:
            out.append(f"{pad}f{f} = {fmt(val)}")
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "artifacts/samples"
    files = sorted(f for f in os.listdir(src) if f.endswith(".bin"))

    variants = collections.Counter()          # element oneof field -> count
    subfields = collections.defaultdict(lambda: collections.defaultdict(list))
    f5_values = collections.Counter()
    f5_group = collections.defaultdict(collections.Counter)
    root_fields = collections.Counter()
    per_file = {}
    fail = []

    for fn in files:
        try:
            face = load(os.path.join(src, fn))
            t = tree(face["layout"])
        except Exception as e:
            fail.append((fn, str(e)))
            continue

        elems = []
        for f, kind, val, raw in t:
            root_fields[f] += 1
            if f != 1 or kind != "msg":
                continue
            for vf, vkind, vval, vraw in val:
                variants[vf] += 1
                if vkind != "msg":
                    subfields[vf]["<scalar>"].append(vval)
                    continue
                rec = {"variant": vf}
                for sf, skind, sval, sraw in vval:
                    if skind == "msg":
                        inner = {}
                        for xf, xkind, xval, xraw in sval:
                            if xkind != "msg":
                                inner[f"f{xf}"] = xval if xkind == "int" else xval.hex()
                        subfields[vf][f"f{sf}{{}}"].append(inner)
                        rec[f"f{sf}"] = inner
                    elif skind == "bytes":
                        subfields[vf][f"f{sf}[]"].append(len(sval))
                        rec[f"f{sf}"] = list(sval)
                    else:
                        subfields[vf][f"f{sf}"].append(sval)
                        rec[f"f{sf}"] = sval
                if vf in (5, 6) and "f5" in rec:
                    f5_values[rec["f5"]] += 1
                    n = len(rec.get("f1", [])) if isinstance(rec.get("f1"), list) else 0
                    f5_group[rec["f5"]][n] += 1
                elems.append(rec)

        per_file[fn] = {"images": face["images"], "elements": elems,
                        "cnt": face["cnt"], "len3": face["len3"],
                        "size": face["size"]}

    print(f"parsed {len(per_file)}/{len(files)} faces; {len(fail)} failed")
    for fn, e in fail:
        print(f"  FAIL {fn}: {e}")

    print("\n=== root fields ===")
    for f, c in sorted(root_fields.items()):
        print(f"  f{f}: {c}")

    print("\n=== element variants (the oneof) ===")
    for f, c in sorted(variants.items()):
        print(f"  f{f:<3} x{c}")

    print("\n=== sub-fields per variant ===")
    for vf in sorted(subfields):
        print(f"\n-- variant f{vf} --")
        for name, vals in sorted(subfields[vf].items()):
            if vals and isinstance(vals[0], dict):
                keys = collections.Counter()
                for d in vals:
                    for k in d:
                        keys[k] += 1
                sample = vals[0]
                print(f"  {name:<10} n={len(vals):<4} keys={dict(keys)} eg={sample}")
            elif vals and isinstance(vals[0], int):
                uniq = sorted(set(vals))
                s = uniq if len(uniq) <= 14 else f"{uniq[:12]}…{uniq[-1]} ({len(uniq)} distinct)"
                print(f"  {name:<10} n={len(vals):<4} values={s}")
            else:
                print(f"  {name:<10} n={len(vals)}")

    print("\n=== f5 (data source) values, with paired image-group sizes ===")
    for v in sorted(f5_values):
        print(f"  f5={v:<4} x{f5_values[v]:<4} group sizes: {dict(f5_group[v])}")

    json.dump(per_file, open("artifacts/analysis/layout-census.json", "w"), indent=1)
    print("\nwrote artifacts/analysis/layout-census.json")

    if len(sys.argv) > 2:
        fn = sys.argv[2]
        face = load(os.path.join(src, fn))
        print(f"\n=== full tree: {fn} ===")
        print("\n".join(show(tree(face["layout"]), 2, [])))
        print(f"\n--- {len(face['images'])} images ---")
        for im in face["images"]:
            print(f"  [{im['i']:3d}] cf={im['cf']:<3} {im['w']:>4}x{im['h']:<4}")


if __name__ == "__main__":
    main()
