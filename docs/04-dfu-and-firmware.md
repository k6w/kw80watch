# 04 — Firmware Update (DFU) and Brick Risk

## Question this answers

*Can the watch be flashed wirelessly, without opening the case?*

**Yes — a wireless firmware update path exists.** Whether it will accept
*custom* firmware is **unknown and not determinable from the APK.**

## Important scope note

The DFU protocol documented below is `com.sifli.siflidfu` — the **SiFli** DFU
service. **The KW80 is Realtek**, so this is likely *not* its path. The KW80's
firmware update almost certainly runs through
`com/huawo/sdk/bluetoothsdk/wl/ota/WlOtaManager.java`, **which has not been
analysed yet.**

The SiFli protocol is recorded here because it was analysed first, it shows the
shape of what to expect, and the image-ID model is probably similar. **Do not
apply these image IDs to the KW80.**

## SiFli DFU protocol (reference only)

`com.sifli.siflidfu.Protocol` — command set over BLE or SPP.

### Image IDs

| ID | Constant | Target | Risk |
|---|---|---|---|
| 0 | `IMAGE_ID_HCPU` | main application CPU | usually recoverable — DFU stays reachable |
| 1 | `IMAGE_ID_LCPU` | low-power CPU | usually recoverable |
| 2 | `IMAGE_ID_NOR_LCPU_PATCH` | NOR LCPU patch | moderate |
| 3 | `IMAGE_ID_RES` | resources | low |
| 4 | `IMAGE_ID_FONT` / `NAND_LCPU_PATCH` | fonts | low |
| 5 | `IMAGE_ID_DYN` / `IMAGE_ID_EX` | dynamic | low |
| 6 | `IMAGE_ID_MUSIC` / `IMAGE_ID_OTA` | music / OTA | low |
| 7 | `IMAGE_ID_TINY_FONT` | tiny font | low |
| **11** | **`IMAGE_ID_BOOTLOADER`** | **bootloader** | **UNRECOVERABLE BRICK** |
| −1 | `IMAGE_ID_CTRL` | control channel | — |
| −2 | `IMAGE_ID_NAND_RES` | NAND resources | low |

### Transfer states and modes

Request/response pairs: `DFU_IMAGE_INIT_REQUEST(0)` → `RESPONSE(1)`,
`START_REQUEST(6)` → `RESPONSE(7)`, `PACKET_DATA(10)` → `RESPONSE(11)`,
`IMAGE_END(13)`, plus a parallel file-oriented set (21–31) and
`DFU_ABORT_COMMAND(37)`.

Modes: `DFU_MODE_NORMAL=1`, `DFU_MODE_RESUME=2`, **`DFU_MODE_FORCE=3`** (with
`DFU_IMAGE_FORCE_INIT_REQUEST=14`) — force mode typically bypasses
version/downgrade checks.

Resume is supported (`DFU_IMAGE_RESUME_REQUEST`, `mRemoteResumeCount`), so an
interrupted transfer is not automatically fatal.

Packet size: `SIFLI_RES_PACKET_LEN = 10240`.

## The signature question

**Client-side, there is no signature verification.** The only cryptographic
primitive anywhere in `com.sifli.siflidfu` is **MD5**, used purely as a download
integrity check:

```java
// FileProcess.java:262
MessageDigest messageDigest = MessageDigest.getInstance("MD5");
```

No AES, RSA, ECDSA, or `Cipher` usage. Same MD5-only pattern in
`DeviceUpgradeManager.downloadOtaData()` — it verifies the downloaded blob
against a server-supplied MD5 and throws `IllegalStateException("Invalid Data")`
on mismatch.

**This proves nothing about the watch.** Signature verification, if it exists,
runs in the **bootloader on the device**, which the APK cannot reveal. Two
possibilities look identical from here:

1. Images are signed, signature embedded in the blob, app just pipes bytes; or
2. Verification is off entirely — common at this price tier.

**Only writing to the watch distinguishes them, and a wrong guess can brick it.**

## Standing safety rules

1. **Never flash a bootloader image.** Nothing worth doing requires it.
2. **Obtain and verify a stock firmware image before any write**, so there is a
   restore path. See [05-cloud-api.md](05-cloud-api.md) — the download URL comes
   from `POST api/v1/devices/upgrades`.
3. **Confirm every write to the watch individually**, in advance.
4. **Identify the Realtek image-ID map before writing anything.** The SiFli table
   above must not be assumed to transfer.

## Custom firmware feasibility

For SiFli models this would be promising — [SiFli-SDK is open
source](https://github.com/OpenSiFli/SiFli-SDK) with [public hardware
docs](https://wiki.sifli.com/en/silicon/product-index.html).

**The KW80 is Realtek**, so that toolchain does not apply. Realtek's watch MCUs
(RTL876x/877x family) have a far less open ecosystem. Custom firmware here is
substantially harder than the SiFli case and should be treated as out of scope
unless the watchface track proves insufficient.
