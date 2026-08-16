# 00 — Claims Register

Every claim in this project, classified by **where the evidence came from**.
Read this before trusting anything in the other documents.

## Why this exists

Four wrong conclusions were published in this project, and all four share one
shape: **evidence about something adjacent was treated as evidence about the
KW80.**

| Wrong claim | What was actually examined |
|---|---|
| "The MCU is SiFli" | packages inside an app that serves 213 models |
| "The MCU is Realtek — settled" | firmware from a **Fitshot Crystal**, a different hardware family |
| "No animation, no custom fonts" | `SetCustomWatchface`, the app's simplest builder |
| "AOD is a built-in style picker" | SWC01's `AodStyle.c` |

Every conclusion that survived was checked against the KW80 or data it produced.

## Evidence classes

| Class | Meaning | Trust |
|---|---|---|
| **A** | Measured on the physical KW80 | load-bearing |
| **B** | Validated against data the KW80 produced (its store faces, its API records) | load-bearing |
| **C** | From the shared phone app, which drives this device | usually sound — the code runs against this watch |
| **D** | From another device's firmware (SWC01/SWC05/LM200PLUS) | **hypothesis only** |
| **E** | Inference, marketing copy, or third-party listings | **hypothesis only** |

**Rule: only A and B may be stated as fact about the KW80.** C is sound where
the code path is confirmed to apply. D and E must always carry the hedge.

## Register

### Class A — measured on the device

| Claim | Evidence |
|---|---|
| GATT: `0x6006` data service (`0x8001`-`0x8004`), `0x1530` DFU (`0x1531`/`0x1532`) | live enumeration |
| Advertises `KW80#02563`, service `0x6006`, mfr **`0x09AC` = Ambiq**, payload `4c 59 31 55 2b 46` | live scan |
| `deviceId` `HWHA0122032101002563`, `productCode` `HA01_HW` | device replies |
| Firmware `V1.0.1R0.2T0.5H0.2B01` | device reply |
| Frame format `6F <cmd> <dir> <len:LE16> <payload> 8F`; `0x81` = status | observed request/response |
| Command support matrix (0x1E/0x07/0x93/0x94 work; whole `0x41` family UNSUPPORTED) | 80 queries run |
| Bind flow works; bindstate `00` -> `01` | executed |
| Writes work and are confirmable | brightness set + readback + restore |
| Picture OTA upload works, CRC-verified, **image displayed** | executed end to end |
| Picture slot advances `0x00c80000` -> `0x00e40000` after an upload | before/after query |
| `0x9E sub=00` returns 32 bytes of structure | live probe |

### Class B — validated against KW80 data

| Claim | Evidence |
|---|---|
| Container: 20-byte header, image blob, protobuf layout, 8-byte trailer | **49/49** samples |
| Header fields = off1, off2, cnt, off3, len3; limits `cnt<=0x3f8`, `len3<=0x800` | 49/49 |
| `off1` holds an LVGL 8 `lv_img_header_t`, `cf=24`, **180x219** | 49/49, matches device DB thumbnail size |
| Section 2 = table of `cnt/4` uint32 offsets to images | 1/1, 28/28, 85/85, 29/29 |
| **Animation supported** — `17.bin` 6 frames 368x448, `WF15` 12 frames 364x364 | its own store faces |
| **Custom bitmap fonts supported** — glyph groups of 10/11 (digits), 7 (weekdays), 12 (months) | 1,668 images across 49 faces |
| No KW80 store face carries an AOD image (0/49) vs KW338 332/334 | catalogue data |
| No firmware published for any HA01 variant | 278 product codes probed; SWC01 control returns correctly |

### Class C — from the shared app

| Claim | Note |
|---|---|
| Image codec `ImageUtil.rgb888ToRGB555Ex` — dithered RGB565 big-endian | **confirmed by our encoder reproducing a real KW80 constant**, so effectively B |
| OTA protocol state machine (`OtaControl`) | **confirmed — the upload worked** |
| `crc16`/`crc32` are the same Kermit-style CRC-16 | used successfully |
| No AOD command exists in the BLE SDK | app serves this device; sound |
| `SetCustomWatchface` layout format | format read, **effect never observed** |

### Class D/E — hypothesis only

| Claim | Class | Status |
|---|---|---|
| **MCU is Ambiq Apollo3 Blue Plus** | A (company ID) + E (product listing) | **probable, not proven** |
| MCU is Realtek | E (app DB field) + D (SWC01 strings) | **retracted** |
| Watch OS = LVGL 8 + MVP PageManager, ~100 pages | D | SWC01 only; KW80 has no games, so builds differ |
| `AodSetting.c` / `AodStyle.c` | D | SWC01 only |
| Load base `0x020a8ffc`, 5,768 functions | D | SWC01 only |
| Custom AOD unreachable | B + C | reasonable; rests on catalogue + shared SDK, not on D |

## How to verify the Ambiq claim

Currently: one class-A signal (company ID `0x09AC`) and one class-E signal
(retailer listing). That is **not** enough to state as fact — the same standard
that would have caught the Realtek error.

Ways to raise it to proven:

1. **A teardown photo** of a KW80 mainboard showing the SoC marking.
2. **BLE stack fingerprinting** — Apollo3 uses ARM Cordio; Realtek uses its own.
   Connection-parameter defaults, MTU behaviour, and GATT ordering differ.
   Compare against a known Apollo3 device.
3. **Decode `0x9E sub=00`** (32 bytes) — may carry chip or flash identifiers.
4. **Decode the manufacturer payload** `4c 59 31 55 2b 46` ("LY1U+F") — still
   unexplained.
5. **A KW80 firmware image**, if one ever appears — the vector table and flash
   map would settle it instantly.

Until one of those lands, write "**probably Ambiq Apollo3**", never "it is".

## Update: shared UI codebase (user observation)

The user compared a video of the Fitshot Crystal (SWC01) against their own KW80
and reports the software looks the same.

**Class A-ish** (direct observation of the user's device vs footage of the
other). What it establishes and what it does not:

| | |
|---|---|
| **Establishes** | Huawo ships **one LVGL + MVP PageManager frontend ported across their range**. This is expected — it is why the app carries separate `sifli`/`Realtek`/`JieLi`/`Bluetrum` branches. |
| **Raises confidence in** | [09-watch-os.md](09-watch-os.md)'s *architecture* claims (LVGL 8, PageManager, general page structure) applying to the KW80 |
| **Does NOT establish** | the MCU. One frontend across four silicon vendors means identical UI proves nothing about the chip. |
| **Does NOT make flashing viable** | Identical *source* still compiles to **incompatible binaries** across SoCs — different register maps, boot ROM, linker layout, BLE stack. "Looks the same" and "the firmware will run" are unrelated claims. |

Open discriminator: the KW80 has **no games**; SWC01's firmware contains
`GameList`, `Game2048`, `FallingBird`. Likely feature-gating by product code
within a shared codebase, but unconfirmed.

## A test that cannot fail is not a test

Shortly after this register was written, an attempt was made to confirm Ambiq by
checking whether the 32 bytes from `0x9E sub=00` fell inside Apollo3's memory
map. **That analysis was discarded**: one of four values landing in the MSPI
window (1/256 of the address space) is chance, and the values are not even known
to be addresses. The same procedure would have "confirmed" Realtek.

Any test whose outcome could not have contradicted the hypothesis is not
evidence. Prefer tests with a control (e.g. BLE stack fingerprinting against a
known-Apollo3 device) or direct observation (a teardown photo).

## Standing discipline

1. State the evidence class with any new claim about the KW80.
2. Never cite SWC01 as fact about the KW80 — it is a different hardware family
   (HR02/KW213, has BT calling, speaker, mic, crown, games; the KW80 has none).
3. When device evidence and adjacent-artifact evidence conflict, **the device
   wins**. Reversing that is exactly how the Realtek error happened.
4. Prefer experiments that produce class-A evidence over further analysis of
   class-D artifacts.

---

## Update: the 548-face corpus (2026-08-08)

All 17 models sharing the KW80's `watchfaceEditor: 2` were swept from the public
catalogue API and deduped by MD5 → **548 unique watchfaces**, all of which parse.
See [10-watchface-capabilities.md](10-watchface-capabilities.md).

This changes the evidence picture for watchface claims, so the classes need
restating for this area specifically:

| Class | Meaning here | Example |
|---|---|---|
| **A** | rendered on our KW80 | `f4` background, `f6` digits with `cf=5`, source 13 = minute, **`f23` vector hands on sources 150/153/154/255** |
| **B** | present in the KW80's *own* 49 store faces | `f23` vector hands, sources 150/153/154/255, `f20` animation, sets 50/51/52/54/181/239/248 |
| **D** | present only in other family-2 models' faces | `f8` bitmap hands, sources 156–163, 214, 238, sets 59–73/212/219/223 |

**Class B is stronger than usual here.** These are not another device's files —
they are files the vendor built *for product code `HA01_HW`* and serves from the
KW80's own catalogue endpoint. A KW80 rendering them is the normal case.
Class D remains genuinely uncertain: those faces were never meant for this watch.

### Two prior claims corrected

1. **"Analogue hands: `wl` branch only — still believed unavailable."** Wrong,
   and now settled at class A: a face built by `tools/wfhands.py` with `f23`
   capsules on sources 150/153/154 was uploaded to the physical KW80 and **all
   three hands render and track the real time** (2026-08-08). `f23` also appears
   57 times across 9 of the KW80's own 49 store faces. Corrected in
   [07-binary-format.md](07-binary-format.md)'s capability table.
2. **The `WlWatchfaceWidgetWire` element enum** (`0 CLOSE, 1 TIME, 2 DATE, …`)
   was offered as the likely meaning of the data-source field. It is not: 2 is
   heart rate and 4 is temperature, read off the vendor's own rendered previews.
   Discard that cross-reference.

### Method note — why the overlay technique is trustworthy

Data-source meanings were not inferred from the numbers. Each was read by
drawing the decoded element boxes onto **the vendor's own preview PNG for the
same face** (`tools/wfoverlay.py`) and seeing what sits inside the box. That is
a direct observation of the vendor's intent, and it is falsifiable — a wrong
guess puts the box somewhere blank. Every entry in the registry has a named
face and a named on-screen value behind it.

### Standing discipline, addition

5. For watchface features, prefer a **probe upload** over more corpus reading.
   `tools/wfprobe.py` turns each remaining open question into one upload whose
   answer can be read off a photo of the watch. Corpus evidence tells you what
   the vendor *did*; only the device tells you what it *can*.
