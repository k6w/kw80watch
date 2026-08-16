#!/usr/bin/env python3
"""Scan for the KW80 over BLE and (optionally) enumerate its GATT table.

READ-ONLY. This script never writes to the watch. It scans, connects, and
reads the GATT structure — nothing more.

    ../.venv/bin/python tools/blescan.py                 # scan only
    ../.venv/bin/python tools/blescan.py --connect       # scan, then enumerate GATT

Hypothesis under test (docs/03, docs/07): the KW80 exposes the vendor "wl"
service 0x1630 with write characteristic 0x1631 and notify characteristic
0x1632. Confirming that pins down which SDK branch drives this watch.

macOS caveat: CoreBluetooth reports a system-generated UUID, not the real
BD_ADDR. The KW80's config has broadcastMac=false, so the MAC is not in the
advertisement either. The `deviceId` needed by the firmware API is therefore
NOT obtainable this way — it would have to come from a GATT command response.
"""
import argparse
import asyncio
import sys

from bleak import BleakClient, BleakScanner

WL_SERVICE = "00001630-0000-1000-8000-00805f9b34fb"
WL_WRITE_CH = "00001631-0000-1000-8000-00805f9b34fb"
WL_NOTIFY_CH = "00001632-0000-1000-8000-00805f9b34fb"

# Other known service families, to identify which branch the watch belongs to.
KNOWN = {
    WL_SERVICE: "wl vendor service (expected for KW80)",
    "00001530-0000-1000-8000-00805f9b34fb": "Nordic Legacy DFU",
    "0000fe59-0000-1000-8000-00805f9b34fb": "Nordic Secure DFU",
    "00000000-0000-0000-6473-5f696c666973": "SiFli service (NOT expected)",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery",
}


async def scan(timeout):
    print(f"scanning {timeout}s ...\n")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    if not found:
        print("nothing found. Is Bluetooth on, and is the watch awake and "
              "disconnected from your phone?")
        return []

    hits = []
    for dev, adv in sorted(found.values(), key=lambda x: -(x[1].rssi or -999)):
        name = adv.local_name or dev.name or "(unnamed)"
        interesting = "KW80" in name.upper() or WL_SERVICE in [
            u.lower() for u in adv.service_uuids
        ]
        mark = " <<< MATCH" if interesting else ""
        print(f"  {adv.rssi:>4} dBm  {name:<28} {dev.address}{mark}")
        if adv.service_uuids:
            for u in adv.service_uuids:
                print(f"              service {u}  {KNOWN.get(u.lower(), '')}")
        if adv.manufacturer_data:
            for cid, data in adv.manufacturer_data.items():
                print(f"              mfr 0x{cid:04x} ({cid}): {data.hex(' ')}")
        if interesting:
            hits.append(dev)
    return hits


async def enumerate_gatt(dev):
    print(f"\nconnecting to {dev.address} ...")
    async with BleakClient(dev) as client:
        print(f"connected: {client.is_connected}\n")
        saw_wl = False
        for svc in client.services:
            note = KNOWN.get(svc.uuid.lower(), "")
            print(f"  service {svc.uuid}  {note}")
            if svc.uuid.lower() == WL_SERVICE:
                saw_wl = True
            for ch in svc.characteristics:
                props = ",".join(ch.properties)
                tag = ""
                if ch.uuid.lower() == WL_WRITE_CH:
                    tag = "  <- wl WRITE"
                elif ch.uuid.lower() == WL_NOTIFY_CH:
                    tag = "  <- wl NOTIFY"
                print(f"      char {ch.uuid}  [{props}]{tag}")

        print("\n=== verdict ===")
        print(f"  wl service 0x1630 present: {saw_wl}")
        print("  -> KW80 uses the `wl` SDK branch" if saw_wl else
              "  -> NOT the wl branch; re-check which SDK path applies")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", action="store_true",
                    help="connect to the first match and enumerate GATT")
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    hits = await scan(args.timeout)
    if args.connect:
        if not hits:
            print("\nno KW80 match to connect to.")
            sys.exit(1)
        await enumerate_gatt(hits[0])


if __name__ == "__main__":
    asyncio.run(main())
