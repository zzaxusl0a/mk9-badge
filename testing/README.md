# Hardware Tester

Self-contained hardware test fixtures for the MK9 badge. Copy the one you want to
the root of `CIRCUITPY` as `code.py` (replacing the production firmware).

If the badge is running the `software/` firmware, the `CIRCUITPY` drive is hidden
by default — hold the bottom-left key and tap RESET (`SW3`) to mount it. See
[Getting the drive back](../DEPLOY.md#getting-the-drive-back).

| File | What it does |
|------|--------------|
| `code.py` | Full fixture — LEDs, key matrix, and accelerometer at once |
| `level.py` | Accelerometer only, as a bubble level — see [Level Test](#level-test) |

See [DEPLOY.md](../DEPLOY.md) for how to get CircuitPython onto the badge in the
first place. The quick path: flash `uf2/badge_test.uf2`, which is CircuitPython
plus these tests plus every library they need, then drop your file on as
`code.py`.

---

## Level Test

`level.py` turns the badge into a bubble level. It exists to answer one question:
*is the accelerometer actually working, and does it agree with which way the
badge is tilted?*

- **Flat on the desk** — the centre key (LED 4) is the only key lit, in green.
- **Tilted** — the *downhill* key lights instead. Dip the right edge and the
  right-middle key lights; dip a corner and that corner key lights. All nine keys
  are reachable: eight tilt directions plus level.
- **Backlight ring** — green while level, ramping through amber to red as the
  tilt increases past about 38 degrees.

### Serial output

Twice a second it prints the raw axes alongside the derived board-relative
values, so you can watch the sensor directly:

```
raw x= +0.31 y= -6.84 z= +7.02 | right=-6.84 bottom=-0.31 | tilt=44.2 deg | key 3
```

`right` is positive when the right-hand edge is the low one; `bottom` is positive
when the edge nearest you is low.

### If the sensor is dead

The whole board flashes red and the console prints an I2C scan of the
accelerometer bus. `0x26` is the address to look for. Nothing at all on the bus
almost always means U1 is misaligned on its pads — see the troubleshooting
section of [buildguide.md](../buildguide.md).

The script prefers `adafruit_msa3xx` but falls back to a small built-in driver
for the same register map, so a missing library shows up as a distinct message
rather than as a dead sensor.

### If the lit key is wrong

U1 is placed at 90 degrees on the PCB, so its raw X/Y axes don't line up with the
badge's left/right and top/bottom, and the correction is baked into two constants
at the top of the file. If the lit key is consistently rotated or mirrored from
the edge you actually tipped down, **hold the centre key for about 1.5 seconds**.
That starts a guided calibration: lay the badge flat, then dip the right edge,
then dip the bottom edge. It derives the mapping and prints the two lines to
paste back into `level.py`:

```
RIGHT_FROM = (1, +1.0)
DOWN_FROM = (0, -1.0)
```

A key that lights on the correct *axis* but the wrong *side* is a sign flip; a
key that lights on the wrong axis entirely is a swap. Calibration fixes both.

---

## Full Fixture (`code.py`)

### LEDs
All 15 LEDs (9 key + 6 backlight) cycle through **red → green → blue** continuously:
- Each color holds for **0.5 s**
- A directional wipe sweeps the next color across all LEDs over **0.5 s**
- Total: **1 second per color**

### Key Matrix
Press any key — its **LED fast-flashes red → green → blue** as long as the key is held, and is excluded from the background wipe until released. All 9 keys can be held simultaneously to verify N-key rollover. Every press/release is also logged to the serial console (`key N down` / `key N up`). Expected LED for each key:

```
key 0 (C0R0) → LED 0    key 1 (C1R0) → LED 1    key 2 (C2R0) → LED 2
key 3 (C0R1) → LED 3    key 4 (C1R1) → LED 4    key 5 (C2R1) → LED 5
key 6 (C0R2) → LED 6    key 7 (C1R2) → LED 7    key 8 (C2R2) → LED 8
```

### Accelerometer
The wipe always sweeps toward whichever edge is tilted down, decided when a new wipe starts:

| Axis reading | Meaning | Direction |
|------|-----------|-----------|
| X < 0 | Tilted left | Right → Left |
| X > 0 | Tilted right | Left → Right |
| Y < 0 | Top edge down | Bottom → Top |
| Y > 0 | Bottom edge down | Top → Bottom |
| Flat (both axes < 1 m/s²) | — | Holds last direction |

Tilt the badge and watch the wipe direction change on the next colour transition.

If the accelerometer library/sensor is missing at boot, or a read fails at runtime, the tester stops the colour-cycle test and instead flashes all LEDs solid **red, red, red, blue, green** (repeated) at 0.3 s/color, with no wipe, as a fault indicator.

### Serial Output
Connect a serial terminal to see:
- A boot message reporting whether the accelerometer initialized OK
- Accelerometer X/Y/Z readings printed once per second (or `accel: not available` if the sensor is down)
- `key N down` / `key N up` for every key press/release

## Libraries Required

Beyond CircuitPython built-ins (`board`, `busio`, `time`, `keypad`), copy these from the Adafruit CircuitPython Bundle into `lib/`:

| Library | Notes |
|---------|-------|
| `neopixel.mpy` | LED driver |
| `adafruit_msa3xx.mpy` | Accelerometer driver |
| `adafruit_bus_device/` | I2C helper — dependency of `adafruit_msa3xx` |
| `adafruit_register/` | Register access helper — dependency of `adafruit_msa3xx` |

If the accelerometer library is missing or the sensor doesn't respond, the tester falls back gracefully — LEDs and keys still work, but the LEDs switch to the red/red/red/blue/green fault-flash pattern described above instead of the normal colour cycle.

---

## Restoring Production Firmware

After testing, copy all files from `software/` back to the root of `CIRCUITPY` — everything except `boot.py` first, then `boot.py` last. `boot.py` hides the `CIRCUITPY` drive from the next hard reset onward, so copy it once the rest is in place. To get the drive back afterwards, hold the bottom-left key and tap RESET (`SW3`).
