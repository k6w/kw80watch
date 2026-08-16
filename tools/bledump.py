#!/usr/bin/env python3
"""Run every parameterless GET command against the watch and record the replies.

    ../.venv/bin/python tools/bledump.py

READ-ONLY: only commands with direction byte 0x70 (get) are sent. Command bytes
come from artifacts/get-commands.json, extracted verbatim from the app's
sendBytes() methods.

Frame: 6F <cmd> <dir> <len:LE16> <payload...> 8F
       dir 0x70=get 0x71=set ; reply 0x80=data 0x81=status[origcmd,status]
"""
import asyncio
import json
import os
import sys

from bleak import BleakClient, BleakScanner

WRITE_CH = "00008001-0000-1000-8000-00805f9b34fb"
NOTIFY = ("00008002-0000-1000-8000-00805f9b34fb",
          "00008004-0000-1000-8000-00805f9b34fb")
ROOT = os.path.join(os.path.dirname(__file__), "..")
STATUS = {0x00: "OK", 0x02: "UNSUPPORTED"}


def decode(raw):
    if len(raw) < 6:
        return None, None, "short"
    cmd, d = raw[1], raw[2]
    ln = raw[3] | (raw[4] << 8)
    body = raw[5:5 + ln]
    if d == 0x81 and len(body) >= 2:
        return cmd, body, f"status for 0x{body[0]:02x}: {STATUS.get(body[1], hex(body[1]))}"
    if d == 0x80:
        txt = ""
        pr = bytes(c for c in body if 32 <= c < 127)
        if len(pr) >= max(3, len(body) // 2):
            txt = f'  "{body.decode("utf-8", "replace").strip(chr(0))}"'
        return cmd, body, f"{len(body)}B {body.hex(' ')}{txt}"
    return cmd, body, f"dir=0x{d:02x} {body.hex(' ')}"


async def main():
    cmds = json.load(open(os.path.join(ROOT, "artifacts", "get-commands.json")))
    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: "KW80" in ((adv.local_name or d.name or "").upper()), timeout=20.0)
    if not dev:
        print("watch not found")
        sys.exit(1)

    got = []
    results = {}

    def on_notify(_c, data):
        got.append(bytes(data))

    async with BleakClient(dev) as client:
        print(f"connected: {client.is_connected}   commands: {len(cmds)}\n")
        for ch in NOTIFY:
            try:
                await client.start_notify(ch, on_notify)
            except Exception:
                pass

        for name, vals in sorted(cmds.items()):
            got.clear()
            payload = bytes(vals)
            try:
                await client.write_gatt_char(WRITE_CH, payload, response=False)
            except Exception as exc:
                print(f"  {name:<34} WRITE FAILED {exc}")
                continue
            await asyncio.sleep(0.9)
            if not got:
                print(f"  {name:<34} (no reply)")
                results[name] = None
                continue
            raw = b"".join(got)
            _, body, desc = decode(raw)
            print(f"  {name:<34} {desc[:110]}")
            results[name] = {"cmd": payload.hex(" "), "raw": raw.hex(" "),
                             "body": body.hex(" ") if body else None}

        for ch in NOTIFY:
            try:
                await client.stop_notify(ch)
            except Exception:
                pass

    out = os.path.join(ROOT, "artifacts", "device-dump.json")
    json.dump(results, open(out, "w"), indent=1)
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
