#!/usr/bin/env python3
"""Upload a watchface image to the KW80 over the OTA channel.

    ../.venv/bin/python tools/wfupload.py face.png            # dry run
    ../.venv/bin/python tools/wfupload.py face.png --send     # do it

Faithful port of com.huawo.sdk.bluetoothsdk.interfaces.ota.OtaControl.

    0. GetOtaAddress(id)   6F 1E 70 05 00 01 <id:LE32> 8F     data channel 0x8001
       then all on service 0x1530:
    1. -> 0x1531   01 <total_len:LE32>
    2. -> 0x1531   02 <type> <addr:4> <len:LE32> <crc:4> 14    type = 4 (Picture)
    3. -> 0x1532   payload, 128-byte chunks, 20 per batch, 2048-byte pieces
    4. -> 0x1531   04                                          verify CRC
    5. -> 0x1531   05                                          commit

The payload is tagged Picture(4). Firmware is Platform(1) and the
unrecoverable image is Bootloader(11); neither is ever sent here. The watch
stays in normal firmware — no EnterOta, no reboot into DFU mode.
"""
import argparse
import asyncio
import struct
import sys

from bleak import BleakClient, BleakScanner

sys.path.insert(0, __import__("os").path.dirname(__file__))
from wfimage import build, huawo_crc  # noqa: E402

DATA_W = "00008001-0000-1000-8000-00805f9b34fb"
DATA_N = ("00008002-0000-1000-8000-00805f9b34fb",
          "00008004-0000-1000-8000-00805f9b34fb")
OTA_CTRL = "00001531-0000-1000-8000-00805f9b34fb"
OTA_DATA = "00001532-0000-1000-8000-00805f9b34fb"

TYPE_PICTURE = 4
MTU = 128
PIECE = 2048
BATCH = 20


def le32(v):
    return struct.pack("<I", v)


def frame(cmd, d, pl):
    return bytes([0x6F, cmd, d, len(pl) & 0xFF, (len(pl) >> 8) & 0xFF]) + pl + b"\x8f"


def dec(raw):
    if len(raw) < 6:
        return "(none)"
    ln = raw[3] | (raw[4] << 8)
    body = raw[5:5 + ln]
    if raw[2] == 0x81 and len(body) >= 2:
        st = {0: "OK", 2: "UNSUPPORTED"}.get(body[1], hex(body[1]))
        return f"status 0x{body[0]:02x} -> {st}"
    return f"data({ln}) {body.hex(' ')}"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", help="image to encode (omit with --raw)")
    ap.add_argument("--raw", help="send a pre-built .bin container as-is")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--id", type=int, default=0)
    ap.add_argument("--pace", type=float, default=0.006,
                    help="delay per chunk; 0 = flat out (drops packets)")
    ap.add_argument("--batch-pause", type=float, default=0.03,
                    help="extra pause every 20 chunks")
    args = ap.parse_args()

    # In the app, OtaData.data = [address:4] + blob, and getOtaData() strips that
    # address. tools/wfimage.build() never includes the address, so the blob it
    # returns IS the payload — do not strip anything here.
    if args.raw:
        payload = open(args.raw, "rb").read()
        blob = payload
        print(f"raw container: {args.raw}")
    else:
        blob = build(args.image, wf_id=args.id)
        payload = blob
    crc = huawo_crc(payload)
    crc4 = bytes([crc & 0xFF, (crc >> 8) & 0xFF, 0, 0])

    pieces = (len(payload) + PIECE - 1) // PIECE
    chunks = (len(payload) + MTU - 1) // MTU

    print(f"source   : {args.raw or args.image}")
    print(f"blob     : {len(blob):,} bytes   payload {len(payload):,}")
    print(f"crc      : 0x{crc:04x}  -> {crc4.hex(' ')}")
    print(f"transfer : {pieces} pieces x {PIECE}B  =  {chunks} chunks x {MTU}B")

    print("\n--- control frames that will be sent ---")
    f1 = bytes([0x01]) + le32(len(payload))
    print(f"  1. 0x1531  {f1.hex(' ')}")
    print(f"  2. 0x1531  02 04 <addr:4> {le32(len(payload)).hex(' ')} {crc4.hex(' ')} 14")
    print(f"  3. 0x1532  {chunks} data chunks ...")
    print(f"     first  {payload[:MTU][:16].hex(' ')} ...")
    print(f"     last   {payload[-(len(payload) % MTU or MTU):][:16].hex(' ')} ...")
    print("  4. 0x1531  04")
    print("  5. 0x1531  05")

    if not args.send:
        print("\ndry run — pass --send to upload")
        return

    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: "KW80" in ((adv.local_name or d.name or "").upper()), timeout=20.0)
    if not dev:
        print("watch not found")
        sys.exit(1)

    got, ota = [], []
    async with BleakClient(dev) as c:
        print(f"\nconnected: {c.is_connected}  mtu={c.mtu_size}")
        for ch in DATA_N:
            try:
                await c.start_notify(ch, lambda _x, d: got.append(bytes(d)))
            except Exception:
                pass
        try:
            await c.start_notify(OTA_CTRL, lambda _x, d: ota.append(bytes(d)))
            print("  subscribed OTA control 0x1531")
        except Exception as e:
            print(f"  could not subscribe 0x1531: {e}")

        # 0. ask the watch where pictures live
        got.clear()
        q = frame(0x1E, 0x70, bytes([0x01]) + le32(args.id))
        print(f"\n[0] GetOtaAddress -> {q.hex(' ')}")
        await c.write_gatt_char(DATA_W, q, response=False)
        await asyncio.sleep(2.5)
        if not got:
            print("    no reply — aborting")
            return
        raw = b"".join(got)
        print("   <-", dec(raw))
        addr = raw[6:10]                    # skip 5-byte header + sub-command echo
        print(f"    address = {addr.hex(' ')}  (0x{struct.unpack('<I', addr)[0]:08x})")

        # --- event-driven state machine, mirroring OtaControl.otaRecvData ---
        q = asyncio.Queue()
        c._notify_q = q

        def on_ota(_ch, data):
            q.put_nowait(bytes(data))

        await c.stop_notify(OTA_CTRL)
        await c.start_notify(OTA_CTRL, on_ota)

        piece_count = (len(payload) + PIECE - 1) // PIECE
        state = {"piece": 0}

        async def send_piece(idx):
            start = idx * PIECE
            piece = payload[start:start + PIECE]
            for off in range(0, len(piece), MTU):
                await c.write_gatt_char(OTA_DATA, piece[off:off + MTU], response=False)
                await asyncio.sleep(0.004)

        async def send_ctrl(data):
            await c.write_gatt_char(OTA_CTRL, data, response=False)

        settings = (bytes([0x02, TYPE_PICTURE]) + addr
                    + le32(len(payload)) + crc4 + bytes([0x14]))

        print(f"\n[1] start -> 01 {le32(len(payload)).hex(' ')}   "
              f"({piece_count} pieces)")
        await send_ctrl(bytes([0x01]) + le32(len(payload)))

        done = False
        while not done:
            try:
                r = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                print("   !! timeout waiting for the watch")
                break
            if len(r) < 2:
                continue
            op, st = r[0], r[1]
            if st in (0x3A, 0x00, 0xFF) and op != 5:
                print(f"   <- {r.hex(' ')}   FAILURE status 0x{st:02x}")
                break
            if op == 1:
                print(f"   <- {r.hex(' ')}   -> settings")
                await send_ctrl(settings)
            elif op == 2:
                print(f"   <- {r.hex(' ')}   -> piece 0/{piece_count}")
                state["piece"] = 0
                await send_piece(0)
            elif op == 3:
                sub = r[2] if len(r) > 2 else 0
                if sub == 2:
                    state["piece"] += 1
                    n = state["piece"]
                    if n % 25 == 0 or n == piece_count - 1:
                        print(f"   .. piece {n}/{piece_count}")
                    await send_piece(n)
                elif sub == 4:
                    print(f"   <- {r.hex(' ')}   all pieces in -> check CRC")
                    await send_ctrl(bytes([0x04]))
            elif op == 4:
                print(f"   <- {r.hex(' ')}   CRC ok -> end")
                await send_ctrl(bytes([0x05]))
            elif op == 5:
                print(f"   <- {r.hex(' ')}   *** OTA COMPLETE ***")
                done = True

        print("\nfinished" if done else "\nstopped early")


if __name__ == "__main__":
    asyncio.run(main())
