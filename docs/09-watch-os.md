# 09 — The Watch OS

> ## READ THIS FIRST
>
> **Everything in this document describes SWC01 (Crystal) firmware, NOT the
> KW80.** No KW80 firmware exists anywhere — the vendor publishes none and it
> cannot be dumped from the device. Every page name, function address, load
> base, and architectural claim here is SWC01's.
>
> SWC01 is a close sibling: **92 of 108 device-config fields are identical**,
> both Realtek, editor-2, 368x448, same thumbnail geometry. Known differences:
> `hasBT` (SWC01 true, KW80 false), `hasQuickReply` (reversed), languages, and
> their own system-face lists.
>
> So it is a **reasonable proxy, not evidence about the KW80**. Do not cite
> anything here as a fact about the user's watch.
>
> **What IS sound about the KW80**, and why:
>
> | Claim | Basis |
> |---|---|
> | Watchface container + header + image table | SWC01 code, but **validated 49/49 against real KW80 store files** |
> | Image codec | the **phone app**, shared by all 213 models |
> | Upload transport | **proven on the physical KW80** — image displayed |
> | BLE command set / support matrix | queried live from the KW80 |
> | AOD unavailability | shared SDK has no AOD command; 0/49 KW80 faces carry AOD images; no editor-2 model has `hasAlwaysOn` |

## Where the firmware came from

`POST api/v1/devices/upgrades` is **unauthenticated**. Sweeping all 213 product
codes (`tools/fw_sweep.py`) found published firmware for **9 of them**.

**HA01_HW — the KW80 — is not one of the 9.** No image exists at any claimed
version.

| Product | Version | File | Usable? |
|---|---|---|---|
| **SWC01** (Crystal) | 1.0.1 | `Core1.0.1B03(KW213_AB).bin` | **yes — plaintext** |
| **SWC05** (Wise-Glaze) | 1.0.1 | `Core1.0.1B01(KW303_AB).bin` | **yes — plaintext** |
| LM200PLUS | 1.0.0 | `Core1.0.0B05(LM200PLUS).bin` | yes — plaintext |
| MOY-7UE4 / 9ZF2 / ABY3 / VZ42 / W934 / WAP2 | 2.0.x | `*-ENCRYPTED.ufw/.fot` | **no — entropy 8.00** |

SWC01 and SWC05 are **Realtek, editor 2, 368×448** — the KW80's exact family.

Downloaded to `artifacts/firmware/`. The three `Core*.bin` files share an
identical 16-byte prefix (`00 f0 2c 02 ff ff …`) and entropy ~7.08 — raw ARM
Thumb code with resources, not compressed and not encrypted.

## The MCU question — RETRACTED

> **This section was wrong about the KW80.** The strings below are genuine, but
> they describe **SWC01**, not the KW80. Using them to override the KW80's own
> BLE company ID (`0x09AC` = Ambiq) inverted the evidence hierarchy. The KW80 is
> **probably Ambiq Apollo3 Blue Plus**. SWC01 is Realtek; that says nothing about
> the KW80.

**SWC01 is Realtek.** Its firmware contains:

- `UPPER_STACK` — Realtek's Bluetooth stack image naming
- `Error! Please implement your ISR Handler for IRQ %d!` — a Realtek RTL87xx SDK string
- `flash switch 4bit success` — QSPI flash init

**This corrects an over-correction.** Earlier the watch's BLE advertisement
(company ID `0x09AC` = Ambiq) was taken as stronger evidence than the app's
`mcu: "Realtek"` field, and [08-ble-gatt.md](08-ble-gatt.md) called Ambiq "the
better guess". Firmware evidence beats an advertising byte that ODMs routinely
copy-paste. The app database was right the first time.

## Architecture

The source file paths are embedded in the binary (Windows-style, so built with
Keil MDK or IAR):

```
src/app/watch/Gui/
    LVGL/                    LVGL 8.x graphics library
        src/{core,draw,draw/sw,misc,widgets,font,hal}
        src/extra/{layouts/flex, libs/qrcode, others/snapshot, widgets/chart}
        user/
    MVP/
        PageManager/         PM_Base.c  PM_Router.c  PM_State.c  PM_Anim.c
        Pages/               one directory per screen
```

So it is **not a general-purpose OS**. It is a bare-metal / RTOS application:
**LVGL 8 for rendering, an MVP page framework on top, ~100 screens.**

The `PM_Router` / `PM_State` / `PM_Anim` split matches the open-source LVGL
PageManager used in the X-TRACK project — worth confirming, because if it is
that one, the framework's API is publicly documented.

## Every UI page in the firmware

Roughly 100 screens, recovered in full:

**Core UI** — MainMenu, MenuStyle, AppList, MoreList, OptionsList, QuickMenu,
QuickMenuAdd, QuickMenuAddPage, QuickMenuEdit, QuickApp, QuickKey, ShortCut

**Watchface** — WatchfaceSelect, WatchfaceLook, WfTopWin, AodSetting, AodStyle

**Health** — HeartRate, HeartAlert, HrTest, Spo2, Pressure, Sleep,
SleepDetailPage, Breath (+ BreathRunning, BreatheCountDown, BreatheExit,
BreatheFail, BreatheFinish, BreatheOptions), Menstruation, Mood, Activity,
ActivityDetail, GoalAchieve, GoalSetting, InactivityAlert, Wrist

**Workout** — WorkoutRunning, WorkoutResult, WorkoutHistoryList,
WorkoutSportAdd, WorkoutSportAddList, WorkoutSportChose, WorkoutSetTargetList,
WorkoutTargetAchieve

**Phone** — Telephone, TelephoneCall, TeleMain, TeleContact, TeleRecent,
IncomCall, NotiDetail, FindPhone, FindDevice, BleDisconnet, MediaOpenHint, Music

**Tools** — Calculator, Stopwatch, Timer, TimerTimeout, Alarm, AlarmTimeout,
WorldTime, Weather, Flashlight, Camera, Qrcode, Remind, EvenRemind, Assistant

**Games** — GameList, Game2048, FallingBird

**System** — Settingrest, Volume, BtSwitch, DoNotDistrbSetting, PasswordLock,
ForThePassword, DeviceInfo, Upgrade, Charge, BatteryLow, LowPower, ShutDown,
ConfirmPowerOff, MeasureFail

**Factory test suite** — FactoryTest, FactoryMainBoardTest, FactoryScreenTest,
FactoryTouchTest, FactoryKeyTesst *(sic)*, FactoryKey1Test, FactoryHrTest,
FactorySpo2Test, FactoryStepTest, FactoryMotoTest, FactoryVoiceTest,
FactoryCodeTest, FactorySystemTest, FactoryAgingMenuTest, FactoryAgingRunTest,
FactorryChargeTest *(sic)*, FactoryInputQcNum, FactoryResul *(sic)*,
FactoryShowResult

## Other findings

- **UART console exists**: `console_uart_init: p_callback %p`,
  `DMA uart_tx_ch_num = %d`. A serial console is compiled in. Reaching it means
  opening the case and finding the pads — but it would be a debug channel, and
  possibly a firmware-dump route.
- **DFU internals**: `DFU TASK`, `Enter DFU mode`, `dfuTotalTimer`,
  `dfuWait4ConTimer`, `dfu init unlock BP fail!` (BP = flash Block Protection),
  `ota_dimage_transfer`, `comb Mormal OTA, Reset to OTA Mode` *(sic)*.
- Device name format `Crystal(ID-%02x%02x)` mirrors the KW80's `KW80#02563`.
- Version strings `V1.0.0R0.0T0.0H0.0B01` — same scheme as the KW80's
  `V1.0.1R0.2T0.5H0.2B01`.

## What can and cannot be done

**Can — unlimited, zero risk:**

- Study this architecture in as much depth as wanted
- Disassemble the ARM Thumb code (Ghidra/radare2) to see how pages are built,
  how watchfaces render, how the protocol is handled
- Map the LVGL usage and the PageManager API

**Cannot — and this is the hard blocker:**

- **Obtain the KW80's own firmware.** The vendor publishes none, the BLE
  protocol has no memory-read command among its 257 operations, and Nordic
  Legacy DFU is write-only by design.
- **Therefore, modify the KW80's OS safely.** With no stock image there is no
  restore path. Flashing SWC01's firmware onto a KW80 is a cross-model write
  with no undo.

The remaining theoretical dump route is the **UART console or SWD pads inside
the case** — which means opening the watch, and Realtek parts are often shipped
with debug access locked.

## Disassembly progress

Tooling, all installed: `radare2 6.1.8`, `capstone 5.0.7`, **`ghidra 12.1.2`**
(`brew install ghidra` — the formula, not a cask; pulls `openjdk@21`).

```bash
r2 -a arm -b 16 -e asm.cpu=cortex "artifacts/firmware/SWC01__Core1.0.1B03(KW213_AB).bin"
# then: aaa
```

**Result: 5,218 functions identified.** The image is genuine, analysable ARM
Thumb code. Saved to `artifacts/analysis/`:

| File | Contents |
|---|---|
| `swc01-functions.txt` | 5,218 function entry points |
| `swc01-r2-functions.txt` | r2 `aflq` output |
| `swc01-source-paths.txt` | 163 original source file paths |
| `swc01-strings.txt` | 4,213 unique strings |

### SOLVED: load base = `0x020a8ffc`

Found by basefind across the full address space on a **4-byte** grid:
**907 string pointers resolve**, against a ~150 noise floor — a 6:1 margin.

Earlier attempts failed because they scanned only `0x02000000-0x02200000` on a
4 KB grid, and the base is not page-aligned. The file starts with a 4-byte
header word (`00 f0 2c 02`), so **file offset 4 maps to `0x020a9000`** — a clean
page boundary. Every aligned guess missed by exactly that offset.

Confirmation, from strings the base unlocked:

```
0x021c9fc3  Characteristic 8001     <- exactly the GATT chars enumerated
0x021c9fd7  Characteristic 8002        on the live KW80 (docs/08)
0x021ca1dc  Characteristic 1532
0x02178710  WIN_SleepDetailPage     <- matches MVP/Pages/ source tree
0x02178738  WIN_Spo2Chart
0x0217f360  NOTIFY_ShutDown
0x021cabc7  app_main_task_queue_create
```

Ghidra import (5,768 functions after its own analysis):

```bash
analyzeHeadless work/ghidra KW80   -import "artifacts/firmware/SWC01__Core1.0.1B03(KW213_AB).bin"   -processor "ARM:LE:32:Cortex"   -loader BinaryLoader -loader-baseAddr 0x020a8ffc
```

Decompiler output is usable. References below `0x020a9000` (seen as
`0x0204xxxx`) fall outside the image — that is the Realtek **ROM** region.

**First result:** `FUN_020e593c` is the watchface file loader. Its decompilation
corrected the header format — see [07-binary-format.md](07-binary-format.md).
The corrected model validates against **49/49** samples.

Probe script: `tools/ghidra_scripts/WfProbe.java` (PyGhidra is not enabled in
this build, so Java scripts are required). Output in
`artifacts/analysis/wf-parser-decompiled.txt`.

### Historical: how the base was found

**Absolute addresses did not resolve until the base was known.**

The file is a *combined* OTA package (`comb Mormal OTA, Reset to OTA Mode`),
not a flat image. Structure so far:

```
0x0000  00 f0 2c 02          (0x022cf000 — meaning unconfirmed)
0x0004  ff × 16              padding
0x0014  high-entropy block   probably a signature
....    ARM Thumb code + strings + resources
0x120000+                    entropy drops to ~4.6 — resource region
```

SWC01 and SWC05 share **only the first 20 bytes** (the header) and diverge
completely after — consistent with different builds sharing a header format.

Four methods were tried to recover the load base, all inconclusive:

1. Pointer-delta voting on string anchors — no consensus
2. Triangulation on the three adjacent tags (`OLWF`/`FACE`/`SOCIAL`) — 2,924
   equally-consistent candidates; 8 bytes of separation is too little signal
3. PC-relative literal pools via capstone — only 145 literals from 512 KB;
   linear Thumb disassembly desyncs badly
4. Stored Thumb function pointers against r2's 5,218 function list — best
   candidate scored 29/5,217, i.e. noise

The fix was method 1 done properly: full address space, 4-byte grid, all 2,178
string anchors.

Because `BL` is PC-relative, r2 finds functions fine at base 0. But `LDR`
literals hold absolute addresses, so **string and data cross-references are
unresolved** — which is exactly what's needed to find, say, the watchface
parser near the `OLWF` tag.

### The full watchface-load call chain

Traced end to end. **One correction along the way:** the loader's
`thunk_EXT_FUN_0000edd2(ptr, 0x41c, 0xa8)` was first read as a message post with
opcode `0x41c`. It isn't. Comparing two call sites —

```c
thunk_EXT_FUN_0000edd2(g  + 0x210, 0x41c, 0xa8);   // in the loader
thunk_EXT_FUN_0000edd2(g2 + 0x41c, 0x870, 0x08);   // in FUN_021a5022
```

— the shape is `f(ram_ptr, offset, size)`, i.e. the Realtek Bee SDK's
**`ftl_save`** (Flash Transport Layer). The loader **persists** the watchface
config to flash. The real notification is the `FUN_02143f4e(0x7e)` call.

Identified ROM thunks (all below the image base, hence `EXT`):

| Thunk | Function |
|---|---|
| `thunk_EXT_FUN_00007aec` | `memcmp` |
| `thunk_EXT_FUN_00007b44` | `memcpy` |
| `thunk_EXT_FUN_00007bde` | `memset` |
| `thunk_EXT_FUN_0000edd2` | `ftl_save` |
| `thunk_EXT_FUN_0001f5cc` / `0001f584` | `strlen` / `strcpy` |

The chain:

```
1. FUN_020e593c            watchface loader
     - memcmp last 4 bytes vs "OLWF"
     - parse the 20-byte header (off1, off2, cnt, off3, len3)
     - enforce cnt <= 0x3f8, len3 <= 0x800
     - ftl_save(state+0x210, 0x41c, 0xa8)   persist config
     - ftl_save(state+4,     0x4c8, 0x40)
     - FUN_02143f4e(0x7e)                   notify
           |
2. FUN_02143f4e(0x7e)      builds msg { type = 7, id = 0x7e }
           |
3. FUN_02143e0a            os_msg_send via *DAT_02143ed4 to the app queue
           |
4. FUN_02143ca6            APP TASK MAIN LOOP
     - os_msg_recv(queue, &msg, ...)
     - if (msg.type == 7)  ->  FUN_020ce1fe(&msg)
           |
5. FUN_020ce1fe            event dispatcher, switches on msg.id
     - falls through to FUN_020cd728, then FUN_020cdd62
     - finally: FUN_0214089e(FUN_020cf73c(), 0x2f, &msg.id)
                            ^ current page object      ^ UI event
           |
6. current page re-renders (WfTopWin / WatchfaceLook)
```

**`FUN_02143ca6` is the app task main loop.** Ghidra's auto-analysis missed it
entirely, because task entry points are only referenced as function pointers
passed to `os_task_create` — never called directly. It had to be defined by
hand (`tools/ghidra_scripts/DecompAt.java` now does this automatically).

So `0x7e` is the **"watchface changed" event**, delivered to whichever page is
currently on screen.

### Historical note: the loader does not render

Tracing consumers of the parsed header (`tools/ghidra_scripts/TraceWfState.java`)
found that **only 2 functions reference the global state pointer `DAT_020e5bc0`,
and only `FUN_020e593c` itself touches the header fields.**

The reason is visible at the end of the accept branch:

```c
g = *DAT_020e5bc0;
g[0x214] = g[0x693];   // copy the parsed header
g[0x218] = g[0x697];   //   off1
g[0x21c] = g[0x69b];   //   off2
g[0x220] = g[0x69f];   //   cnt
g[0x224] = g[0x6a3];   //   off3
g[0x228] = g[0x6a7];   //   len3
g[0x210] = (g[0x210] & 0xf0) + 1;          // set a type/state nibble
thunk_EXT_FUN_0000edd2(g + 0x210, 0x41c, 0xa8);   // post 0xa8 bytes, opcode 0x41c
g[0x11] = 5;
thunk_EXT_FUN_0000edd2(g + 4, 0x4c8, 0x40);       // post 0x40 bytes, opcode 0x4c8
FUN_02143f4e(0x7e);
```

So the loader **parses and validates, then hands off**: it packs the header into
a 0xa8-byte message and posts it under opcode `0x41c` to another task. Rendering
happens downstream of that message, in the GUI task — which is why no direct
reader of the header fields exists.

`thunk_EXT_FUN_0000edd2` resolves below the image base (`0x0000edd2`), i.e. it
is a **Realtek ROM** routine — almost certainly the RTOS message-send primitive.

**The trail for the image codec is therefore: find the handler for message
opcode `0x41c`.** That handler receives `off1`/`off2`/`cnt` and is what walks
the image data.

### Next targets in the decompiler

1. **The section-1 decompressor** — the remaining blocker for an editor.
   The registry at `DAT_02155524` was enumerated: `lv_img_decoder_init`
   (`FUN_021552dc`) registers **only the stock LVGL decoder**, which handles
   `cf` 4/5/6 and 0xb-0xe but **not** the `cf = 24` (`USER_ENCODED_0`) used by
   watchface images. So decompression happens **before** LVGL, in the watchface
   render path. Next: find the caller chain from the watchface page down to
   whatever inflates ~4:1 into a RAM buffer. See
   [07-binary-format.md](07-binary-format.md).
2. **The BLE command dispatch table** — reachable from the
   `Characteristic 8001` string reference.
3. **`cnt` semantics** — always a multiple of 4, limit 0x3f8.

### Scale

Full RE of a 1.35 MB stripped ARM Thumb firmware remains a multi-session job,
but the hard part (base address) is done and the decompiler now works.

## Honest bottom line

The OS is now well understood, and can be understood far better still without
touching the hardware. But **rewriting the KW80's own frontend is not currently
safe**, because there is no way to recover it if a flash fails.

That changes only if a firmware dump becomes possible — via the UART console,
or if Huawo ever publishes an HA01_HW image (`tools/fw_sweep.py` re-checks this
in about a minute).
