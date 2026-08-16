#!/usr/bin/env python3
"""Bind the KW80 to this machine.

    ../.venv/bin/python tools/blebind.py [--uuid SIXTEENCHARSXX]

This WRITES to the watch: it changes bind state. It does not touch DFU and
cannot alter firmware. To undo, factory-reset the watch or re-pair in HaWoFit.

Frame format (from com.huawo.sdk.bluetoothsdk.interfaces.ops):

    6F <cmd> <dir> <len:LE16> <payload...> 8F
        dir 0x70 = get, 0x71 = set
        responses: 0x80 = ok, 0x81 = error

    StartBind         6F 93 71 01 00 01 8F
    StartConfirmBind  6F 93 71 11 00 00 <16 bytes> 8F
    EndBind           6F 94 71 01 00 01 8F
    GetBindState      6F 94 70 01 00 00 8F
"""
import argparse
import asyncio
import sys

from bleak import BleakClient, BleakScanner

WRITE_CH = "00008001-0000-1000-8000-00805f9b34fb"
NOTIFY_CH = "00008002-0000-1000-8000-00805f9b34fb"
NOTIFY_CH2 = "00008004-0000-1000-8000-00805f9b34fb"


def frame(cmd, direction, payload=b""):
    return bytes([0x6F, cmd, direction, len(payload) & 0xFF,
                  (len(payload) >> 8) & 0xFF]) + payload + b"\x8f"


START_BIND = frame(0x93, 0x71, bytes([0x01]))
END_BIND = frame(0x94, 0x71, bytes([0x01]))
GET_BIND_STATE = frame(0x94, 0x70, bytes([0x00]))


def confirm_bind(uuid16: bytes):
    assert len(uuid16) == 16
    return frame(0x93, 0x71, bytes([0x00]) + uuid16)


def describe(raw: bytes):
    if len(raw) < 6:
        return "short frame"
    cmd, direction = raw[1], raw[2]
    ln = raw[3] | (raw[4] << 8)
    body = raw[5:5 + ln]
    kind = {0x80: "OK", 0x81: "ERROR"}.get(direction, f"dir=0x{direction:02x}")
    return f"cmd=0x{cmd:02x} {kind} len={ln} payload={body.hex(' ') or '(empty)'}"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uuid", default="KW80MACCLIENT01",
                    help="client id, padded/truncated to 16 bytes")
    ap.add_argument("--wait", type=float, default=4.0)
    args = ap.parse_args()

    uuid16 = args.uuid.encode()[:16].ljust(16, b"\x00")

    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: "KW80" in ((adv.local_name or d.name or "").upper()), timeout=20.0)
    if not dev:
        print("watch not found")
        sys.exit(1)

    seen = []

    def on_notify(_c, data):
        raw = bytes(data)
        seen.append(raw)
        print(f"    <- {raw.hex(' ')}")
        print(f"       {describe(raw)}")

    async with BleakClient(dev) as client:
        print(f"connected: {client.is_connected}")
        for ch in (NOTIFY_CH, NOTIFY_CH2):
            try:
                await client.start_notify(ch, on_notify)
            except Exception as exc:
                print(f"  subscribe {ch[4:8]} failed: {exc}")

        async def step(label, payload, wait=None):
            seen.clear()
            print(f"\n[{label}]  -> {payload.hex(' ')}")
            await client.write_gatt_char(WRITE_CH, payload, response=False)
            await asyncio.sleep(wait or args.wait)
            if not seen:
                print("    (no reply)")

        await step("1. GetBindState (before)", GET_BIND_STATE, 2.0)
        await step("2. StartBind — the watch may prompt you to confirm ON THE WATCH",
                   START_BIND, 12.0)
        await step("3. StartConfirmBind", confirm_bind(uuid16), 8.0)
        await step("4. EndBind", END_BIND, 4.0)
        await step("5. GetBindState (after)", GET_BIND_STATE, 3.0)

        for ch in (NOTIFY_CH, NOTIFY_CH2):
            try:
                await client.stop_notify(ch)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
