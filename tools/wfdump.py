#!/usr/bin/env python3
"""Parse a KW80 watchface .bin: header, sections, and the protobuf layout.

    python3 tools/wfdump.py artifacts/samples/WF01.bin

See docs/07-binary-format.md for the format description. The section-1 image
codec is not yet decoded, so only its size and entropy are reported.
"""
import collections
import math
import struct
import sys

MAGIC = b"UCPDOLWF"
SECTION1_CONST = bytes.fromhex("18d0621b")


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def entropy(data):
    if not data:
        return 0.0
    counts = collections.Counter(data)
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def read_varint(b, i):
    shift = value = 0
    while True:
        byte = b[i]
        value |= (byte & 0x7F) << shift
        i += 1
        shift += 7
        if not byte & 0x80:
            return value, i


def decode_protobuf(b, depth=0):
    """Best-effort recursive protobuf dump. Unknown schema, so field numbers only."""
    lines = []
    i = 0
    pad = "  " * depth
    while i < len(b):
        try:
            key, i = read_varint(b, i)
        except IndexError:
            break
        field, wire = key >> 3, key & 7
        try:
            if wire == 0:
                val, i = read_varint(b, i)
                lines.append(f"{pad}f{field} varint = {val}")
            elif wire == 2:
                ln, i = read_varint(b, i)
                sub, i = b[i:i + ln], i + ln
                if sub and all(32 <= c < 127 for c in sub):
                    lines.append(f"{pad}f{field} str = {sub.decode()!r}")
                elif sub:
                    lines.append(f"{pad}f{field} msg ({ln} bytes) {{")
                    inner = decode_protobuf(sub, depth + 1)
                    lines.append(inner if inner else f"{pad}  <bytes {sub.hex(' ')}>")
                    lines.append(f"{pad}}}")
                else:
                    lines.append(f"{pad}f{field} msg (empty)")
            elif wire == 5:
                i += 4
                lines.append(f"{pad}f{field} fixed32")
            elif wire == 1:
                i += 8
                lines.append(f"{pad}f{field} fixed64")
            else:
                break
        except (IndexError, UnicodeDecodeError):
            break
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()

    hdr_len, unk04, unk08, s1, s2 = (u32(b, o) for o in (0, 4, 8, 12, 16))

    print(f"=== {path} ({len(b):,} bytes) ===")
    print(f"  0x00 header length : {hdr_len}")
    print(f"  0x04 unidentified  : {unk04:,}")
    print(f"  0x08 unidentified  : {unk08}")
    print(f"  0x0C section1 (S1) : {s1:,}")
    print(f"  0x10 section2 (S2) : {s2:,}")

    print("\n  checks:")
    print(f"    S1 + S2 + 8 == filesize : {s1 + s2 + 8 == len(b)}")
    print(f"    trailer magic UCPDOLWF  : {b[-8:] == MAGIC}")
    print(f"    section1 const at 0x14  : {b[20:24] == SECTION1_CONST}")

    body = b[20:s1]
    print(f"\n  section 1 (images): {len(body):,} bytes, "
          f"entropy {entropy(body):.2f} bits/byte  [codec not yet decoded]")

    print(f"\n  section 2 (protobuf layout): {s2} bytes")
    print(decode_protobuf(b[s1:s1 + s2]))


if __name__ == "__main__":
    main()
