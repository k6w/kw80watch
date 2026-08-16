#!/usr/bin/env python3
"""Send a single query command to the KW80 and print the reply.

    ../.venv/bin/python tools/blequery.py deviceinfo

Only *query* commands are wired up here. Nothing in this file modifies watch
state, and nothing here touches the DFU service (0x1530).

Framing, from com.huawo.sdk.bluetoothsdk (see docs/08-ble-gatt.md):

    request  : 0x6F <..> <cmd> <..> <..> <chk> 0x8F
    response : [5-byte header][payload][1-byte 0x8F tail]

GetDeviceInfo.sendBytes() returns exactly: 6F 03 70 01 00 08 8F
DataManager.sendTaskData() writes that verbatim to 0x8001.
"""
import argparse
import asyncio
import sys

from bleak import BleakClient, BleakScanner

SERVICE = "00006006-0000-1000-8000-00805f9b34fb"
WRITE_CH = "00008001-0000-1000-8000-00805f9b34fb"
NOTIFY_CH = "00008002-0000-1000-8000-00805f9b34fb"
NOTIFY_CH2 = "00008004-0000-1000-8000-00805f9b34fb"

# Verbatim from the decompiled app's sendBytes(). READ-ONLY queries only.
# Structure: 6F <cmd> 70 01 00 <sub> 8F
COMMANDS = {
    "devicetype":      bytes([0x6F, 0x03, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    "firmwareversion": bytes([0x6F, 0x03, 0x70, 0x01, 0x00, 0x07, 0x8F]),
    "deviceinfo":      bytes([0x6F, 0x03, 0x70, 0x01, 0x00, 0x08, 0x8F]),
    "deviceid":        bytes([0x6F, 0x02, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    "battery":         bytes([0x6F, 0x08, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    "bindstate":       bytes([0x6F, 0x94, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    "sn":              bytes([0x6F, 0x41, 0x70, 0x01, 0x00, 0x0B, 0x8F]),
    "protocolversion": bytes([0x6F, 0x41, 0x70, 0x01, 0x00, 0x09, 0x8F]),
    "wfversion":       bytes([0x6F, 0x41, 0x70, 0x01, 0x00, 0x0A, 0x8F]),
    "watchfaceids":    bytes([0x6F, 0x1E, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    # added to cross-check the rotation-source probe against real device values
    "batterystate":    bytes([0x6F, 0x08, 0x70, 0x01, 0x00, 0x01, 0x8F]),
    "activitynum":     bytes([0x6F, 0x52, 0x70, 0x01, 0x00, 0x00, 0x8F]),
    "newestheartrate": bytes([0x6F, 0x62, 0x70, 0x01, 0x00, 0x01, 0x8F]),
    "goal":            bytes([0x6F, 0x50, 0x70, 0x01, 0x00, 0x00, 0x8F]),
}


def parse_tlv(payload):
    """ValueUnit list: 1-byte type, 1-byte length, then `length` data bytes."""
    units, i = [], 0
    while i + 2 <= len(payload):
        vtype, vlen = payload[i], payload[i + 1]
        data = payload[i + 2:i + 2 + vlen]
        if len(data) < vlen:
            break
        units.append((vtype, vlen, data))
        i += 2 + vlen
    return units


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=sorted(COMMANDS) + ["all"], nargs="?",
                    default="deviceinfo")
    ap.add_argument("--wait", type=float, default=3.0, help="seconds to collect replies")
    args = ap.parse_args()
    todo = sorted(COMMANDS) if args.command == "all" else [args.command]

    print(f"scanning for KW80 ...")
    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: "KW80" in ((adv.local_name or d.name or "").upper()), timeout=15.0
    )
    if not dev:
        print("watch not found — is it awake and in range?")
        sys.exit(1)

    chunks = []

    def on_notify(_char, data):
        chunks.append(bytes(data))
        print(f"  <- notify {len(data):>3} bytes: {bytes(data).hex(' ')}")

    async with BleakClient(dev) as client:
        print(f"connected: {client.is_connected}\n")
        for ch in (NOTIFY_CH, NOTIFY_CH2):
            try:
                await client.start_notify(ch, on_notify)
                print(f"  subscribed {ch[4:8]}")
            except Exception as exc:
                print(f"  could not subscribe {ch[4:8]}: {exc}")

        for name in todo:
            payload = COMMANDS[name]
            chunks.clear()
            print(f"\n  -> {name:<16} {payload.hex(' ')}")
            await client.write_gatt_char(WRITE_CH, payload, response=False)
            await asyncio.sleep(args.wait)
            if not chunks:
                print("     (no reply)")
                continue
            raw = b"".join(chunks)
            if len(raw) > 6:
                body = raw[5:-1]                    # GetTask.getBusinessBytes()
                inner = body[1:-1] if len(body) > 2 else body
                print(f"     PAYLOAD {len(body)} bytes: {body.hex(' ')}")
                for vtype, vlen, data in parse_tlv(inner):
                    printable = data and all(32 <= c < 127 for c in data)
                    extra = f'  "{data.decode("utf-8", "replace")}"' if printable else ""
                    print(f"       type={vtype:<3} len={vlen:<3} {data.hex(' ')}{extra}")
            else:
                print(f"     empty payload (status only)")

        for ch in (NOTIFY_CH, NOTIFY_CH2):
            try:
                await client.stop_notify(ch)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
