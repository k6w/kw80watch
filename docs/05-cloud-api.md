# 05 — Huawo Cloud API

## Hosts

| Host | Role |
|---|---|
| `https://api.huawo-wear.com/` | main REST API |
| `https://static.huawo-wear.com/files/` | static asset CDN (watchface `.bin`, thumbnails) |
| `https://hz.huawo-wear.com/` | alternate region API |
| `https://hzstatic.huawo-wear.com/files/` | alternate region CDN |

Client: Retrofit + OkHttp + Jackson (`com/huawo/module_service/core/http/RetrofitClient.java`).

## Required headers

Every request passes through `AddRequestHeaderInterceptor`:

```
phoneName       URL-encoded Build.MODEL
phoneOsVersion  Build.VERSION.RELEASE
phoneOs         "Android"
appId           com.huawo.hawofit
appVersion      2.5.2
appBuild        <long version code>
locale          <language string>
country         URL-encoded display country
timeZone        TimeZone.getDefault().getID()
```

A separate `AuthorizationInterceptor` handles auth and force-logs-out on
expiry — **most endpoints require a logged-in session.** Login is at
`POST https://api.huawo-wear.com/api/users/v1/login`.

## Firmware endpoints

```
POST api/v1/devices/upgrades      → RemoteResponse<DeviceUpgradeInfo>
POST api/v1/gps/upgrades          → GPS firmware
GET  api/v1/gps/agps/{days}       → AGPS data
POST api/v1/otalogs               → OTA telemetry
GET  api/v1/devices/binds         → bound devices
POST api/v1/devices/binds         → bind a device
```

Request body — `DeviceRemote.upgradesRequestBody()`:

```java
map.put("currentVersion", str);   // firmware version, via FirmwareVersionUtils.extractV()
map.put("productCode",    str2);  // "HA01" or "HA01_HW" for the KW80
map.put("currentBuild",   l);     // build number (long)
map.put("customerCode",   Environment.server().customer_code);
map.put("deviceId",       str3);  // per-unit device identifier
```

The response yields a download URL and an MD5. `DeviceUpgradeManager.downloadOtaData()`
fetches it, verifies the MD5, and caches it under `<cacheDir>/device/firmwares/<md5>`.

### Blocker on pulling stock firmware

Three of the five body fields come from a **paired watch**:

| Field | Source | Have it? |
|---|---|---|
| `productCode` | device DB | **yes** — `HA01` / `HA01_HW` |
| `customerCode` | app build constant | not yet extracted — static, obtainable |
| `currentVersion` | connected watch | **no** |
| `currentBuild` | connected watch | **no** |
| `deviceId` | connected watch | **no** |

Plus an auth token, requiring a logged-in account.

**Untested:** whether the endpoint tolerates a low/fake `currentVersion` and
`currentBuild` (to elicit "latest firmware") and whether `deviceId` is validated
against the account's bound devices. Both are plausible; neither is confirmed.

Pulling stock firmware is therefore **likely blocked on having the watch
paired**, contrary to the initial estimate that it was network-only. Worth one
unauthenticated probe to check the failure mode before assuming.

## Watchface store endpoints

`com/huawo/module_service/dao/remote/WatchFaceOnLine.java`:

```
GET    api/v1/products/{deviceType}/watchfaces          → online face list
GET    api/v1/products/{deviceType}/watchfaces/likes    → favourites
PUT    api/v1/products/{deviceType}/watchfaces/likes/{watchId}
DELETE api/v1/products/{deviceType}/watchfaces/likes/{watchId}
GET    api/v1/watchfaces/{deviceType}                   → my faces
POST   api/v1/watchfaces                                → online list (v2)
GET    /api/v1/watchfaces/categoriesWithWatchfaces      → categorised
GET    <url>  @Streaming                                → download a .bin
```

Common query params: `customerCode`, `locale`, and for the categorised endpoint
`productCode` + `version`.

### Face record shape (`RowsDTO`)

```java
String id, name, productId;
String bin;            // download URL of the watchface binary
String binMd5;         // integrity hash
Long   byteSize;
String thumbnail, aodThumbnail;
String author, descri, tag, remark, status, fileId;
boolean like;
```

**This is the single most valuable endpoint for the project.** `bin` + `binMd5`
means real, known-good KW80 watchface files can be downloaded as format samples —
the raw material for reverse-engineering editor family 2.

`deviceType` here maps to `productCode`, so `HA01` / `HA01_HW` should select
KW80-compatible faces.

**Untested:** whether the list endpoint requires auth. If it's open, format
samples can be collected with no watch and no account — which would unblock most
of the remaining work. **This is the highest-value thing to test next.**

## Other endpoints

`AppUpgradeRemote`, `UserRemote`, `WeatherRemote`, `SportRemote`, `SleepRemote`,
`HeartRateRemote`, `HRVRemote`, `PAIRemote`, `BloodPressureRemote`,
`WorkoutRemote`, `ShareRemote`, `FeedbackRemote`, `UploadFileRemote`,
`PushAppRemote`, `WeChatRemote`, `OthersRemote`, `AIRemote` — not relevant to
watchfaces.

## Also in the APK

`GET /api/v1/apps/config?lastUpdateTime=...` returns `AppConfigInfo` — the live
version of `assets/AppConfig.json`. The bundled copy is stamped
`2026-05-07 10:42:43`; the live endpoint would give current device data,
including any models added since.
