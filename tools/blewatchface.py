#!/usr/bin/env python3
"""Build and send a custom watchface layout to the KW80.

    ../.venv/bin/python tools/blewatchface.py            # dry run, prints the frame
    ../.venv/bin/python tools/blewatchface.py --send     # actually send it

This WRITES to the watch and changes what is displayed. It does not touch DFU
or firmware. Recover via the watch's own Watchface screen, or a factory reset.

Frame, from SetCustomWatchface.watchfaceToBytes():

    6F 1E 71 <len:LE16> <payload> 8F
    payload = <subcmd> <id:LE32> <widget blocks...>
        subcmd 0x02 = SetCustomWatchface, 0x03 = SetNewCustomWatchface

    per widget:
        position (skipped for Dial/HourHand/MinuteHand/SecondHand):
            <idx> <type> 00 04 <x:LE16> <y:LE16>
        base:
            <idx> <type>
        colour   (optional): 02 04 <colour bytes, reversed>
        style    (optional): <idx> <type> 03 01 <style>

WidgetType (NOT the WlWatchfaceWidgetWire enum — different numbering):
"""
import argparse
import asyncio
import sys

from bleak import BleakClient, BleakScanner

WRITE_CH = "00008001-0000-1000-8000-00805f9b34fb"
NOTIFY = ("00008002-0000-1000-8000-00805f9b34fb",
          "00008004-0000-1000-8000-00805f9b34fb")

TYPE = dict(Heartrate=0, Step=1, Calorie=2, Distance=3, Date=4, Dial=5,
            Weather=6, POINTER=7, Battery=8, Duration=9, Time=13, REMIND=14,
            HourHand=16, MinuteHand=17, SecondHand=18)
NO_POSITION = {TYPE["Dial"], TYPE["HourHand"], TYPE["MinuteHand"], TYPE["SecondHand"]}


def le(v, n):
    return bytes((v >> (8 * i)) & 0xFF for i in range(n))


def build(widgets, wf_id=0, subcmd=0x02):
    """widgets: list of dicts {type, x, y, colour=None, style=None}"""
    p = bytearray([subcmd]) + le(wf_id, 4)
    for idx, w in enumerate(widgets):
        t = w["type"]
        if w.get("x") is not None and t not in NO_POSITION:
            p += bytes([idx, t, 0x00, 0x04]) + le(w["x"], 2) + le(w["y"], 2)
        p += bytes([idx, t])
        if w.get("colour") is not None:
            c = le(w["colour"], 4)
            p += bytes([0x02, 0x04]) + bytes(reversed(c))
        if w.get("style") is not None and w["style"] >= 0:
            p += bytes([idx, t, 0x03, 0x01, w["style"] & 0xFF])
    return bytes([0x6F, 0x1E, 0x71]) + le(len(p), 2) + bytes(p) + b"\x8f"


def decode(raw):
    if len(raw) < 6:
        return "short"
    cmd, d = raw[1], raw[2]
    ln = raw[3] | (raw[4] << 8)
    body = raw[5:5 + ln]
    if d == 0x81 and len(body) >= 2:
        st = {0x00: "OK", 0x02: "UNSUPPORTED"}.get(body[1], hex(body[1]))
        return f"status for 0x{body[0]:02x}: {st}"
    return f"data({ln}) {body.hex(' ')}"


GET_IDS = bytes([0x6F, 0x1E, 0x70, 0x01, 0x00, 0x00, 0x8F])


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="actually write to the watch")
    ap.add_argument("--id", type=int, default=0)
    ap.add_argument("--subcmd", type=lambda s: int(s, 0), default=0x02)
    args = ap.parse_args()

    # Minimal layout: a single Time element, comfortably inside the 368x448 screen.
    widgets = [dict(type=TYPE["Time"], x=100, y=200)]
    frame = build(widgets, wf_id=args.id, subcmd=args.subcmd)

    print("widgets :", widgets)
    print(f"frame   : {frame.hex(' ')}")
    print(f"length  : {len(frame)} bytes (payload {len(frame) - 6})")
    if not args.send:
        print("\ndry run — pass --send to write it to the watch")
        return

    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: "KW80" in ((adv.local_name or d.name or "").upper()), timeout=20.0)
    if not dev:
        print("watch not found")
        sys.exit(1)

    got = []
    async with BleakClient(dev) as client:
        print(f"\nconnected: {client.is_connected}")
        for ch in NOTIFY:
            try:
                await client.start_notify(ch, lambda _c, d: got.append(bytes(d)))
            except Exception:
                pass

        async def step(label, payload, wait=3.0):
            got.clear()
            print(f"\n[{label}] -> {payload.hex(' ')}")
            await client.write_gatt_char(WRITE_CH, payload, response=False)
            await asyncio.sleep(wait)
            print("   <-", decode(b"".join(got)) if got else "(no reply)")

        await step("GetWatchfaceIDs (before)", GET_IDS, 2.0)
        await step("SetCustomWatchface", frame, 5.0)
        await step("GetWatchfaceIDs (after)", GET_IDS, 3.0)


if __name__ == "__main__":
    asyncio.run(main())
