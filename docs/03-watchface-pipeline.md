# 03 — Watchface Pipeline

HaWoFit implements several unrelated watchface systems, selected per device by
the `watchfaceEditor` field in the device database. **The KW80 is editor family
2.** Most of what follows about family 4 does not apply to it, and is recorded
only because it was investigated first and shapes what's worth attempting.

## Editor families

| Editor | Models | MCU | Engine |
|---|---|---|---|
| 1 | 2 | Realtek | unknown |
| **2** | **17** | **Realtek** | **← the KW80. Not yet reverse-engineered.** |
| 4 | 182 | mostly SiFli | QuickJS + LVGL (documented below) |
| 5 | 1 | JieLi | unknown |
| 6 | 8 | JieLi/Bluetrum/Realtek | unknown |
| 10 | 3 | JieLi | unknown |

Gating code — `DeviceDifferenceManager.java:218`:

```java
public static boolean hasWatchfaceEditor04Feature() {
    return DeviceConfigManager.getProductConfigs().getWatchfaceEditor().intValue() == 4;
}
```

Only family 4 has a dedicated capability check. No equivalent
`hasWatchfaceEditor02Feature` exists, so family 2 is presumably the default path.

---

## Family 4 — QuickJS + LVGL (NOT the KW80)

Worth understanding because it's the ceiling of what this vendor's watches can
do, and because 182 of 213 models use it.

A watchface is a **zip** of a generated JavaScript module plus image resources
encoded to `.bin`. **QuickJS runs on the watch** and imports LVGL bindings.

`com/huawo/watchface/qjs/Dependence.java`:

```java
public static final String BASE_PATH = "/support_script/qjs/";
// base dependencies: module "lv" (LVGL), module "lvapp"
// emits: import { <module> } from "/support_script/qjs/<path>"
```

Widget set (`com/huawo/watchface/qjs/widgets/`): `TextWidget`,
`SingleImageWidget`, `SequenceImageWidget`, `GifWidget`, `GifSelectionWidget`,
`ArcWidget`, `PointerWidget`, `GroupWidget`, `LineImageWidget`, `LinkTextWidget`,
`OptionWidget`, `ValueWidget`, `AppLinkWidget`.

Every widget carries `location` (Point), `size` (Size), `name`/`namePrefix`/
`nameSuffix`, `jsVarName`, and a `Dependence`.

Resource naming, from `Watchface.ZipTask.exportBinFiles()`:

| Widget | Filename pattern |
|---|---|
| `LineImageWidget` | `lineRes<i>.bin` |
| `PointerWidget` | `point<i>.bin` |
| `SingleImageWidget` | `img<i>.bin` |
| `OptionWidget` | `option<i><key>.bin` |
| `GroupWidget` | `group<i><hex>.bin` |

Image encoding goes through `libezip.so` (`com.sifli.ezip.sifliEzipUtil`,
version 2.3.9) — a native ARM64 library. The class also converts MP4→GIF via
`MediaMetadataRetriever` + a bundled `gifEncoder`/`LZWEncoder`/`NeuQuant`.

`SFWatchfaceType` constants: `FACE=0`, `MUTIL_Language=1`, `BG_IMAGE=2`,
`CUSTOM=3`, `MUSIC=4`, `JAVA_SCRIPT=5`, `EQ=6`, `PREVIEW_VIDEO=7`.

Transport is BLE **or** Bluetooth SPP (`SFBLEManager` / `SFSppManager`).

---

## Family 2 — the KW80's format

**Status: not yet reverse-engineered.** This is the actual work item.

Candidate implementation is `com/huawo/sdk/bluetoothsdk/wl/`:

| Class | Likely role |
|---|---|
| `wl/watch/WlWatchfaceManager.java` | watchface push orchestration |
| `wl/watch/WlWatchfaceCallback.java` | progress/result callbacks |
| `wl/models/V10CustomWatchfaceConfig.java` | custom watchface config model |
| `wl/models/WlWatchfaceWidgetWire.java` | **wire format for widgets** — likely the core |
| `wl/models/CustomWatchfaceStorage.java` | on-watch storage accounting |
| `wl/models/WatchfaceInfo.java` | installed-face metadata |
| `wl/task/SetV10CustomWatchface.java` | the install command |
| `wl/task/GetDeviceWatchfaceAvailableStorage.java` | free-space query |
| `wl/channel/Wl1630NotifyRouter.java` | notification routing (`1630` = chip or protocol rev?) |
| `wl/ota/WlOtaManager.java` | firmware update — see [04](04-dfu-and-firmware.md) |

Generic operation interfaces also exist at
`com/huawo/sdk/bluetoothsdk/interfaces/ops/`: `SetCustomWatchface`,
`SetNewCustomWatchface`, `DeleteWatchface`, `SetWatchfaceName`.

The `V10` / `SetNewCustomWatchface` vs `SetCustomWatchface` split suggests at
least two protocol revisions. Which one the KW80 uses is unknown.

Given `hasAlbumTransmission: false` on the KW80, custom imagery must travel
inside the watchface payload rather than through a separate album channel.

### Open questions for family 2

1. Is the payload a zip, a flat binary, or a widget wire-protocol stream?
2. What pixel format — RGB565 is the usual choice at this tier. Compressed?
3. Is there a native encoder dependency (as `libezip.so` is for family 4), or is
   the packing pure Java? **This decides whether a browser-based editor is
   feasible**, and is the single highest-value thing to determine next.
4. Fixed widget slots, or free placement?
5. Does the watch validate the payload, and how does it fail?

### Next step

Read `WlWatchfaceWidgetWire.java` and `SetV10CustomWatchface.java`. Both are
static analysis — **no watch or phone needed**.
