#!/usr/bin/env python3
"""Download the official KW80 watchface catalogue and binaries.

The vendor store requires no authentication. Files land in artifacts/samples/
and every download is verified against the catalogue's MD5.

    python3 tools/fetch_samples.py [PRODUCT_CODE]

PRODUCT_CODE defaults to HA01_HW (49 faces). HA01 returns an empty list.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

API = "https://api.huawo-wear.com/api/v1/products/{pc}/watchfaces?customerCode=&locale=en"
CDN = "https://static.huawo-wear.com/files/"
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "phoneOs": "Android",
    "appId": "com.huawo.hawofit",
    "appVersion": "2.5.2",
    "locale": "en",
}
ROOT = os.path.join(os.path.dirname(__file__), "..")


def get(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=HEADERS), timeout=30
    ).read()


def main():
    pc = sys.argv[1] if len(sys.argv) > 1 else "HA01_HW"
    outdir = os.path.join(ROOT, "artifacts", "samples")
    os.makedirs(outdir, exist_ok=True)

    catalogue = json.loads(get(API.format(pc=pc)))
    cat_path = os.path.join(ROOT, "artifacts", f"{pc.lower()}-watchfaces.json")
    with open(cat_path, "w") as fh:
        json.dump(catalogue, fh, indent=2, ensure_ascii=False)
    print(f"{pc}: {catalogue['total']} faces -> {cat_path}")

    ok = bad = skip = 0
    for row in catalogue["rows"]:
        dest = os.path.join(outdir, f"{row['name']}.bin")
        if os.path.exists(dest):
            skip += 1
            continue
        try:
            blob = get(CDN + row["bin"])
        except Exception as exc:
            print(f"  FAIL {row['name']}: {exc}")
            bad += 1
            continue
        if hashlib.md5(blob).hexdigest() != row["binMd5"]:
            print(f"  MD5 MISMATCH {row['name']}")
            bad += 1
            continue
        with open(dest, "wb") as fh:
            fh.write(blob)
        print(f"  ok {row['name']:10s} {len(blob):>9,d} bytes")
        ok += 1
        time.sleep(0.15)  # be polite to the CDN

    print(f"\ndownloaded={ok} skipped={skip} failed={bad}")


if __name__ == "__main__":
    main()
