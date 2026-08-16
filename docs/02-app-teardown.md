# 02 — HaWoFit APK Teardown

## The app

| | |
|---|---|
| Package | `com.huawo.hawofit` |
| Version analysed | 2.5.2 |
| Developer | Huawo Wear Technology Co., Ltd. |
| Play Store | [com.huawo.hawofit](https://play.google.com/store/apps/details?id=com.huawo.hawofit) |
| iOS | [App Store id1561083814](https://apps.apple.com/us/app/hawofit/id1561083814) |
| Source | `hawofit-2-5-2.xapk` (XAPK bundle, 121 MB) |

Supports watches branded Kr2, beatXP Unbound, Crystal, KingWear, and others —
213 models total.

### Why it's so large

Initial suspicion was a mislabeled or repackaged APK. It's genuine. The bulk is:

- **AMap Navi SDK** (`libAMapSDK_NAVI_v11_1_060.so`, 59 MB) — offline maps
- **FFmpeg** (`libavcodec`, `libavformat`, `libavfilter`, ~20 MB) — video watchfaces
- **Embedded TTS voices** (`assets/tts/`, ~9 MB)
- **Huawei HMS Core / AGConnect** — for Huawei AppGallery distribution
- **NeonUI** (`libneonui_shared.so`, 6.4 MB) — UI rendering engine

Verified genuine by decoding `AndroidManifest.xml`: 160 `com.huawo.*` component
references, package `com.huawo.hawofit`.

## Bundle contents

| File | Size | Purpose |
|---|---|---|
| `com.huawo.hawofit.apk` | 116 MB | base APK, 8 dex files, 6063 assets |
| `config.arm64_v8a.apk` | 90 MB | native libraries |
| `config.xxhdpi.apk` | 10 MB | density resources |
| `config.{en,es,vi}.apk` | small | locale splits |

Signed with APK Signature Scheme v2/v3 only — no v1 `META-INF/*.RSA`, so the
signing certificate can't be read with `openssl pkcs7`.

## Reproducing the analysis

```bash
cd /Users/drwn/Documents/Projects/kw80watch

# 1. unpack the XAPK bundle
mkdir -p work/xapk && unzip -o -q hawofit-2-5-2.xapk -d work/xapk

# 2. decompile (about 3 minutes, 5402 .java files)
jadx -d work/jadx --no-res --no-debug-info -j 8 work/xapk/com.huawo.hawofit.apk

# 3. pull the device database
mkdir -p artifacts
unzip -p work/xapk/com.huawo.hawofit.apk assets/AppConfig.json > artifacts/AppConfig.json
```

### Gotchas hit during analysis

- **macOS `strings` has no `-e` flag.** Binary `AndroidManifest.xml` stores its
  string pool as UTF-16LE. `tr -d '\000'` also fails ("Illegal byte sequence").
  Use Python: `open(f,'rb').read().decode('utf-16-le', errors='ignore')`.
- **Grepping for `sign`** matches `unsignedShortFromByteArray` everywhere. Use
  word boundaries: `grep -wE 'signature|verify|encrypt|AES|RSA'`.
- **The Bash tool's cwd persists** between calls. Use absolute paths.
- **APKPure blocks scripted downloads** (403 via Cloudflare). The XAPK was
  supplied manually.

## Packages that matter

| Package | Applies to KW80? | What it is |
|---|---|---|
| `com.huawo.module_service` | **yes** | cloud API, device manager, beans |
| `com.huawo.module_interaction` | **yes** | UI, incl. `WatchfaceEditActivity`, `WatchfaceCenterActivity`, `WatchfaceInstallActivity` |
| `com.huawo.sdk.bluetoothsdk` | **yes** | Huawo's own BLE SDK |
| `com.huawo.sdk.bluetoothsdk.wl` | **likely** | non-SiFli watchface + OTA path |
| `com.huawo.sdk.bluetoothsdk.slifi` | no | SiFli branch |
| `com.sifli.*` | no | SiFli vendor SDK (DFU, watchface, ezip) |
| `com.huawo.watchface.qjs` | no | QuickJS/LVGL engine — editor family 4 only |

**Unverified:** the `wl` package is assumed to be the KW80's path because it is
the non-SiFli watchface/OTA implementation. The code that selects `wl` vs
`slifi` per device has not been traced. Confirm before relying on it.

## Native libraries of note

| Library | Size | Relevance |
|---|---|---|
| `libezip.so` | 516 KB | SiFli image compression — **not needed for KW80** |
| `libsfwatchface.so` | 4.8 KB | SiFli JNI stub — not needed |
| `libneonui_shared.so` | 6.4 MB | UI rendering |
| `libpl_droidsonroids_gif.so` | 42 KB | GIF decoding |
