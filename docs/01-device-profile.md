# 01 — Device Profile: KingWear KW80

## Correction to an earlier assumption

An early read of the APK found `com.sifli.watchfacesdk` and `libsfwatchface.so`
and concluded the KW80 was a **SiFli SF32LB** device. **That was wrong.**

HaWoFit is one app covering **213 watch models**. The SiFli code is there for the
175 SiFli models it supports.

This matters a lot: the JavaScript/LVGL watchface engine described in
[03-watchface-pipeline.md](03-watchface-pipeline.md) belongs to SiFli devices and
is **not** what the KW80 uses.

## RETRACTED: the "Realtek" claim

> This section concluded Realtek. **That is retracted.** The KW80 advertises
> Bluetooth company ID `0x09AC` = **Ambiq**, and retail listings specify
> "Apollo 3 Plus" (Ambiq Apollo3 Blue Plus), whose datasheet lists the QSPI
> AMOLED interface this watch's 368x448 panel needs. The Realtek conclusion came
> from SWC01 firmware strings — a **different hardware family**. Device evidence
> outranks another device's firmware. Current status: **probably Ambiq Apollo3
> Blue Plus, not proven.** See [00-claims-register.md](00-claims-register.md).

### Original section (kept for the record)

## How strong is the "Realtek" claim?

**Strong for "not SiFli". Weaker for "specifically Realtek".** Be precise about
this — an earlier version of this document overstated it as "authoritative vendor
data, not inference".

### Supporting evidence

- `assets/AppConfig.json` inside the APK is the vendor's own device database.
  Exactly **two** entries have `bleName: "KW80"`; both say `mcu: "Realtek"`,
  368×448, editor 2. No KW80 entry says anything else.
- `ProductConfig.java:18-21` defines `BLUETRUM_MCU`, `JIELI_MCU`, `REALTEK_MCU`,
  `SIFLI_MCU` as constants — a real enumeration, not free text.
- `DeviceConfigManager.java:483` builds `bleCacheMap` keyed on `bleName`, so the
  app resolves a scanned device to a product config **by advertised BLE name**.
  The user's watch advertises `KW80#02563`.

### Countervailing evidence

- The **only** `mcu` string comparison anywhere in the codebase is
  `"sifli".equals(getMcu())` (`ProductConfig.java:873`,
  `WatchProperties.java:189`). **No code branches on `"Realtek"`.**
- `WatchProperties.getMcu()` returns `"sifli"` when the field is null, and both
  `DeviceConfigManager:170` and `DeviceBindManager:156` hard-set `"sifli"`.
- So in practice the field behaves as a binary is-SiFli / is-not-SiFli flag.
  "Realtek" is the vendor's label for the not-SiFli case, uncorroborated by any
  runtime behaviour.
- **No chip ID has been read off the physical watch.** The identification is an
  inference from BLE advertising name to database row.

### What actually depends on this

Nothing downstream requires Realtek-ness specifically. The load-bearing facts are
`watchfaceEditor: 2` and `productCode: HA01_HW`, and both are **confirmed
empirically**: the store returns 49 faces for `HA01_HW` and 0 for `HA01`, and all
49 parse with the identical header layout documented in
[07-binary-format.md](07-binary-format.md).

Extracted data: `artifacts/AppConfig.json`, KW80 entries isolated in
`artifacts/kw80-productconfig.json`.

## The KW80 entries

Two rows share the BLE name `KW80`, differing only in `productCode` and
`videoWatchfaceDuration`. Which one applies depends on the specific unit and can
only be confirmed by pairing.

| Field | `HA01_HW` | `HA01` |
|---|---|---|
| `id` | 1297959786255482880 | 1297987244673466368 |
| `buzId` | `d_kw80_id` | `d_ha01_id` |
| `bleName` | KW80 | KW80 |
| `productName` | KW80 | KW80 |
| **`productCode`** | **HA01_HW** | **HA01** |
| **`mcu`** | **Realtek** | **Realtek** |
| `solutionProvider` | null | null |
| `shape` | rectangle | rectangle |
| **`width` × `height`** | **368 × 448** | **368 × 448** |
| `radius` (corner) | 55 | 55 |
| thumbnail | 180 × 219, radius 26 | 180 × 219, radius 26 |
| **`watchfaceEditor`** | **2** | **2** |
| `buttonCount` | 2 | 2 |
| `videoWatchfaceDuration` | 1 | 0 |
| `screen` | null | null |

The user's watch advertises as `KW80#02563` — the `#NNNNN` suffix is a
per-unit BLE advertising discriminator, not a model variant.

### Feature flags

**Enabled:** `hasPasscode`, `hasPhysiologicalCycle`, `hasQuickReply`,
`hasSpO2`, `hasStress`

**Disabled — note these, they constrain the design:**

| Flag | Value | Consequence |
|---|---|---|
| `hasBT` | false | **BLE only.** No Bluetooth Classic / SPP. All transfers go over GATT. |
| `hasAlwaysOn` | false | No AOD variant needed per face. |
| `hasAlbumTransmission` | false | No photo-album push channel. Images must arrive inside the watchface payload. |
| `hasMusicTransmission` | false | — |
| `hasAI` | false | — |

`hasBT: false` is the significant one: everything must fit through BLE GATT
writes, which are slow. Expect meaningful transfer times for image-heavy faces.

## Fleet context

Across all 213 models in the database:

| MCU | Models | Editor families used |
|---|---|---|
| sifli | 175 | 4 (all) |
| **Realtek** | **26** | **2 (×17), 4 (×6), 1 (×2), 6 (×1)** |
| JieLi | 10 | 6 (×6), 10 (×3), 5 (×1) |
| slifi *(typo of sifli)* | 1 | 4 |
| Bluetrum | 1 | 6 |

The KW80 sits in the **Realtek + editor 2** group — 17 models. That group is the
addressable market for anything built here, which is relevant to the marketplace
question: a KW80-only marketplace is small, but an editor-2 marketplace covers 17
models with identical tooling *if* they share geometry handling.

**Unverified:** whether all 17 editor-2 models share one binary format, or
whether screen dimensions alone differentiate them. Worth checking before
designing the SDK — it's a cheap query against `artifacts/AppConfig.json`.
