# 07 — KW80 Watchface Binary Format (`.bin`)

Reverse-engineered from **49 official KW80 watchfaces** downloaded from the
vendor CDN. All 49 MD5s verified against the catalogue. Samples in
`artifacts/samples/`, catalogue in `artifacts/ha01hw-watchfaces.json`.

**Status: SOLVED.** Container, header, layout descriptor and image codec all
recovered and validated. See the final section — the codec was in the phone app,
not the firmware. A working encoder is at `tools/wfimage.py`.

## How the samples were obtained

The vendor watchface store needs **no authentication**:

```bash
curl "https://api.huawo-wear.com/api/v1/products/HA01_HW/watchfaces?customerCode=&locale=en"
```

`productCode` matters: `HA01_HW` returns **49 faces**; `HA01` returns **0**.
Strong evidence the KW80 is the `HA01_HW` variant.

Each record gives `bin` (CDN path), `binMd5`, `thumbnail`. Files download from
`https://static.huawo-wear.com/files/<bin>`.

Reproduce with `tools/fetch_samples.py`.

## Top-level layout

```
+--------------------------------------------------+
| 0x00  header (20 bytes)                          |
+--------------------------------------------------+
| 0x14  image resource blob                        |  } section 1, S1 bytes total
|       (starts with constant 18 d0 62 1b)         |  } (includes the header)
+--------------------------------------------------+
| S1    protobuf layout descriptor                 |  } section 2, S2 bytes
+--------------------------------------------------+
| S1+S2 magic "UCPDOLWF" (8 bytes)                 |
+--------------------------------------------------+
```

**Invariant, holding for all 49 samples:** `filesize == S1 + S2 + 8`

## Header (20 bytes, little-endian) — confirmed from firmware

**Source: `FUN_020e593c` in the SWC01 firmware, decompiled in Ghidra.** This
supersedes an earlier guess that read fields 3 and 4 as sizes. The firmware
converts fields 0, 1 and 3 to pointers by adding the buffer base, so **they are
offsets**; fields 2 and 4 are used as raw values.

```c
// FUN_020e593c, reformatted
tag = *(u32 *)(buf + len - 4);
if (memcmp(&tag, "OLWF", 4) == 0) {
    g->off1  = buf[0] + (int)buf;    // offset -> pointer
    g->off2  = buf[1] + (int)buf;    // offset -> pointer
    g->cnt   = buf[2];               // raw
    g->off3  = buf[3] + (int)buf;    // offset -> pointer
    g->len3  = buf[4];               // raw
    if (g->len3 <= 0x800 && g->cnt <= 0x3f8) { /* accept */ }
}
```

| Offset | Field | Meaning | Observed |
|---|---|---|---|
| 0x00 | `off1` | **offset** to section 1 | always `20` (immediately after header) |
| 0x04 | `off2` | **offset** to section 2 | 19,505 – 77,167 |
| 0x08 | `cnt` | count/table size, **≤ 0x3f8 (1016)** | 4 – 340, always ≡ 0 mod 4 |
| 0x0C | `off3` | **offset** to section 3 (protobuf) | |
| 0x10 | `len3` | **length** of section 3, **≤ 0x800 (2048)** | 80 – 1145 |

Firmware-enforced limits: `cnt <= 0x3f8` **and** `len3 <= 0x800`. A file
violating either is rejected.

The earlier `filesize == S1 + S2 + 8` invariant still holds, now explained:
`off3 + len3 + 8 == filesize`, because section 3 is last and the trailer is 8
bytes.

**Validated: all 49 samples pass** `off1 == 20`, `20 < off2 < off3 < filesize`,
`off3 + len3 + 8 == filesize`, and both limits. Zero failures.

`cnt` is always a multiple of 4, suggesting a 4-byte-entry table
(`cnt / 4` = 1 – 85 entries). Which table it indexes is **not yet confirmed**.

At offset `0x14` every file begins with the constant 4 bytes `18 d0 62 1b`.

Trailer magic: `55 43 50 44 4f 4c 57 46` = ASCII `UCPDOLWF`. **Only the last 4
bytes matter** — the firmware compares just `OLWF`.

## Three file types share this loader

The same firmware function dispatches on the trailing 4-byte tag:

| Tag | Address | Handling |
|---|---|---|
| `OLWF` | `DAT_020e5bd0` | watchface — the format above |
| `FACE` | `DAT_020e5bd8` | a second watchface type; sets a pointer at `buf + 0x50804` (fixed-size payload) |
| `SOCIAL` | `s_SOCIAL_020e5be0` | social-app icon set; 6-byte compare, and the buffer must equal `FUN_0210bdae()`'s return |

The tag table sits at file offset `0x3cbd4` → address `0x020e5bd0`.

## Section 1 — SOLVED: an LVGL 8 image descriptor

**The word at `off1` is a standard LVGL 8 `lv_img_header_t`.** Confirmed from
firmware (`FUN_0215508a`, LVGL's built-in `info_cb`, which does exactly this bit
extraction and accepts `cf` in 4..27), and validated against data.

```c
typedef struct {          // 4 bytes, little-endian bitfield
    uint32_t cf          : 5;   // bits  0-4   colour format
    uint32_t always_zero : 3;   // bits  5-7   must be 0
    uint32_t reserved    : 2;   // bits  8-9
    uint32_t w           : 11;  // bits 10-20
    uint32_t h           : 11;  // bits 21-31
} lv_img_header_t;
```

### Validation: 49/49

Every sample has a valid header at `off1`:

| Field | Value | Cross-check |
|---|---|---|
| `cf` | **24** = `LV_IMG_CF_USER_ENCODED_0` | vendor-defined format |
| `always_zero` | 0 | correct in all 49 |
| `reserved` | 0 | correct in all 49 |
| `w` × `h` | **180 × 219** | **exactly** `thumbnailWidth`/`thumbnailHeight` from the device DB |

So **section 1 is the watchface thumbnail**, and the 180×219 match against the
device database is independent confirmation the header layout is right.

Compression, WF01:

| | raw RGB565 | stored | ratio |
|---|---|---|---|
| thumbnail 180×219 | 78,840 | 20,423 | 3.86× |
| screen 368×448 | 329,728 | 78,449 | 4.20× |

Consistent ~4:1 in both sections — `USER_ENCODED_0` is a compressed RGB565-class
format.

### The decompressor is not LVGL's

`lv_img_decoder_init` (`FUN_021552dc`) registers exactly **one** decoder — the
stock built-in:

```c
decoder[0] = 0x215508b;   // info_cb        FUN_0215508a
decoder[1] = 0x2154d1f;   // open_cb        FUN_02154d1e
decoder[2] = 0x2154773;   // read_line_cb   FUN_02154772
decoder[3] = 0x215472d;   // close_cb       FUN_0215472c
```

Both `open_cb` and `read_line_cb` handle only `cf` 4/5/6 (TRUE_COLOR variants)
and 0xb–0xe (ALPHA). **Neither handles `cf = 24`.**

Therefore the watchface code **decompresses into RAM before handing the image to
LVGL**, rewriting the header to a plain `TRUE_COLOR` descriptor. The vendor
decompressor lives in the watchface render path, not in the LVGL decoder
registry.

**That was the last unknown — and it turned out not to matter.** See the final
section: the app sends `cf=4` raw RGB565, which the stock LVGL decoder handles
natively. The `cf=24` compressor is only used by the vendor's own store files,
and we never need to produce one.

### Note on brute-force scanning

Scanning the file for "plausible LVGL headers" is useless — the constraint is
weak enough that ~1 in 50 random words passes, yielding 104,625 false candidates
across 49 files. Only headers at known offsets (`off1`) are meaningful.

`off2` does **not** hold a bare image header (48/49 fail), so section 2 has its
own container structure, still undetermined.

## Section 1 — earlier notes

Entropy 4.2 – 5.1 bits/byte. **Not encrypted** (encrypted data would sit near
8.0). Consistent with compressed or structured image data.

Sizes span 83 KB to 1.24 MB against a 368×448 screen. Uncompressed RGB565 for
one full screen would be 329,728 bytes, so smaller files are definitely
compressed and larger ones hold multiple images.

**Not yet decoded.** A tested-and-rejected hypothesis: a 448-entry uint16
row-length table at offset 20 or 24 — the sums come out 30× too large.

Data immediately after the header reads as smoothly-varying little-endian
uint16 values (`0x0047, 0x0045, 0x003d, 0x003d, 0x003b …`), consistent with
RGB565 pixels of a dark image. Whether that's raw or lightly compressed is
undetermined.

## Section 2 — protobuf layout descriptor

Standard protobuf wire format. Multi-byte field tags (`a8 01` = field 21,
`b0 01` = field 22, `b8 01` = field 23) confirm it beyond doubt.

Decoded structure — repeated field 1, each holding one element variant
(a `oneof`), plus a trailing `field 5`:

```
message Watchface {
  repeated Element elements = 1;
  uint32 field5 = 5;          // = 1 in samples
}

message Element {                     // exactly one of:
  Background bg      = 4;
  Textish    text    = 5;
  Numeric    numeric = 6;
  Glyphs     glyphs  = 5;   // (0x2a) seen in WF28 — needs disambiguation
  Complex    complex = 12;  // (0x62) large 95-byte variant in WF04/WF28
}
```

Confirmed sub-fields on the numeric variant (field 6):

| Field | Meaning | Evidence |
|---|---|---|
| 1 | resource index list | 10-byte payload; in WF28, bytes `14 15 16 17 18 19 1a 1b 1c 1d` = indices 20–29, i.e. **glyphs 0–9** |
| 3 | position `{f1: x, f2: y}` | WF01 values (91, 251), (24, 57), (24, 152) — all inside 368×448 |
| 5 | element type / data source | 12, 13, 17 |
| 21 | width | 18, 54 |
| 22 | height | 26, 76 |
| 23 | constant 25 | colour depth or render mode |

In WF28, field 5 (`0x2a`) carries an 11-index list `02 … 0c` — eleven glyphs,
consistent with digits 0–9 plus a separator for a clock.

### Why this matters

The layout is a **decodable and re-encodable structure**, not an opaque blob.
Element positions, sizes, and glyph-set references can be read and rewritten
with any protobuf library. For an editor, that's the whole ballgame — placing
and moving elements is tractable *today*.

The remaining hard part is the image codec in section 1.

## Cross-reference: the app's own element enums

`WlWatchfaceWidgetWire` and `V10CustomWatchfaceConfig` share one element
numbering, almost certainly the same one used in protobuf field 5:

| Value | Element |
|---|---|
| 0 | CLOSE (none) |
| 1 | TIME |
| 2 | DATE |
| 3 | HEARTRATE |
| 4 | STEP |
| 5 | DISTANCE |
| 6 | CALORIE |
| 7 | ACTIVE_TIME |
| 8 | WEATHER |
| 9 | SLEEP |
| 10 | BATTERY |

`V10CustomWatchfaceConfig` adds, for user-made faces:

- `displayMode`: SINGLE=1, SEQUENCE=2, RANDOM=3
- `pointerStyle`: NONE=0, 1, 2, 3
- `position`: TOP=1, MIDDLE=2, BOTTOM=3
- `textColorRgb`, `bgCount`, `coverIndex`
- `elements`: list of `{type, x, y}`

Note the observed field-5 values (12, 13, 17) **exceed** this 0–10 range, so
either field 5 is not the element type, or store-built faces use a wider
vocabulary than user-built ones. **Unresolved.**

## Open questions, ranked

1. **The section-1 image codec.** Blocks everything visual. Validation path:
   decode a background and compare against the catalogue `thumbnail` PNG.
2. **Header fields at 0x04 and 0x08.** Likely a checksum and a resource count;
   a writer must reproduce both correctly.
3. **The `0x62` (field 12) element variant** — 95 bytes, present in WF04/WF28,
   with nested RGB-looking triples (`08 ff 01 10 ff 01 18 ff 01` = 255,255,255).
   Probably a styled/analogue element.
4. **Whether field 5 is the element type**, given the range conflict above.
5. **Whether the other 16 editor-2 models share this format.**

---

# SOLVED: the image codec — and it was never in the firmware

Hours were spent hunting a decompressor through the SWC01 firmware. **The codec
is in the phone app, in readable Java**:
`com.huawo.sdk.bluetoothsdk.interfaces.utils.ImageUtil`.

Found by following `CustomWatchfaceHandler.otaCustomWatchface()`, which is the
app's real custom-watchface upload path.

## `rgb888ToRGB555Ex` — misnamed, it emits RGB565

```java
d = ((y & 7) << 3) + (x & 7);                       // 8x8 ordered dither index
v = (min(blue  + B[d], 255) >> 3)                   // blue  5 bits, 0-4
  | (min(red   + R[d], 255) >> 3) << 11             // red   5 bits, 11-15
  | (min(green + G[d], 255) >> 2) << 5;             // green 6 bits, 5-10
out[(y*w + x)*2]     = (v >> 8) & 0xff;             // BIG-ENDIAN
out[(y*w + x)*2 + 1] =  v       & 0xff;
```

Three 64-entry (8x8) dither matrices, one per channel, copied verbatim into
`tools/wfimage.py`. Output is **2 bytes/pixel, uncompressed**.

## `getHead` confirms the LVGL header

```java
private static byte[] getHead(int w, int h) {
    return longToByteArray(((w << 10) | (h << 21)) + 4, 4);
}
```

Exactly the `lv_img_header_t` layout derived from firmware — with `cf = 4`
(`LV_IMG_CF_TRUE_COLOR`).

### The decisive cross-check

`tools/wfimage.py` emits a thumbnail header of **`0x1b62d004`**.
Every one of the 49 store watchfaces has **`0x1b62d018`** at offset 20.

```
0x1b62d004   cf=4  (TRUE_COLOR,      raw)        <- our encoder
0x1b62d018   cf=24 (USER_ENCODED_0,  compressed) <- store files
             ^^^^^^^^ identical: w=180, h=219
```

They differ **only in the colour-format field**. The unexplained constant
`18 d0 62 1b` at offset 20 is simply `getHead(180, 219)`.

So the two producers differ only in compression:

| Producer | `cf` | Pixels |
|---|---|---|
| App custom watchface | 4 | raw RGB565, ~4x larger |
| Vendor store `.bin` | 24 | compressed ~4:1 |

**We do not need the compressor.** Raw `cf=4` is what the app itself sends, and
the firmware's built-in LVGL decoder handles `cf=4` natively — which is exactly
why no vendor decoder is registered in `lv_img_decoder_init`.

## Container produced by the app

From `ImageUtil` lines 115-122 plus `CustomWatchfaceHandler`:

```
[4-byte LVGL header  (w,h,cf=4)][ main pixels  ]
[4-byte LVGL header (tw,th,cf=4)][ thumb pixels ]
[crc16_lo][crc16_hi][id]["UFACE"]                  <- 8-byte trailer
```

Note `ImageUtil` line 116: `h == 448 ? 219` — the KW80's exact screen and
thumbnail heights, hardcoded.

### The trailer tags finally make sense

The firmware's tag table (`OLWF` / `FACE` / `SOCIAL`) matches the **last 4
bytes** of each producer's 5-char magic:

| Producer | 5-char magic | last 4 = firmware tag |
|---|---|---|
| App custom watchface | `UFACE` | **`FACE`** |
| Vendor store file | `...OLWF` | **`OLWF`** |

Both use the same `[3 bytes][5-char magic]` trailer shape.

## Working encoder

`tools/wfimage.py` converts any image to this format:

```
$ python3 tools/wfimage.py input.png out.bin
wrote out.bin  408,584 bytes
  main  header 0x3805c004 -> cf=4 w=368 h=448
  thumb header 0x1b62d004 -> cf=4 w=180 h=219
  trailer 92 96 00 55 46 41 43 45  = ...UFACE
  size check: 408,584 == 408,584  True
```

Remaining unknown: **the transport**. `CustomWatchfaceHandler` uploads this blob
via `BluetoothSDK.getOtaAddressBy(id)` then an OTA data transfer — *not* the
`0x1E` command. That explains why `SetCustomWatchface` alone (`0x1E`) returned
OK but changed nothing: `0x1E` sets only the **layout**; the **image** goes over
the OTA channel.

## The upload transport — it is the DFU service

`OtaControl` writes to:

```java
BluetoothSDK.writeData(b, BleUUID.OTA_SERVICE_ID, BleUUID.OTA_WRITE_ID, ...)  // 0x1530 / 0x1531
BleManager.write(dev,   BleUUID.OTA_SERVICE_ID, BleUUID.OTA_READ_ID,  ...)    // 0x1530 / 0x1532
```

`OTA_SERVICE_ID = 0x1530` — the **Nordic Legacy DFU service**. So watchface
image upload and firmware flashing **share one transport**. What separates them
is a type byte:

```java
enum OtaDataType {
    Platform(1), TouchPanel(2), Heartrate(3), Picture(4),
    AGPS(6), Patch(10), Bootloader(11), Unknown(255)
}
```

Watchface images go as **`Picture(4)`**. Firmware is `Platform(1)`; the
unrecoverable one is `Bootloader(11)`.

### Actual sequence — read in full from `OtaControl`

**`EnterOta` is NOT part of this path.** It appears only at
`BluetoothSDK.java:1791` as a separate API used for firmware OTA.
`CustomWatchfaceHandler` calls `getOtaAddressBy(id)` then `BluetoothSDK.ota()`
-> `OtaControl.upload()`, which begins writing immediately. **The watch does not
reboot into OTA mode for a picture upload** — it stays in normal firmware.

```
0. GetOtaAddress(id)     6F 1E 70 05 00 01 <id:LE32> 8F      data channel, cmd 0x1E (supported)

   then, all on service 0x1530:
1. -> 0x1531   01 <total_len:LE32>                            start
2. -> 0x1531   02 <type> <addr:4> <len:LE32> <crc32:4> 14     settings; type = 4 (Picture)
3. -> 0x1532   data in 128-byte chunks, 20 per batch,
               taken from 2048-byte pieces                    payload
4. -> 0x1531   04                                             verify CRC
5. -> 0x1531   05                                             end
```

Constants from `OtaControl` / `OtaData`: `sendMTU = 128`,
`sizeOfPiece = 2048`, `PACKAGE_COUNT_CALLBACK = 20` (the trailing `0x14`).

`OtaData.getOtaData()` strips the leading 4 bytes, so:

- `address` = `blob[0:4]` — goes in the **settings** command, not the payload
- payload = `blob[4:]`
- `getLength()` = `len(blob) - 4`
- `getCrc()` = **crc32** of the payload (note: crc32 here, while the `"UFACE"`
  trailer inside the blob uses crc16)

Blob layout (`CustomWatchfaceHandler`):

```
[ota address][head(w,h)][main pixels][head(tw,th)][thumb pixels][crc16_lo crc16_hi id "UFACE"]
```

`tools/wfimage.py` produces everything except the leading address, which the
watch supplies in step 1.

### Risk assessment

An earlier draft of this section called the upload "materially riskier" on the
assumption it rebooted the watch into OTA mode. **That was wrong** — reading
`OtaControl` in full shows no `EnterOta` on this path.

Actual position:

- It writes to the DFU **service** (0x1530), so it is not in the same
  structurally-safe category as the data channel.
- But the watch **stays in normal firmware** — no reboot, no DFU mode.
- The payload is explicitly tagged `Picture(4)`; firmware is `Platform(1)` and
  the unrecoverable one is `Bootloader(11)`.
- Transfer is CRC32-verified by the watch (step 4) before anything is committed.

Residual risk is a malformed control frame confusing the OTA state machine. The
watch would most likely time out (`OtaMsg.TIMEOUT = 403`) and return to normal.

Still worth explicit go-ahead, but it is closer to the data-channel writes than
to firmware flashing.

---

# CONFIRMED WORKING — custom watchface installed on the KW80

2026-08-07. A generated image was encoded, uploaded, and **is displayed on the
watch**. Full pipeline:

```bash
python3 tools/wfimage.py  face.png out.bin      # encode
python3 tools/wfupload.py face.png --send       # upload over OTA
```

Successful run:

```
[0] GetOtaAddress      -> address = 00 00 c8 00  (0x00c80000)
[1] start  01 08 3c 06 00      (200 pieces)
    <- 01 01   -> settings
    <- 02 01   -> piece 0/200
    ... 200 pieces, one round trip each ...
    <- 03 01 04 08 3c 06 00    all pieces in (0x00063c08 = 408,584 = exact payload len)
    <- 04 01                   CRC verified
    <- 05 01                   OTA COMPLETE
```

## What made it work: the watch drives the transfer

Two failed attempts first, both from pushing data instead of responding to the
watch. `OtaControl.otaRecvData()` is a state machine driven by notifications on
`0x1531`:

```
notify [op, status, sub, ...]
    status 0x3A / 0x00 / 0xFF   -> failure
    op 1                        -> send settings frame
    op 2                        -> send piece 0
    op 3, sub 2                 -> advance piece index, send next piece
    op 3, sub 4                 -> all pieces received, send 04 (check CRC)
    op 4                        -> send 05 (end)
    op 5                        -> complete
```

A piece is 2048 B = 16 chunks of 128 B, below the 20-per-batch cap, so it is
**one round trip per piece, 200 total**.

### The two failures, recorded

1. **Unpaced blast** — all 3,193 chunks fired back-to-back with
   `write-without-response`, which has no flow control. The controller dropped
   packets; the watch reported `03 01 02 80 5d 01 00` = "have 89,472 bytes, send
   the next piece", and the tool answered `04` (check CRC) instead. Misreading
   `sub == 2` as an error was the actual bug.
2. **Paced blast** — a fixed per-chunk delay. Still blind pushing; the link
   dropped before the commit frame.

Tuning delays was never the fix. Honouring `sub == 2` was.

## Corrections made along the way

- `BytesUtils.crc16` and `crc32` are the **same** algorithm — a Kermit-style
  byte-wise CRC-16, **not** standard CCITT. `crc32` returns the same 16-bit
  value zero-padded to 4 bytes, because the accumulator is masked to `0xFFFF`
  every step. An initial implementation used standard CCITT and was wrong.
- `OtaData.getOtaData()` strips the 4-byte **address**, not the first four bytes
  of the image. Since `wfimage.build()` never prepends an address, its output IS
  the payload — stripping 4 bytes there removed the main LVGL header. Caught by
  the dry run.

---

# Capability map — CORRECTED

An earlier version of this section claimed the KW80 could not do animation,
custom fonts, or AOD. **All three were wrong.** The error: it analysed
`SetCustomWatchface` — the phone app's minimal "photo background" builder — and
treated that as the device ceiling. The **store format is the real surface.**

## Section 2 SOLVED: an image table

`cnt / 4` is an **image count**, and section 2 begins with that many `uint32`
offsets, each relative to `off2` and pointing at an LVGL image header.

Validated: **1/1, 28/28, 85/85, 29/29** valid headers — 100%.
**1,668 images across the 49 faces.**

```
off2 + 0                  uint32 offset[0]   -> background
off2 + 4                  uint32 offset[1]
...                       cnt/4 entries total
off2 + offset[i]          lv_img_header_t + encoded pixels
```

## What the store format actually supports

| Group size | Meaning |
|---|---|
| 10 | digits 0-9 — **a custom bitmap font** |
| 11 | digits + separator |
| 7 | **weekday** name graphics |
| 12 | **month** name graphics |
| many at full screen size | **animation frames** |

Evidence:

| Face | Images | Contents |
|---|---|---|
| `17.bin` | 33 | **6 frames of 368x448** + glyph sets |
| `WF15` | 29 | **12 frames of 364x364** + glyph sets |
| `WF01` | 28 | background + three glyph sets (18x26, 54x76, 60x28) |
| `WF44` | 85 | background + 24x 40x40, 24x 204x33, glyphs |
| `WF04` | 1 | background only — the simplest possible face |

Colour formats: **77 x `cf=24`** (opaque: backgrounds, animation frames) and
**1,591 x `cf=25`** (glyphs — `USER_ENCODED_1`, near-certainly alpha-capable).

This also explains the protobuf resource-index lists decoded earlier:
WF28's `0a 0a 14 15 16 17 18 19 1a 1b 1c 1d` = indices 20-29 = **ten digit
glyphs**, indexing this table.

## Always-on display

**The watch has AOD.** The firmware contains `AodSetting.c` and `AodStyle.c`,
and it is enabled from the watch UI. `hasAlwaysOn: false` in the device database
gates the **phone app's** AOD screen, not the hardware.

## Real capability list

| Capability | Status |
|---|---|
| Full-screen background | **proven working** end to end |
| Custom bitmap fonts (digits, weekdays, months) | **supported** by the format |
| Animation (multi-frame) | **supported** — up to ~254 images (`cnt <= 0x3f8`) |
| Multiple type sizes per face | **supported** |
| Alpha/transparency for glyphs | `cf=25` — very likely |
| Always-on display | **exists**, configured on-device |
| Layout: element type/position/size/colour/style | format known, render untested |
| Analogue hands | **SUPERSEDED — see below** |

## The one real blocker left

We cannot yet **produce** `cf=24` / `cf=25` images — that is the ~4:1 vendor
compression, still undecoded.

**Possible way around it:** the firmware's stock LVGL decoder handles `cf=4`
(raw TRUE_COLOR) natively, which is exactly what `tools/wfimage.py` already
emits and what the watch accepted for the custom-builder upload. If the OLWF
loader passes `cf=4` images straight through to LVGL, rich faces can be built
with **raw** images and no compressor at all — just larger files.

**That is the single highest-value experiment remaining.**

---

# CONFIRMED: building OLWF faces with custom bitmap fonts

Established **by experiment on the physical KW80** (class A), not inference.

## The recipe that works

| Element | Format | Layout field |
|---|---|---|
| background | **`cf=4`** (`TRUE_COLOR`, raw RGB565 BE) | `f4{f1=<idx>}` |
| glyphs | **`cf=5`** (`TRUE_COLOR_ALPHA`, RGB565 BE + 1 alpha byte) | `f6{... f23=5}` |

**Glyphs must have a real alpha channel.** `cf=4` opaque glyphs are **silently
skipped** — no error, nothing drawn — regardless of what `f23` says.

This mirrors the vendor exactly: they use `cf=24` for backgrounds and `cf=25`
for every one of their 1,591 glyphs. `cf=4`/`cf=5` is the uncompressed
equivalent of that same opaque/alpha split. **The compressor is not needed.**

## How it was determined

A single upload carrying three digit groups at different heights:

| Group | Y | Images | `f23` | Result |
|---|---|---|---|---|
| A | 60 | `cf=4` opaque | 4 | **not drawn** |
| B | 170 | `cf=5` + alpha | 5 | **drawn — showed live minutes** |
| C | 280 | `cf=4` opaque | 25 | **not drawn** |

Only B rendered, and it displayed the current minute value, which also confirms
`f5=13` = minute.

## Container recipe

```
0x00   header: off1, off2, cnt, off3, len3           5 x u32 LE
off1   thumbnail: lv_img_header_t(cf=4) + RGB565 pixels
off2   image table: cnt/4 x u32 offsets (relative to off2), then the images
off3   protobuf layout
       8-byte trailer, last 4 bytes "OLWF"
```

Layout, with **1-based** image indices (`layout ref = table index + 1`):

```
f1{ f4{ f1=<bg idx>, f2={} } }                       background
f1{ f6{ f1=<10 index bytes>,                         digit group
        f3={f1=x, f2=y},
        f5=<12 hour | 13 minute | 17 date>,
        f21=w, f22=h, f23=5 } }
f5=1                                                 terminator
```

Firmware limits, enforced by `FUN_020e593c`: `cnt <= 0x3f8`, `len3 <= 0x800`.

## Tooling

```bash
./.venv/bin/python tools/wfbuild.py  face.bin        # build an OLWF face
./.venv/bin/python tools/wfupload.py --raw face.bin --send
```

## Cost of raw images

| Asset | Raw size |
|---|---|
| background 368x448 `cf=4` | 329,732 B |
| thumbnail 180x219 `cf=4` | 78,844 B |
| glyph 54x76 `cf=5` | 12,316 B |
| **10-digit set** | **123,160 B** |

A background + one digit set is ~532 KB and uploads in about a minute. The
picture slot advanced by 0x1C0000 (1.8 MB) after the first upload, so several
faces fit. Long animations at full screen size would be the first thing to
strain it — 12 frames of 368x448 raw is ~4 MB.


---

# SUPERSEDED: this document's capability map is incomplete

A later sweep of **548 vendor watchfaces** across all 17 models sharing the
KW80's editor family found two element types this document never saw, and
settled the data-source enum by overlaying decoded layouts onto the vendor's own
rendered previews.

**Read [10-watchface-capabilities.md](10-watchface-capabilities.md) instead.**

The one claim here that must be retracted outright:

> | Analogue hands | `wl` branch only — still believed unavailable |

Wrong. The `f23` element is a **vector shape rotated by a clock source**, and it
appears **57 times in 9 of the KW80's own 49 store faces** (`WF03`, `WF04`,
`WF05`, `WF07`, `WF15`, `WF23_2`, `WF24`, `WF27`, `WF28`). Sources 150, 153 and
154 are hour, minute and second. A working analogue face costs ~500 bytes of
layout and no images at all — `tools/wfhands.py` builds one.

Also new since this document: element `f8` (bitmap sprite hands, 418 uses
elsewhere but none on the KW80), the full data-source registry, and 398 vendor
hand sprites extracted from `cf=4`/`cf=5` images (`tools/wfextract.py`).
