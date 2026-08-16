# 10 — Watchface Capabilities: the complete reference

Everything the OLWF format can express, derived from a **548-face corpus** of
vendor watchfaces across all 17 models that share the KW80's watchface editor
family, plus what has been proven on the physical KW80.

This supersedes the "Capability map" section of
[07-binary-format.md](07-binary-format.md), which was written from 49 faces and
missed two whole element types.

| | |
|---|---|
| Corpus | 548 unique `.bin` files (deduped by MD5 from 3,354 catalogue rows) |
| Models | KW80, KW86, KW213 ×7 rebrands, KW317 ×2, SWC01, SWC05, AOL-S04 |
| Images | 21,711 |
| Elements | 6,094 |
| Parse rate | **548/548, zero failures** |
| Tooling | `tools/wfcensus.py`, `tools/wfelem.py`, `tools/wfoverlay.py`, `tools/wfextract.py` |

## How this was established

Three independent lines, cross-checked:

1. **Parse** every layout into a generic protobuf tree and aggregate field
   usage (`wfcensus.py`). Nothing is guessed — the counts are what the vendor
   actually shipped.
2. **Overlay** the decoded elements onto the vendor's *own rendered preview
   PNG* for the same face (`wfoverlay.py`). The preview shows what the watch
   draws; the layout says where each element sits and which code drives it.
   Lining them up makes each code read itself — this is how the data-source
   registry below was built, not by inference.
3. **Experiment** on the physical KW80 for the parts the corpus cannot settle.

Evidence classes follow [00-claims-register.md](00-claims-register.md).

---

# 1. Executive summary — what a KW80 watchface can do

| Capability | Element | Status on KW80 |
|---|---|---|
| Full-screen background image | `f4` | **A — proven on device** |
| Positioned static images (sprites) | `f4` | **B** — 46 uses in KW80 faces |
| Multi-digit numbers with a custom bitmap font | `f6` | **A — proven on device** |
| Number alignment (left / centre / right) | `f6.f4` | **B** |
| A unit suffix glyph after a number (`°`, `%`) | `f6.f6` | **B** |
| Indexed graphic sets (weekday, month, AM/PM, battery) | `f5` | **B** — 82 uses |
| Multi-level progress gauges (11-step) | `f5` | **B** |
| 24-state weather icon | `f5` t=248 | **B** |
| Frame animation on a fixed timer | `f20` | **B** — 3 KW80 faces |
| **Analogue hands that track real time** | `f23` | **A — proven on device 2026-08-08** |
| Vector polygons + circles, arbitrary colours | `f23` | **A — proven on device** |
| **Partial arcs / rotating arc bands** | `f23` | **A — proven on device** |
| Bitmap sprite hands + sub-dial needles | `f8` | **D — never used in a KW80 face** |
| Always-on display layout | — | not expressible; AOD is on-watch only |

The single most important correction to earlier work: **the KW80 does have
time-driven rotation — confirmed on the physical watch.** `tools/wfhands.py`
built a face with three `f23` capsules on sources 150 / 153 / 154; all three
hands render and track the real time. The element rotates about the canvas
centre. It also appears 57 times across 9 of the KW80's own
49 store faces (`WF03`, `WF04`, `WF05`, `WF07`, `WF15`, `WF23_2`, `WF24`,
`WF27`, `WF28`). Earlier notes said analogue hands were "`wl` branch only — still
believed unavailable". That was wrong.

---

# 2. Container recap

```
0x00   header      off1, off2, cnt, off3, len3          5 × u32 LE
off1   thumbnail   lv_img_header_t + pixels
off2   image table cnt/4 × u32 offsets (relative to off2), then the images
off3   layout      protobuf, len3 bytes
       trailer     8 bytes, last 4 = "OLWF"
```

Firmware limits, enforced in `FUN_020e593c`:

| Limit | Value | Worst case seen in 548 faces |
|---|---|---|
| `cnt` (= 4 × image count) | ≤ `0x3f8` → **254 images** | 116 images (`SWC05_WF177`) |
| `len3` (layout bytes) | ≤ `0x800` → **2048 B** | 1,400 B (`SWC05_WF317`) |

KW80's own 49 faces: 1–85 images, layout 80–1,145 B, file 83 KB – 1.24 MB.
Largest file in the whole corpus: 564,932 B (`KW317_CK_KW311WF030`) — the KW80's
own `WF44` at 1.24 MB is the biggest anywhere, so ~1.2 MB is a safe ceiling.

**Layout budget is the real constraint, not image count.** A vector hand costs
95 bytes; a digit group ~33 B; a picture set ~20 B. 2048 bytes buys roughly 20
hands, or 60 digit groups.

---

# 3. Colour formats

`lv_img_header_t` (LVGL 8): `cf:5 | always_zero:3 | reserved:2 | w:11 | h:11`,
little-endian u32.

| `cf` | Name | Bytes/px | Layout | Corpus count |
|---|---|---|---|---|
| 4 | `TRUE_COLOR` | 2 | RGB565 **big-endian** | 57 |
| 5 | `TRUE_COLOR_ALPHA` | 3 | RGB565 BE + 1 alpha byte, interleaved | 341 |
| 24 | `USER_ENCODED_0` | — | vendor compression, opaque, ~4:1 | 2,095 |
| 25 | `USER_ENCODED_1` | — | vendor compression, alpha | 19,218 |

We can **produce** 4 and 5, and **read** 4 and 5. The vendor's 24/25 compressor
is still undecoded, and is not needed — the firmware's stock LVGL decoder
handles 4 and 5 natively, which is why no vendor decoder is registered in
`lv_img_decoder_init`.

**Hard rule, established by experiment (class A):** anything with transparency
must be `cf=5` **with a real alpha channel**. `cf=4` opaque glyphs are silently
skipped — no error, nothing drawn — whatever the element's `f23` says.

### Vendor artwork is extractable

398 of the corpus's images are in `cf=4`/`cf=5` and decode cleanly with
`tools/wfextract.py` → `artifacts/vendor-art/`. Every one is an analogue hand
sprite:

```
hand-src150 (hour)  131    hand-src157 (heart rate)   2
hand-src153 (min)   128    hand-src158 (calories)     4
hand-src154 (sec)   124    hand-src161 (steps)        4
hand-src156 (weekday) 2    hand-src163 (battery)      3
```

These are directly reusable as source art — real vendor hands, correct
proportions, alpha intact.

---

# 4. The layout protobuf — complete schema

```protobuf
message Watchface {
  repeated Element elements = 1;    // draw order = document order, first = back
  uint32 version           = 5;     // always 1
  uint32 schema            = 6;     // present only on KW86 (see §4.7)
}

message Element {                   // exactly one field is set
  Image      image  = 4;
  PictureSet set    = 5;
  Digits     digits = 6;
  BitmapHand bhand  = 8;
  Animation  anim   = 20;
  VectorHand vhand  = 23;
}
```

Image indices in every element are **1-based** into the image table
(`layout ref = table index + 1`).

## 4.1 `f4` — Image

```protobuf
message Image {
  uint32   index = 1;               // image table ref
  Position pos   = 2;               // absent/empty => full screen at (0,0)
}
message Position { uint32 x = 1; uint32 y = 2; }
```

1,121 uses. 499 full-screen backgrounds, 622 positioned sprites.

## 4.2 `f5` — PictureSet

One image chosen from a list by a data source. The workhorse for anything that
is a fixed set of states.

```protobuf
message PictureSet {
  bytes    indices = 1;             // one byte per state, in state order
  Position pos     = 2;
  uint32   type    = 3;             // data source, see §5
}
```

1,240 uses. The number of indices *is* the state count, and it is how each type
code was identified: 7 → weekday, 12 → month, 2 or 3 → AM/PM, 11 → a level
gauge, 24 → weather.

Repeats are allowed and meaningful — `02 02 02 03 03 03 04 04 05 05 06` is 11
battery levels drawn with only 5 distinct images.

## 4.3 `f6` — Digits

A multi-digit number rendered from a 10-glyph bitmap font.

```protobuf
message Digits {
  bytes    glyphs = 1;              // exactly 10 refs, for '0'..'9'
  Position pos    = 3;
  uint32   align  = 4;              // absent = left, 1 = centre, 2 = right
  uint32   source = 5;              // data source, see §5; absent = 0 = steps
  uint32   suffix = 6;              // ref to an 11th glyph drawn after the number
  uint32   w      = 21;             // glyph cell width
  uint32   h      = 22;             // glyph cell height
  uint32   cf     = 23;             // colour format of the glyph images
}
```

2,294 uses; `glyphs` is exactly 10 refs in all 2,294.

`f23` is **the LVGL `cf` of the referenced glyph images**, not a style flag.
Vendor files carry 25 because their glyphs are `cf=25`; ours carry 5 because
ours are `cf=5`. The device experiment that produced this rule is in
[07-binary-format.md](07-binary-format.md): `cf=4` glyphs with `f23=4` and with
`f23=25` both drew nothing; `cf=5` glyphs with `f23=5` drew and tracked live
minutes.

`suffix` is always `last glyph index + 1`, same dimensions — verified on all
four instances (`WF16`, `WF18_2`, `WF21`, `WF44`), every one a `°` after a
temperature.

## 4.4 `f8` — BitmapHand

A sprite rotated about a pivot. **Not used by any KW80 face — class D.**

```protobuf
message BitmapHand {
  uint32   index = 1;               // the hand sprite (cf=5, tall and narrow)
  Rect     box   = 2;               // {x=1, y=2, w=3, h=4} rotation area, square
  Position pivot = 3;               // pivot *within the sprite*
  uint32   range = 5;               // 360; may be omitted
  uint32   source= 6;               // rotation data source, see §5
}
```

The sprite is placed so its `pivot` lands on the centre of `box`, then rotated
by the source's angle. Worked example, `KW317_CK_KW311WF025`, second hand:
sprite 12×236, `box` = (11, 57, 388, 388) → centre (205, 251), `pivot` =
(6, 194) → x = 12/2 (centred), 194 px down the sprite, leaving a 42 px
counterweight tail.

## 4.5 `f20` — Animation

```protobuf
message Animation {
  bytes    frames = 1;              // image refs, in order
  Position pos    = 2;              // absent/empty => (0,0)
  uint32   period = 3;              // ms per frame
  uint32   loop   = 5;              // always 1
}
```

19 uses. Frame counts 4–14, periods 100/400/420/700 ms. KW80's three:
`17.bin` 6 frames of 368×448 @ 400 ms, `WF07` 12 × 274×274 @ 100 ms,
`WF15` 12 × 364×364 @ 200 ms.

**This is a free-running timer, not a clock binding.** It cannot be used to make
something track the time. Use `f23` for that.

## 4.6 `f23` — VectorHand

The most capable element, and the one that was missed. A vector shape drawn
into an off-screen canvas and rotated by a data source.

```protobuf
message VectorHand {
  Rect              canvas = 1;     // {x=1, y=2, w=3, h=4}; x,y usually absent
  repeated Position points = 2;     // polygon vertices, canvas coords
  repeated Circle   circles= 3;
  uint32            range  = 5;     // 360
  uint32            source = 6;     // rotation data source, see §5
  Colour            fill   = 7;     // polygon fill;   empty message = black
  Colour            arcCol = 8;     // circle colour;  empty message = black
  uint32            f9     = 9;     // seen once (WF27); meaning unknown
}
message Circle { Position centre = 1; uint32 r = 2; uint32 start = 3; uint32 end = 4; }
message Colour { uint32 r = 1; uint32 g = 2; uint32 b = 3; }   // omitted = 0
```

1,002 uses, 57 of them in KW80 faces.

**Rotation is about the centre of `canvas`.** Proven by `WF27`'s second hand:
its polygon runs y = 46…256 and it carries a counterweight circle at
(184, 268) — both straddling (184, 224), which is exactly 368/2 × 448/2.

Worked example, `WF03`/`WF04`/`WF05` (identical hand set):

| Source | Polygon | Circles | Reads as |
|---|---|---|---|
| 150 hour | x 177–191, y 111–206 (14 × 95) | r7 at (184,111) and (184,206) | white capsule, floating above centre |
| 153 minute | x 177–191, y 49–206 (14 × 157) | r7 at both ends | longer capsule |
| 154 second | x 182–186, y 47–264 (4 × 217) | r2 at both ends | thin needle with a tail past centre |
| 255 static | — | r9, r6, r2 at (184,224) | the centre cap, three stacked discs |

Polygon + end circles = a **capsule**; that is how every rounded hand in the
corpus is built. Compound hands stack several `f23` elements with the same
`source`: `WF28`'s hour hand is three — an outer white shape, an inner shape
with `fill = {}` (black) to hollow it out, and a separate tail below the pivot.

### Partial arcs — CONFIRMED on device (class A, 2026-08-08)

`end` is 360 in all 683 vendor circles and `start` is always absent, so no
vendor file exercises partial arcs. `tools/wfprobe.py arcs` tested four of them
on the physical KW80. All four rendered, and all four match **one** convention:

| Authored | Rendered | Reading |
|---|---|---|
| `start=0, end=90` | top-right quadrant | 0° = east, sweep counter-clockwise |
| `start=0, end=180` | top half | east → north → west |
| `start=0, end=270` | all but the bottom-right quadrant | east → north → west → south |
| `start=90, end=270` | left half | north → west → south |

```
        90 (north / 12 o'clock)
             |
180 (west) --+-- 0 = 360 (east / 3 o'clock)
             |            sweep runs start -> end counter-clockwise
       270 (south)
```

**The shape is a filled pie sector from the centre, not a stroked ring.** There
is no stroke-width field. To get a *band*, draw the sector, then draw a smaller
full disc in the background colour over it as a mask — the same trick `WF28`
uses to hollow out its hour hand (an inner shape with `fill = {}` = black).
The mask must be a **separate `f23` element**, because one element carries only
one polygon colour and one circle colour.

Because the sector is static geometry inside a rotatable element, an arc that
*grows* with a value is **not** expressible — the source rotates the shape, it
does not change the sweep. What you get instead is a **rotating arc band**,
which is the moving-ring look, driven by hour, minute or second.
`tools/wfhalo.py` builds one.

For a genuinely filling gauge, use the `f5` PictureSet types 212 / 219 / 239 —
11 pre-rendered levels for calories, heart rate and steps. That is what the
vendor does.

Authoring notes, learned building `tools/wfhalo.py`:

- A shape that should point at 12 o'clock when its value is 0 must be drawn
  pointing up. For a band whose leading edge is at 12 o'clock and which extends
  `W` degrees clockwise, author `start = 90 - W, end = 90`.
- **A mask disc wipes everything already drawn inside its radius**, including
  the background bitmap. So concentric band *tracks* cannot be painted into the
  background — the outer band's mask erases the inner one. Interleave them as
  vector elements, outermost first: track, sweep, track, sweep.
- A full ring must be authored as a plain `end = 360` disc, not as a sector.
  `90 - 360 = -270`, which wraps to 90, giving a zero-width arc that draws
  nothing.
- **A sector whose `start` exceeds its `end` draws nothing.** The renderer will
  not sweep across 0°/360°. Proven on device: on one face an authored
  `350° -> 90°` band rendered as *nothing* while a `240° -> 310°` band beside it
  worked. Emit a wrapped span as **two sectors meeting at 0°** — both can live
  in the same element, which keeps them one colour and one rotation.
  `tools/wfhalo.py:span()` does this.
- Consequence: a band wider than 90° with its leading edge at 12 o'clock
  *always* wraps, so it always needs splitting. This is the single easiest way
  to author an arc that silently fails.

## 4.7 KW86 uses a reduced schema

All 49 KW86 faces, and only those, set root `f6 = 1`. In those files:

- `Digits` omits `w`, `h` and `cf` — sizes come from the glyph images.
- The background is a `PictureSet` with `type = 223` and a single index,
  rather than an `Image`.
- The suffix glyph is field 20 or 24 instead of 6.

Read this as an older schema revision, flagged by root `f6`. It does not apply
to the KW80, which never sets root `f6`.

---

# 5. Data-source registry

One ID space, shared by `Digits.source`, `PictureSet.type` and the rotation
elements' `source`. **Every meaning below was read off a rendered preview**,
not inferred from the number.

## 5.1 Numeric values — `f6` Digits

| ID | Meaning | KW80 uses | Corpus | Evidence |
|---|---|---|---|---|
| **0** (absent) | steps | 18 | 323 | `WF12` "6040" under STEPS |
| **1** | calories | 11 | 246 | `WF18_2` "140" beside 🔥 |
| **2** | heart rate | 14 | 245 | `WF12` "88" under BPM |
| **4** | temperature | 5 | 69 | `WF18_2` "24" beside ⛅; takes the `°` suffix |
| **9** | battery % | 5 | 184 | `WF06` "100%" |
| **12** | hour | 40 | 320 | `WF12` "08" — also **class A**, live on our watch |
| **13** | minute | 40 | 321 | `WF12` "00" — also **class A**, live on our watch |
| **14** | second | 1 | 34 | `WF06` "56" |
| **17** | day of month | 46 | 361 | `WF12` "01" between SAT and JAN |
| **51** | month number | 9 | 161 | `WF25` "01-01 Sat", first field |
| 214 | active minutes (clock icon) | 0 | 27 | `KW311WF014`, ⏱ complication — **best reading, not certain** |
| 238 | unidentified | 0 | 3 | KW86 only |

## 5.2 Graphic sets — `f5` PictureSet

| ID | States | Meaning | KW80 | Corpus |
|---|---|---|---|---|
| **50** | 2 or 3 | AM / PM (3rd state = "24H") | 3 | 58 |
| **51** | 12 | month name | 6 | 59 |
| **52** | 7 | weekday name | 44 | 380 |
| **54** | 11 | battery level icon | 9 | 129 |
| **59 / 60** | 3 or 10 / 10 | hour tens / hour units | 1 | 61 |
| **61 / 62** | 6 or 10 / 10 | minute tens / minute units | 1 | 58 |
| **65–69** | 10 each | steps, digits 1–5 | 2 | 13 |
| **70 / 71** | 4 / 10 | day-of-month tens / units | 1 | 18 |
| 73 | 2 | two-state indicator, unidentified | 0 | 67 |
| **181** | 2 | Bluetooth connected / disconnected | 1 | 8 |
| **212** | 11 | calories progress gauge | 0 | 26 |
| **219** | 11 | heart-rate progress gauge | 0 | 20 |
| **223** | 1 | background (KW86 schema only) | 0 | 49 |
| **239** | 11 | steps progress gauge | 1 | 37 |
| **248** | 24 | weather condition | 2 | 68 |

The 59–71 block exists because each digit gets **its own x, y**. That is how
`WF46` runs "08:00" along a diagonal and `KW86` spaces digits by hand — the
`f6` Digits element lays digits out on a fixed pitch and cannot do that.

## 5.3 Rotation angles — `f8` and `f23`

| ID | Drives | KW80 | Corpus | Evidence |
|---|---|---|---|---|
| **150** | hour hand (12 h) | 12 | 398 | **A — live on our watch** |
| **151** | **hour on a 24 h dial** | 0 | 0 | **A** — 59.4% at 14:31 vs 60.5% expected |
| **152** | draws, always 0 — see below | 0 | 0 | inconclusive |
| **153** | minute hand | 12 | 403 | **A — live on our watch** |
| **154** | second hand | 10 | 290 | **A — live on our watch** |
| **155** | **day of month** | 0 | 0 | **A** — 26.9% vs 8/31 → 25.8% |
| **156** | **weekday** (Sunday first) | 0 | 4 | **A** — 85.4% vs Sat 6/7 → 85.7%; corpus agrees |
| **157** | heart rate *or* stress | 0 | 5 | **A** — reads 38.2%, non-zero and stable; needs the on-watch number to separate the two |
| **158** | **calories** | 0 | 7 | **A** — 0% idle → 2.2% after walking |
| **159** | draws, always 0 — see below | 0 | 0 | inconclusive |
| **160** | draws, always 0 — see below | 0 | 0 | inconclusive |
| **161** | **steps** | 0 | 7 | **A** — 0% idle → 2.1% after walking |
| **162** | draws, always 0 — see below | 0 | 0 | inconclusive |
| **163** | **battery** | 0 | 5 | **A** — on-screen 84.8% vs `GetBattery` = 0x56 = **86%** 25 min earlier |
| **255** | static (no rotation) | 23 | 301 | **A** — our centre cap rendered |

### Seven live rotation sources confirmed on device (class A, 2026-08-08)

`tools/wfprobe.py rot2` put sources 151, 152, 155–163 on eleven concentric
rings, one per ring, each segment tinted the same hue as its track so colour
alone identifies the source. Two photos were taken 24 minutes apart, the second
after walking and running heart-rate, SpO2 and stress measurements. Angles were
read against a protractor overlay (`±2–3` points; three rings sitting at true
zero establish the offset).

| Source | Idle | After activity | Expected | Verdict |
|---|---|---|---|---|
| 151 | — | 59.4% | hour 14:31 → 60.5% | **hour, 24 h dial** |
| 155 | 26.9% | 26.9% | day 8/31 → 25.8% | **day of month** |
| 156 | 85.4% | 85.4% | Sat, Sunday-first 6/7 → 85.7% | **weekday** |
| 157 | ~36% | 38.2% | — | heart rate or stress, unresolved |
| 158 | 0% | **2.2%** | small after a short walk | **calories** |
| 161 | 0% | **2.1%** | small after a short walk | **steps** |
| 163 | 84.8% | 84.8% | `GetBattery` = 86% | **battery** |
| 152, 159, 160, 162 | 0% | 0% | — | see the caveat below |

`GetBattery` returning 0x56 = 86% against an on-screen 84.8% is the anchor that
validates the whole reading method.

### Caveat: "a segment appeared" does not prove the source exists

An earlier draft of this section claimed all eleven sources were confirmed
because all eleven drew a segment. **That inference is wrong.** A source the
firmware does not recognise would plausibly resolve to angle 0 and *still draw* —
the element renders either way. So a segment at 0° is indistinguishable from an
unsupported source.

Only a **non-zero, explainable** value proves a source is wired to data. That
gives seven: 151, 155, 156, 157, 158, 161, 163 — on top of the already-proven
150, 153, 154, 255.

152, 159, 160, 162 sat at exactly 0° through walking, SpO2, stress and
heart-rate measurements. They are either unsupported, or supported but backed by
data this watch never produces (sleep, distance, active minutes, floors, VO2max).
Nothing distinguishes those two cases from the outside.

## 5.4 Correction to an earlier claim

[07-binary-format.md](07-binary-format.md) cross-referenced
`WlWatchfaceWidgetWire` and offered `0 CLOSE, 1 TIME, 2 DATE, 3 HEARTRATE,
4 STEP, 5 DISTANCE …` as the likely enum. **It is not this enum.** 2 is heart
rate, not date; 4 is temperature, not steps. That app class belongs to the `wl`
branch, which [08-ble-gatt.md](08-ble-gatt.md) already showed the KW80 does not
use. Discard it.

---

# 6. What the phone feeds the watch

A watchface can only show what the watch knows. Everything below arrives over
the DATA1 channel (service `0x6006`, write `0x8001`) in the standard frame
`6F <cmd> <dir> <len:LE16> <payload> 8F`. Source: 259 op classes in
`com.huawo.sdk.bluetoothsdk.interfaces.ops`.

## 6.1 Feeds that map to a watchface element today

| Op | Cmd | Carries | Element it drives |
|---|---|---|---|
| `SetDeviceTime` | — | time, timezone | 12, 13, 14, 17, 51, 52, 50, 150, 153, 154, 156 |
| `SetWeather` | `0x78` | see below | source 4, set 248 |
| `SetGoal` | — | step / calorie / active-time goals | scales gauges 212, 219, 239 |
| `SetUserInfo` | — | height, weight, age, gender | affects calorie maths |
| `SetTimeFormat` | — | 12 h / 24 h | AM/PM set 50 |
| `SetUnit` / `SetWeatherUnit` | — | metric / imperial, °C / °F | source 4 |

Sensor values — heart rate (2, 157), steps (0, 161), calories (1, 158),
battery (9, 54, 163) — are produced **on the watch**. The phone does not push
them and cannot fake them.

## 6.2 `SetWeather` payload — the full field list

`SetWeather` sends a TLV list under command `0x78`:

| Tag | Size | Field |
|---|---|---|
| 2 | var | city name (string) |
| 3 | 1 | condition type → picks 1 of the 24 images in set 248 |
| 4 | 1 | current temperature → source 4 |
| 5 | 1 | humidity |
| 8 / 9 | 1 | minimum / maximum temperature |
| 10 | 1 | feels-like temperature |
| 11 | 1 | UV index |
| 12 | 4 | pressure |
| 17 | 4 | visibility |
| 31 | 1 | wind scale |
| 29 | 5 | forecast entry: `day, type(2), min, max` — repeated per day |

The `Weather` model also carries `airQuality`, `rainfallProbability`,
`windDirection`, `windSpeed`, `sunriseTime`, `sunsetTime`, which
`SetWeather.sendBytes()` does **not** transmit.

So the watch stores humidity, UV, pressure, visibility, wind scale and a
multi-day forecast — but **no data-source ID in the corpus reads any of them**.
Either the renderer has codes for them that no designer used, or it does not.
This is the single biggest unexplored surface; see §8.

## 6.3 Everything else the phone can push

Not watchface-visible as far as the corpus shows, but on the device and worth
knowing about for the wider SDK: `PushMessage` (notifications),
`SetDeviceMusicInfo` / `SetMusicState` / `SetMusicVolumn`, `SetContacts`,
`SetAlarms`, `SetReminderEvents`, `SetWorldClockCity`, `SetLocation` /
`SetCurrentGpsLocation`, `SetElectronicCard`, `SetPhysiologicalPeriods`,
`SetSocialAppSwitches`, plus the whole Muslim-worship and AI-agent families.

`SetFaceScreen` / `GetFaceScreen` (cmd `0x05`) is **not** the store-watchface
path — it configures the built-in simple face with eight style bytes:
`dateStyle, timeStyle, batteryStyle, lunarCalendarStyle, screenOrientation,
backgroundStyle, heartrateStyle, usernameStyle`.

---

# 7. Practical limits

Raw uncompressed asset costs on the KW80's 368×448 screen:

| Asset | Bytes |
|---|---|
| Background 368×448 `cf=4` | 329,732 |
| Thumbnail 180×219 `cf=4` | 78,844 |
| Animation frame, full screen `cf=4` | 329,732 |
| Digit 54×76 `cf=5` | 12,316 |
| 10-digit set at 54×76 | 123,160 |
| Hand sprite 14×160 `cf=5` | 6,724 |

Working figures:

- Background + one digit set ≈ **532 KB**, roughly a minute to upload.
- The picture slot advanced by 0x1C0000 (1.8 MB) after our first upload, so
  several faces fit.
- 12 full-screen animation frames raw is ~4 MB — **do not**. Animate a small
  region (`f20` takes a position), like `WF07`'s 274×274, or use `f23` hands,
  which cost 95 bytes and no image at all.

**Vector hands are free.** A complete analogue face — background, three hands, a
centre cap — is one background image plus about 500 bytes of layout.

---

# 8. Open questions, ranked by value

1. ~~**Partial arcs.**~~ **ANSWERED — they work.** See §4.6. 0° = east,
   counter-clockwise, filled sector. Mask with a second element for a band.
2. ~~**Do sources 156–163 work on the KW80?**~~ **PARTLY ANSWERED — seven live
   sources confirmed** (151 hour-24h, 155 day, 156 weekday, 157 HR-or-stress,
   158 calories, 161 steps, 163 battery). See §5.3. 152, 159, 160 and 162 draw
   but never leave 0°, which does not distinguish unsupported from
   no-data-available.
3. **Does `f8` work on the KW80?** 418 uses across other models, zero on ours.
   If it does, bitmap hands unlock, and 398 extracted vendor sprites are ready
   to drop in. **Test:** one upload with a `cf=5` sprite and `source=150`.
3. **Do sources 156–163 work on the KW80?** They would give sub-dial needles
   for weekday, heart rate, calories, steps and battery.
4. **Are there data-source codes for humidity, UV, pressure, wind, forecast?**
   The watch stores all of them. Nothing in 548 faces reads them. A sweep of
   unused IDs on real hardware would settle it.
5. **Does `f23` accept a non-centred `canvas` (`f1.f1`/`f1.f2`)?** 132 of 1,002
   set them. If the rotation centre follows the canvas, sub-dials become
   possible with vector shapes too.
6. `f23.f9` — one occurrence, `WF27`, value 4. Unknown.
7. `PictureSet` type 73 (67 uses, 2 states) and 238 (3 uses) — unidentified.
8. The `cf=24`/`cf=25` compressor. Still undecoded. Still not needed.

Every one of 1–5 is a single OLWF upload to answer, using the transport that is
already proven working.

---

# 9. Tooling

| Tool | Does |
|---|---|
| `tools/wfcensus.py <dir> [file]` | parse a corpus, aggregate every field; dump one full tree |
| `tools/wfelem.py <variant> [file]` | deep-dump one element type across a corpus, annotated with image dims |
| `tools/wfoverlay.py <name…>` | draw decoded elements over the vendor's own preview PNG |
| `tools/wfextract.py <dir> <out>` | decode every `cf=4`/`cf=5` image out of a corpus |
| `tools/wfbuild.py` | build an OLWF face |
| `tools/wfimage.py` | RGB565 BE encoder with the app's 8×8 ordered dither |
| `tools/wfupload.py --raw <bin> --send` | upload over the OTA channel |
| `tools/cmfdecompile.py` | decompile CMF Watch Pro / Pro 2 dials (different format) |

`wfoverlay.py` takes `WF_SRC` and `WF_THUMBS` env vars to point at a corpus
other than the KW80 samples.

## Corpus on disk

```
artifacts/samples/          49 KW80 faces
artifacts/thumbs/           49 KW80 preview PNGs
artifacts/fam2/*.json       catalogues for all 17 family-2 models
artifacts/fam2/bins/        548 unique faces
artifacts/fam2/thumbs/      548 preview PNGs
artifacts/vendor-art/       398 decoded hand sprites
artifacts/analysis/layout-census.json
```

Reproduce the catalogue fetch with:

```bash
curl "https://api.huawo-wear.com/api/v1/products/<CODE>/watchfaces?customerCode=&locale=en"
```

No authentication. Family-2 codes: `KW80`(as `HA01_HW`), `KW86`, `KW213`,
`KW213_CK`, `KW213_GV`, `KW213_GV2`, `KW213_GV3`, `KW213_MAX`, `KW213_BS`,
`KW213_RO2`, `KW317`, `KW317_CK`, `SWC01`, `SWC05`, `AOL-S04`.
`HA01` and `HA02` return zero faces.
