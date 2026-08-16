#!/usr/bin/env python3
"""Sweep the Huawo upgrade API across every model in the device database.

READ-ONLY. Queries only; nothing is written anywhere.

HA01_HW itself returns no firmware. If a related model does, that image tells us
what this family's firmware looks like — header, whether it is signed or
encrypted, and what the OS actually is. That is analysis material even if the
image is never flashed.

    python3 tools/fw_sweep.py [--only-editor2]
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
URL = "https://api.huawo-wear.com/api/v1/devices/upgrades"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "okhttp/4.12.0",
    "phoneOs": "Android",
    "appId": "com.huawo.hawofit",
    "appVersion": "2.5.2",
    "locale": "en",
}


def probe(product_code):
    """Claim a very old version so the server offers whatever it has."""
    body = json.dumps({
        "currentVersion": "0.0.1",
        "productCode": product_code,
        "currentBuild": 0,
        "customerCode": "Huawo",
        "deviceId": "",
    }).encode()
    req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=25).read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {"error": str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-editor2", action="store_true",
                    help="limit to the KW80's editor-2 family")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(ROOT, "artifacts", "AppConfig.json")))
    models = cfg["productConfigs"]
    if args.only_editor2:
        models = [m for m in models if m.get("watchfaceEditor") == 2]

    codes = sorted({m["productCode"] for m in models if m.get("productCode")})
    print(f"probing {len(codes)} product codes ...\n")

    hits, empty, errors = [], 0, 0
    for code in codes:
        res = probe(code)
        if "error" in res:
            errors += 1
            print(f"  {code:<16} ERROR {res['error'][:60]}")
        elif res.get("data"):
            hits.append((code, res["data"]))
            print(f"  {code:<16} *** FIRMWARE FOUND ***")
            print(f"      {json.dumps(res['data'])[:400]}")
        else:
            empty += 1
        time.sleep(0.25)

    print(f"\nfirmware available: {len(hits)}   empty: {empty}   errors: {errors}")
    if hits:
        out = os.path.join(ROOT, "artifacts", "firmware-hits.json")
        with open(out, "w") as fh:
            json.dump({c: d for c, d in hits}, fh, indent=2, ensure_ascii=False)
        print(f"saved -> {out}")


if __name__ == "__main__":
    main()
