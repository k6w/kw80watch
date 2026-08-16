# KW80 device readout

Read live from the watch over BLE, 2026-08-07, from the MacBook.
Reproduce: `./.venv/bin/python tools/blequery.py all`

> **Note:** `deviceId` below is a per-unit serial. Strip it before publishing
> this repo anywhere public.

| Query | Command bytes | Reply payload | Decoded |
|---|---|---|---|
| battery | `6f 08 70 01 00 00 8f` | `5a` | **90 %** |
| bindstate | `6f 94 70 01 00 00 8f` | `01` | **bound** (to the phone) |
| deviceid | `6f 02 70 01 00 00 8f` | ASCII | **`HWHA0122032101002563`** |
| devicetype | `6f 03 70 01 00 00 8f` | `00` + ASCII | **`HA01_HW`** |
| firmwareversion | `6f 03 70 01 00 07 8f` | `07` + ASCII | **`V1.0.1R0.2T0.5H0.2B01`** |
| watchfaceids | `6f 1e 70 01 00 00 8f` | `00 00 00 00 00` | empty / unclear |
| deviceinfo (sub 08) | `6f 03 70 01 00 08 8f` | *(none)* | zero-length — unsupported |
| sn / protocolversion / wfversion | `6f 41 70 01 00 0b\|09\|0a 8f` | `41 02` | error: cmd `0x41` unsupported |

## Decoded identifiers

- **`deviceId` = `HWHA0122032101002563`** — `HW` + `HA01` + `220321` (2022-03-21?)
  + `01` + `00` + `2563`. The trailing `2563` matches the BLE advertising name
  `KW80#02563`.
- **`productCode` = `HA01_HW`** — confirms the inference made from the store
  catalogue (49 faces for `HA01_HW`, 0 for `HA01`).
- **Firmware `V1.0.1R0.2T0.5H0.2B01`.** Parsed by
  `FirmwareVersionUtils.PATTERN = V(.+?)R(.+?)T(.+?)H(.+?)B(\d+).*`:
  V=`1.0.1`, R=`0.2`, T=`0.5`, H=`0.2`, B=`01`.
  So `currentVersion = "1.0.1"`, `currentBuild = 1`.
- **`customerCode` = `"Huawo"`** — `EnvironmentImpl.java:12`, via
  `ProductConfig.SOLUTIONPROVIDER_HUAWO`.

## Protocol structure

```
request  : 6F <cmd> 70 01 00 <sub> 8F
response : 6F <cmd> 80 <len_lo> <len_hi> <payload...> 8F
error    : 6F 01 81 02 00 <cmd> <errcode> 8F
```

Byte 1 is the command ID, byte 5 a sub-command selector. `0x70` marks a
request, `0x80` a response, `0x81` an error. `GetTask.getBusinessBytes()` takes
`recv[5:-1]`.

Notable: **queries work while the watch is bound to the phone.** No session
handshake was needed for these reads.

## Firmware endpoint result

`POST https://api.huawo-wear.com/api/v1/devices/upgrades` — **no authentication
required**, same as the watchface store.

```json
{"currentVersion":"1.0.1","productCode":"HA01_HW","currentBuild":1,
 "customerCode":"Huawo","deviceId":"HWHA0122032101002563"}
```

Response: `{"code":0,"msg":null,"data":null,"ok":true}`

Retried claiming `1.0.0`/build 0 and `0.0.1`/build 0 — **`data: null` every
time.** The vendor has **no firmware image published for this model**. Plausible
for a 2022 device that never shipped an update.

### Consequence for the firmware track

**There is no stock firmware image to download, so there is no restore path.**

Standing rule 2 said "no writes to the watch until stock firmware is downloaded
and verified". That download is not possible. So in practice: **no firmware
writes at all**, unless the firmware can be dumped off the device by another
route. A failed flash would be unrecoverable.

This does not affect the watchface track, which uses the normal data channel.
