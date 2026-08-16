# 08 — Live BLE / GATT Findings

First contact with the actual hardware, 2026-08-07, from the MacBook via
CoreBluetooth (`bleak` 3.0.2). **Read-only: scan, connect, service discovery.
Nothing was written to the watch.**

Reproduce with `tools/blescan.py --connect`.

## Advertisement

```
KW80#02563    -45 dBm
  service  00006006-0000-1000-8000-00805f9b34fb
  mfr data 0x09ac (2476): 4c 59 31 55 2b 46      # ASCII "LY1U+F"
```

macOS reports a CoreBluetooth UUID (`71DCD961-B873-…`), **not** the BD_ADDR.
Combined with `broadcastMac: false`, the real MAC is unavailable from this
machine. If the API's `deviceId` is the MAC, it cannot be obtained this way — it
would have to come back from a GATT command response.

## GATT table

```
service 00006006  (app constant: DATA1_SERVICE_ID)
    char 00008001  [write-without-response, read]           DATA1_WRITE_CH_ID
    char 00008002  [write-without-response, notify, read]   DATA1_READ_CH_ID
    char 00008003  [write-without-response, read]           DATA2_WRITE_CH_ID
    char 00008004  [write-without-response, notify, read]   DATA2_READ_CH_ID

service 00001530  Nordic Legacy DFU  (app constant: OTA_SERVICE_ID)
    char 00001531  [write-without-response, notify, read]   OTA_WRITE_ID
    char 00001532  [write-without-response, read]           OTA_READ_ID
```

No Device Information service (0x180A), so no manufacturer/model strings to read.

## Hypothesis disproven: it is NOT the `wl` branch

[03-watchface-pipeline.md](03-watchface-pipeline.md) proposed
`com/huawo/sdk/bluetoothsdk/wl/` as the KW80's path, at medium confidence.
**That was wrong.** The `wl` branch uses service `0x1630` with characteristics
`0x1631`/`0x1632` (`BleUUID.WL_SERVICE_ID` etc.). **The watch does not expose
`0x1630` at all.**

Consequences:

- The `wl` packet framing (`WlPacketAssembler`: prefix `0x6F`, suffix `0x8F`,
  min length 6) is **not confirmed** to apply here.
- `WlWatchfaceWidgetWire` and `V10CustomWatchfaceConfig` may still describe the
  right *element vocabulary* — their enums match what the protobuf layout
  suggests — but they are no longer confirmed as this watch's code path.

## What it actually uses

The **generic `DATA1` channel** from `BleUUID.java`, driven by
`com/huawo/sdk/bluetoothsdk/interfaces/task/DataManager.java`. The relevant
command set is therefore `com/huawo/sdk/bluetoothsdk/interfaces/ops/`:

`GetDeviceInfo`, `SetCustomWatchface`, `SetNewCustomWatchface`,
`DeleteWatchface`, `SetWatchfaceName`, `GetDeviceWatchfaceAvailableStorage`,
`GetPAIs`, …

`DataManager.java:301` and `:369` log sends against `0x8003` and `0x8001`
respectively, confirming both write characteristics are in active use.

## The MCU question, reopened

**The watch's own advertisement says Bluetooth company ID `0x09AC` = Ambiq.**

[Ambiq](https://ambiq.com) makes the Apollo family of ultra-low-power MCUs,
extremely common in budget smartwatches.

This **conflicts with the app's device database**, which lists
`mcu: "Realtek"` — see [01-device-profile.md](01-device-profile.md).

| Source | Says | Strength |
|---|---|---|
| Watch's BLE advertisement | Ambiq (0x09AC) | direct from the device |
| HaWoFit device database | Realtek | vendor metadata, and the field only ever gets compared against `"sifli"` |

> **SETTLED LATER — this section's conclusion was wrong.** Firmware analysis
> ([09-watch-os.md](09-watch-os.md)) found `UPPER_STACK` and the RTL87xx SDK
> string `Error! Please implement your ISR Handler for IRQ %d!` inside the
> sibling firmware. **It is Realtek.** The `0x09AC` company ID is a copy-pasted
> advertising byte, which ODMs routinely leave unchanged. The app database was
> right; calling Ambiq "the better guess" here was an over-correction.

What remains solid regardless: **not SiFli**, editor family 2, `HA01_HW`.

Also unresolved: the manufacturer payload `4c 59 31 55 2b 46` (`"LY1U+F"`).

## Nordic Legacy DFU is live

`0x1530` is the **Nordic Legacy DFU** service — a publicly documented protocol
with open-source tooling (`nrfutil`, `adafruit-nrfutil`).

Relevant property: Legacy DFU generally validates only a CRC and an init packet,
**not a cryptographic signature** — which is precisely why Nordic deprecated it
in favour of Secure DFU. If this is a genuine Legacy DFU implementation, custom
firmware is more plausible than the earlier Realtek assumption suggested.

**Not yet verified, and not to be tested casually.** The standing rules in
[04-dfu-and-firmware.md](04-dfu-and-firmware.md) still apply: no writes to DFU
until a stock firmware image exists as a restore path.

## Next step (done — see the update below)


---

# Update: bound, and the protocol frame corrected

## Frame format (corrected)

Earlier this doc described byte 5 as a "sub-command". The bind commands make the
real structure clear:

```
request : 6F <cmd> <dir> <len:LE16> <payload...> 8F
          dir 0x70 = get, 0x71 = set/action
reply   : 6F <cmd> 0x80 <len:LE16> <data...> 8F      data response
          6F 0x01 0x81 02 00 <origcmd> <status> 8F   status response
          status 0x00 = OK, 0x02 = UNSUPPORTED
```

So what looked like a "sub-command byte" is simply the first byte of a 1-byte
payload. And `0x81` replies are **not** errors by definition — `6f 01 81 02 00
93 00 8f` means "command 0x93: status OK".

## Factory reset

Pressing reset on the watch changed **only** `bindstate` `01` -> `00`. Firmware
version, deviceId and productCode were unchanged, confirming a reset does not
reinstall firmware — so it is no route to obtaining a firmware image.

## Bind succeeded

`tools/blebind.py`, run while unbound:

```
GetBindState (before)  -> 00
StartBind              6F 93 71 01 00 01 8F              -> status OK
StartConfirmBind       6F 93 71 11 00 00 <16-byte id> 8F -> status OK
EndBind                6F 94 71 01 00 01 8F              -> status OK
GetBindState (after)   -> 01     BOUND
```

The watch is now bound to this machine with client id `KW80MACCLIENT01`.
Reversible by factory-resetting the watch or re-pairing in HaWoFit.

## Full device dump

`tools/bledump.py` runs all **80 parameterless GET commands** extracted verbatim
from the app (`artifacts/get-commands.json`); replies in
`artifacts/device-dump.json`. Highlights:

| Query | Value |
|---|---|
| `GetDeviceID` | `HWHA0122032101002563` |
| `GetDeviceType` | `HA01_HW` |
| `GetFirmwareVersion` | `V1.0.1R0.2T0.5H0.2B01` |
| `GetVersionForLS` | `00 14 aa 58 02` |
| `GetBindState` | `01` (bound) |
| `GetBattery` | `0x57` = 87 % |
| `GetBrightness` | `0x50` = 80 |
| `GetDisplayDuration` | `0a 00` = 10 s |
| `GetFeatureSwitches` | `f8 93 00 00` |
| `GetHeartrateAlarm` | `b4 32 00` = max 180, min 50 |
| `GetGoal` | `46 00 01 5e 01 01 05 00 01 08 00 01 3c 00 01` |
| `GetWatchfaceIDs` | `00 00 00 00 00` (none installed?) |
| `GetDevicePasscode` | `0x10` |

43 of 80 returned data; the rest replied `UNSUPPORTED` or stayed silent.

**No sensor addresses.** The protocol exposes no I2C/register-level access —
that information exists only in firmware.

## Hardware extraction from SWC01: partial

| Target | Status |
|---|---|
| QSPI flash init | **found** — `FUN_020a97ca` (810 bytes), via `flash switch 4bit success` |
| UART console init | **found** — `FUN_020ab5c4` (184 bytes), via `DMA uart_tx_ch_num = %d` |
| Display init sequence | **not found yet** |
| Sensor I2C addresses | **not found yet** |

Two approaches failed and are recorded so they are not repeated:

1. **Scanning for MIPI-DCS opcode clusters** (0x11/0x29/0x36/0x3A...) produced
   351 "candidate regions", all false positives — those bytes are common ARM
   Thumb opcodes (`0x29` = CMP etc.).
2. **String anchors for `Gsensor` / `G-SENSOR` / `FLASH ID`** have **no code
   references**. They sit above 0x021e0000, i.e. in the resource region — they
   are factory-test *UI labels*, not driver debug strings.

The workable route is via LVGL: find `lv_disp_drv_register`, take the
`flush_cb`, and follow it down to the SPI/QSPI write primitive. The panel init
table will be a data blob referenced near there. That is a substantial piece of
work, not a quick grep.

## Write path verified

`SetBrightness` (`6F 07 71 01 00 <level> 8F`) used as a safe, reversible probe:

```
read      -> 80
set 0x20  -> status OK
read      -> 40      (watch quantises brightness to 20% steps)
set 0x50  -> status OK
read      -> 80      (exactly restored)
```

**Writes work and are confirmable by readback.** Binding was what enabled this.

## Command support on firmware V1.0.1

Binding did **not** widen the command set. This 2022 firmware implements only a
subset of the app's 257 operations — the app targets 213 models, this build is
one of the older ones.

| Command | ID | Status |
|---|---|---|
| `GetWatchfaceIDs` | 0x1E | **supported** — returns `00 00 00 00 00` |
| `SetBrightness` / `GetBrightness` | 0x07 | **supported** |
| `GetBindState` / bind flow | 0x93/0x94 | **supported** |
| `GetWatchfaceID` | 0x0F | UNSUPPORTED |
| `GetWatchfaceNameList` | 0x11 | UNSUPPORTED |
| whole `0x41` family (SN, protocol ver, watchface ver, album/music storage, device features) | 0x41 | UNSUPPORTED |

## Custom watchface protocol

From `SetCustomWatchface.java` / `SetNewCustomWatchface.java`. **Command `0x1E`
— the same ID as the working `GetWatchfaceIDs`**, so the set direction is very
likely supported too.

```
SetCustomWatchface     6F 1E 71 <len:LE16> 02 <id:4> <widgets...> 8F
SetNewCustomWatchface   6F 1E 71 <len:LE16> 03 <id:4> <widgets...> 8F
```

Per widget, appended in order:

```
position block (skipped for HourHand/MinuteHand/SecondHand/Dial):
    <idx> <type> 00 04 <x:LE16> <y:LE16>
base:
    <idx> <type>
colour (if set):
    02 04 <colour, byte order reversed>
style (if >= 0):
    <idx> <type> 03 01 <style>
```

`type` uses the `V10CustomWatchfaceConfig` / `WlWatchfaceWidgetWire` enum:
CLOSE=0, TIME=1, DATE=2, HEARTRATE=3, STEP=4, DISTANCE=5, CALORIE=6,
ACTIVE_TIME=7, WEATHER=8, SLEEP=9, BATTERY=10.

**Note this is the built-in *dial builder* path** — placing data elements at
coordinates over a background — not the `.bin` upload path documented in
[07-binary-format.md](07-binary-format.md). Those are two different mechanisms.
