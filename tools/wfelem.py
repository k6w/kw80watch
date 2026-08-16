#!/usr/bin/env python3
"""Deep-dump one element variant across every vendor face.

    ../.venv/bin/python tools/wfelem.py 23        # the vector-hand element
    ../.venv/bin/python tools/wfelem.py 5         # the indexed picture-set element
    ../.venv/bin/python tools/wfelem.py 6         # the digit-group element

Prints each instance in full, with the file it came from and the image
dimensions of every index it references, so a group's meaning can be read off
directly instead of guessed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wfcensus import load, parse, tree  # noqa: E402

SRC = "artifacts/samples"


def render(node, indent, out):
    for f, kind, val, raw in node:
        pad = " " * indent
        if kind == "msg":
            out.append(f"{pad}f{f} {{")
            render(val, indent + 2, out)
            out.append(f"{pad}}}")
        elif kind == "bytes":
            out.append(f"{pad}f{f} = [{' '.join(str(x) for x in val)}]")
        else:
            out.append(f"{pad}f{f} = {val}")
    return out


def main():
    want = int(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None
    total = 0
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".bin") or (only and only not in fn):
            continue
        face = load(os.path.join(SRC, fn))
        dims = {im["i"] + 1: f"{im['w']}x{im['h']}/cf{im['cf']}" for im in face["images"]}
        hits = []
        for f, kind, val, raw in tree(face["layout"]):
            if f != 1 or kind != "msg":
                continue
            for vf, vkind, vval, vraw in val:
                if vf == want:
                    hits.append((vval, vraw))
        if not hits:
            continue
        print(f"\n########## {fn}   ({len(face['images'])} images) ##########")
        for k, (val, raw) in enumerate(hits):
            print(f"--- f{want} #{k}  ({len(raw)} B) ---")
            print("\n".join(render(val, 2, [])))
            # annotate any byte list with the images it points at
            for f, kind, v, _ in val:
                if kind == "bytes" and v and all(0 < x <= len(dims) for x in v):
                    seen, order = {}, []
                    for x in v:
                        if x not in seen:
                            seen[x] = dims.get(x, "?")
                            order.append(x)
                    print(f"    ^ f{f} -> " +
                          ", ".join(f"{x}:{seen[x]}" for x in order[:12]))
            total += 1
    print(f"\n{total} instances of variant f{want}")


if __name__ == "__main__":
    main()
