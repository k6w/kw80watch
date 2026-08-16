# 06 — Status, Assumptions, Blockers

Last updated: 2026-08-07

## Original goal

A custom watchface SDK for the KW80, a web-based editor (elements, fonts,
images, GIFs), and a marketplace where others can install community faces.

## Decomposition

| # | Phase | State |
|---|---|---|
| 1 | Reverse-engineer the watchface format | **~70%** — container + layout solved, image codec open |
| 2 | SDK: pack/unpack library | not started |
| 3 | Delivery: BLE push to watch | **unblocked** — the Mac can talk to the watch directly, see [08](08-ble-gatt.md) |
| 4 | Editor: web canvas app | not started |
| 5 | Marketplace: accounts, upload, browse, install | not started |

## Established facts

- KW80 = 368×448 rectangle, corner radius 55, **`productCode: HA01_HW`**,
  `watchfaceEditor: 2`. **MCU disputed:** app DB says Realtek, the watch's own
  BLE advertisement says Ambiq (0x09AC). See [08](08-ble-gatt.md). "Not SiFli"
  holds regardless, and nothing downstream depends on the distinction.
- **GATT confirmed live:** data channel `0x6006` (`0x8001` write / `0x8002`
  notify), plus **Nordic Legacy DFU** at `0x1530`.
- **BLE only** (`hasBT: false`). No SPP. All transfers via GATT.
- No album-transmission channel — imagery rides inside the watchface payload.
- HaWoFit covers 213 models; **17 share the KW80's editor-2 family**.
- **The vendor watchface store needs no authentication.** 49 official KW80 faces
  downloaded and MD5-verified — see [07-binary-format.md](07-binary-format.md).
- **Container format solved:** 20-byte header, image blob, protobuf layout
  descriptor, `UCPDOLWF` trailer. `filesize == S1 + S2 + 8` holds for all 49.
- **Layout is protobuf** — decodable and re-encodable with standard libraries.
  Element positions, sizes, and glyph references are already readable.
- Section 1 entropy is 4.2–5.1 bits/byte, so **not encrypted**.
- A wireless firmware update path exists; the phone-side client does no
  signature verification (MD5 integrity only).
- **Live device readout obtained** — see `artifacts/device-readout.md`.
  Battery 90 %, bound, firmware `V1.0.1R0.2T0.5H0.2B01`, `productCode` confirmed
  as `HA01_HW` by the watch itself.
- **Command protocol decoded:** `6F <cmd> 70 01 00 <sub> 8F` request,
  `6F <cmd> 80 <len×2> <payload> 8F` response. Queries work without any session
  handshake even while the watch is bound to the phone.
- **No stock firmware exists for the KW80.** The upgrade API is open but returns
  `data: null` for `HA01_HW` at every version claim. A sweep of all 213 product
  codes found firmware for **9 other models**, including two in the KW80's exact
  family (SWC01, SWC05) — **plaintext, not encrypted**.
- **The OS is identified:** LVGL 8.x + an MVP PageManager framework, ~100 UI
  pages, on **Realtek RTL87xx**. See [09-watch-os.md](09-watch-os.md).
- **MCU settled as Realtek** by firmware strings (`UPPER_STACK`, the RTL87xx ISR
  message). The Ambiq BLE company ID was a red herring.

## Corrected along the way

**The KW80 was initially identified as SiFli SF32LB. It is not SiFli.** The
mistake came from finding `com.sifli.*` in the APK before establishing that
HaWoFit is a multi-vendor app. Consequences: the QuickJS + LVGL engine,
`libezip.so` encoding, the SiFli DFU image-ID map, and the open-source SiFli-SDK
custom-firmware route **all do not apply** to this watch.

**It was then called Realtek on the app database's say-so. That is now
disputed** — the watch advertises Bluetooth company ID Ambiq. See
[08](08-ble-gatt.md).

**The `wl` SDK branch was proposed as its code path. Disproven** — the watch
exposes `0x6006`, not `0x1630`.

**Pulling stock firmware was initially described as network-only. It isn't** —
`DeviceRemote.upgradesRequestBody()` needs `deviceId`, `currentVersion`, and
`currentBuild`, all of which come from a paired watch, plus an auth token. This
was a misreading corrected by reading the code, **not** something discovered by
attempting it: the S25 has never been available, so no firmware pull was ever
tried.

## The one thing that decides the editor's architecture

**The section-1 image codec is undecoded.** Until it is:

- reading and rewriting *layout* (positions, sizes, element types) is possible **now**
- generating *new imagery* is not

If the codec turns out to need a native library the way family 4 needs
`libezip.so`, the editor needs a server-side encode step rather than pure
client-side export. Nothing else in the design changes.

## Assumptions not yet verified

| Assumption | Confidence | How to check |
|---|---|---|
| ~~`wl/` is the KW80's watchface path~~ | **DISPROVEN** | watch exposes `0x6006`, not `0x1630`. It uses the generic `DATA1` channel — see [08](08-ble-gatt.md) |
| Protobuf field 5 is the element type | low | conflicts with the 0–10 enum range — see [07](07-binary-format.md) |
| All 17 editor-2 models share this format | low | fetch their catalogues and compare headers |
| Header field 0x04 is a checksum | low | correlate against section-1 contents |

## Still blocked on the Galaxy S25

- BLE HCI snoop capture of the **official app performing a real install** — the
  only remaining reason to want the phone.

**No longer blocked:** everything else. The Mac talks to the watch, queries
return real data, and the cloud APIs need no authentication.

| Once blocked on the S25 | Now |
|---|---|
| `deviceId` | `HWHA0122032101002563`, read over BLE |
| `currentVersion` / `currentBuild` | `1.0.1` / `1`, read over BLE |
| `customerCode` | `"Huawo"`, from `EnvironmentImpl.java:12` |
| auth token for firmware API | **not needed** — endpoint is open |

## Not blocked — doable now

1. **Decode the section-1 image codec.** Validation loop: decode a background,
   compare against the catalogue `thumbnail` PNG for that face. This is the
   critical path.
2. **Fetch catalogues for the other 16 editor-2 models** and diff headers to see
   whether the format generalises.
3. **Resolve the protobuf schema** — map field 5 and the `0x62` variant by
   correlating decoded layouts against face thumbnails.
4. **Extract `customerCode`** from app build constants.

## Immediate next action

Extract the `DataManager` packet framing and `GetDeviceInfo` command bytes, then
send that query over `0x8001` and read `0x8002`. It returns firmware version and
build — two of the three fields the firmware download API needs.

Requires **writing** to the watch (a query, not a modification, on the normal
data channel rather than DFU). Needs approval per rule 3 below.

## Standing safety rules

1. Never flash a bootloader image.
2. ~~No writes until stock firmware is downloaded~~ → **no firmware writes at
   all.** The vendor publishes no image for this model, so there is no restore
   path and a failed flash is unrecoverable. Revisit only if the firmware can be
   dumped off the device by another route.
3. Confirm every watch write individually, in advance.
4. Do not reuse SiFli DFU image IDs here — this is not a SiFli device.
