# KW80 Watchface Project

Goal: a custom watchface SDK, a web-based editor, and a marketplace for the
**KingWear KW80** smartwatch (paired via the **HaWoFit** app).

**Status: WORKING.** A custom-generated watchface has been encoded on the Mac,
uploaded over BLE, and is displayed on the KW80. No firmware was ever flashed.

```bash
python3 tools/wfimage.py  face.png out.bin     # any image -> watchface blob
python3 tools/wfupload.py face.png --send      # upload it to the watch
```

Container, header, layout descriptor, image codec and OTA transport are all
solved. See [07-binary-format.md](docs/07-binary-format.md) for the container
and [10-watchface-capabilities.md](docs/10-watchface-capabilities.md) for everything
a watchface can express.

## Documentation

| Doc | Contents |
|---|---|
| [00-claims-register.md](docs/00-claims-register.md) | **READ FIRST — every claim classified by evidence strength** |
| [01-device-profile.md](docs/01-device-profile.md) | What the KW80 actually is — hardware, screen, feature flags |
| [02-app-teardown.md](docs/02-app-teardown.md) | HaWoFit APK structure and how it was analysed |
| [03-watchface-pipeline.md](docs/03-watchface-pipeline.md) | Watchface formats — the two editor families |
| [04-dfu-and-firmware.md](docs/04-dfu-and-firmware.md) | Firmware update path, brick risks, safety rules |
| [05-cloud-api.md](docs/05-cloud-api.md) | Huawo cloud API — hosts, endpoints, auth |
| [06-status-and-next-steps.md](docs/06-status-and-next-steps.md) | What's proven, what's assumed, what's blocked |
| [07-binary-format.md](docs/07-binary-format.md) | **The KW80 `.bin` watchface format** |
| [08-ble-gatt.md](docs/08-ble-gatt.md) | **Live GATT table from the real watch** |
| [09-watch-os.md](docs/09-watch-os.md) | **The watch OS — LVGL 8 + MVP, ~100 pages, from sibling firmware** |
| [10-watchface-capabilities.md](docs/10-watchface-capabilities.md) | **Complete watchface reference — every element, every data source, from 548 vendor faces** |

Live device data: [`artifacts/device-readout.md`](artifacts/device-readout.md)

## Tools

```bash
# make and install a watchface  <- the working pipeline
./.venv/bin/python tools/wfimage.py  face.png out.bin
./.venv/bin/python tools/wfupload.py face.png --send

# device
./.venv/bin/python tools/blescan.py --connect     # scan + enumerate GATT
./.venv/bin/python tools/blequery.py all          # 80 read-only queries
./.venv/bin/python tools/bledump.py               # dump every queryable value
./.venv/bin/python tools/blebind.py               # bind the watch to this machine

# analysis
python3 tools/fetch_samples.py [HA01_HW]          # official faces + MD5 verify
python3 tools/wfdump.py artifacts/samples/WF01.bin
python3 tools/fw_sweep.py                         # check for published firmware
```

## Layout

```
README.md
docs/                        analysis write-ups
tools/                       fetch_samples.py, wfdump.py, blescan.py,
                             blequery.py, fw_sweep.py, ghidra_scripts/
artifacts/
  AppConfig.json             full 213-model device database, pulled from the APK
  kw80-productconfig.json    just the KW80 entries
  ha01hw-watchfaces.json     catalogue of the 49 official KW80 faces
  samples/                   those 49 .bin files, MD5-verified
  Localizable.url            AMap server list (incidental)
work/
  xapk/                      extracted XAPK — base APK + split APKs
  dex/                       raw classes*.dex
  jadx/                      decompiled Java (5402 files)
  jadx.log
hawofit-2-5-2.xapk           source bundle (HaWoFit v2.5.2)
```

`work/` is regenerable — see [02-app-teardown.md](docs/02-app-teardown.md) for the commands.

## The one-paragraph summary

The KW80 is a BLE watch, 368×448 rectangular, product code `HA01_HW`. HaWoFit is
a single app supporting **213 different watch models** across four MCU vendors,
so most of what's inside it does not apply to the KW80. The KW80 uses **watchface
editor family 2**; the richer JavaScript/LVGL watchface engine found in the app
belongs to **editor family 4** (SiFli models) and is **not** available on this
watch. **MCU: probably Ambiq Apollo3 Blue Plus** — the watch advertises Bluetooth
company ID `0x09AC` (Ambiq) and retail listings say "Apollo 3 Plus". An earlier
claim of "Realtek, settled" was **retracted**: it rested on firmware strings from
SWC01, a different hardware family. See
[00-claims-register.md](docs/00-claims-register.md).

The vendor's watchface store turned out to need **no authentication**, so 49
official KW80 faces were downloaded as format samples. From those the container
format was solved: a 20-byte header, an image blob, a **protobuf** layout
descriptor, and a `UCPDOLWF` trailer.

The image codec turned out to live in the **phone app**, not the firmware —
`ImageUtil.rgb888ToRGB555Ex`, an ordered-dithered RGB565 encoder wrapped in a
standard LVGL 8 image header. Upload goes over the OTA channel tagged
`Picture(4)`, driven by a notification state machine on `0x1531`.

**Both are implemented and confirmed working on real hardware.**

Firmware can be updated wirelessly and no signature checking exists in the
phone-side client, but no firmware has ever been flashed here and there is no
stock KW80 image to restore from — so that route stays closed.

## Safety rules (standing)

1. **Never send OtaDataType `Platform(1)` or `Bootloader(11)`.** Watchface
   uploads use `Picture(4)` and cannot touch firmware. There is no stock KW80
   image anywhere, so a bad firmware write is unrecoverable.
2. **No firmware flashing at all**, for the same reason — no restore path exists.
3. **Every new class of write to the watch gets confirmed first.**
