# MK9 Badge — Firmware

CircuitPython firmware for the MK9 badge. State-machine architecture adapted from the [DCZIA Zippy Badge](https://github.com/dczia/zippy-badge).

---

## Hardware

### Microcontroller
RP2040-based board running CircuitPython 8+.

### Key Matrix (3×3)
Scanned with `keypad.KeyMatrix`. Physical layout:

```
C0R0  C1R0  C2R0        key# 0  key# 1  key# 2
C0R1  C1R1  C2R1   →    key# 3  key# 4  key# 5
C0R2  C1R2  C2R2        key# 6  key# 7  key# 8
```

| Signal | GPIO |
|--------|------|
| C0     | GP17 |
| C1     | GP13 |
| C2     | GP0  |
| R0     | GP27 |
| R1     | GP26 |
| R2     | GP16 |

### NeoPixel LEDs (15 total — GP21)

**Key LEDs 0–8** sit beneath each key. `LED index == key_number`.

**Backlight LEDs 9–14** ring the board perimeter (clockwise from top-right):

| Index | Position             |
|-------|----------------------|
| 9     | Top-right            |
| 10    | Right side           |
| 11    | Bottom-right         |
| 12    | Bottom-left          |
| 13    | Left side            |
| 14    | Top-left             |

### Accelerometer — I2C1
GoodArk **GSDA213**, which shares the MSA301 register map (part ID `0x13` at
register `0x01`, address `0x26`), so `adafruit_msa3xx.MSA301` drives it.

| Signal | GPIO |
|--------|------|
| SDA    | GP18 |
| SCL    | GP19 |

### SAO Connectors

**I2C0** (shared bus for both SAOs):

| Signal | GPIO |
|--------|------|
| SDA    | GP9  |
| SCL    | GP10 |

**SAO GPIO pins:**

| Pin     | GPIO | Default role |
|---------|------|--------------|
| SAO1 G1 | GP29 | BLE UART **RX** (Friend TXO) — see Bluetooth below |
| SAO1 G2 | GP28 | BLE UART **TX** (Friend RXI) — see Bluetooth below |
| SAO2 G1 | GP12 | input, pull-up |
| SAO2 G2 | GP11 | input, pull-up |

> With `USE_BLE_SAO = True` (default in `setup.py`) SAO1's two side pins become a
> UART for the Bluetooth module. Power and the shared I2C0 bus are unchanged on
> both headers, so I2C/power SAOs still work — **put other SAOs in SAO2.** Set
> `USE_BLE_SAO = False` to revert SAO1 to plain GPIO inputs.

---

## Software Structure

```
software/
├── boot.py          — Runs before code.py; enables USB HID, hides the drive
├── code.py          — Entry point; creates and runs the state machine
├── state.py         — Base State and StateMachine classes
├── setup.py         — Hardware init (pixels, keymatrix, I2C, accel, BLE UART)
├── global_tools.py  — Shared mutable globals (brightness, pattern index)
├── keymap.py        — EDITABLE: what each of the 9 keys sends (key/text/combo)
├── typer.py         — Uniform keyboard output over USB HID and/or Bluetooth
├── state_startup.py — Boot animation: diagonal colour wipe + BLE status flash
└── state_badge.py   — Main badge mode: backgrounds, ripples, keyboard output
```

### State machine

`code.py` creates a `StateMachine` and registers two states:

| State     | Description |
|-----------|-------------|
| `startup` | Diagonal rainbow sweep across keys + backlights, then fades into badge mode. Any keypress skips straight to badge mode. |
| `badge`   | Continuous background pattern with ripple overlays on keypresses and NKRO USB keyboard output. |

### Badge mode details

**Background patterns** (shake the badge to cycle):

| # | Pattern       |
|---|---------------|
| 0 | Rainbow wave  |
| 1 | Breathing pulse |
| 2 | Sparkle / twinkle |

**Ripple effect** — each keypress launches an expanding wavefront from that key's LED position. Up to N simultaneous ripples are supported. Each key has a unique colour derived from its position on the colour wheel.

**Accelerometer reactivity** — tilt shifts the hue offset of the background pattern continuously. A vigorous shake (>16 m/s²) cycles to the next pattern after a 2-second cooldown.

**Keyboard output** — each keypress is sent to the host as configured in
`keymap.py`. By default it's the classic numpad with full N-key rollover:

```
7  8  9
4  5  6
1  2  3
```

Output is routed automatically: **USB HID when a USB host is connected,
Bluetooth when running on battery** (see Bluetooth below).

---

## Bluetooth keyboard (optional SAO add-on)

Plug an **Adafruit Bluefruit LE UART Friend (#2479)** into **SAO1** to make the
badge a wireless Bluetooth keyboard. The RP2040 has no radio, so the Friend
provides it; its stock firmware already speaks BLE HID via AT commands (no extra
firmware to flash). When no USB host is connected, keypresses go out over BLE.

### Wiring (SAO1 header → Friend)

| SAO1 pin | Friend pin | Note |
|----------|------------|------|
| VCC (3.3 V) | VIN | Friend accepts 3.3–16 V |
| GND | GND | |
| GPIO1 = GP29 | **TXO** | Friend → RP2040 (UART RX) |
| GPIO2 = GP28 | **RXI** | RP2040 → Friend (UART TX) |
| — | **CTS → GND** | required; the Friend ignores input if CTS floats |

Because the Friend isn't SAO-shaped, use a short SAO→Friend adapter/harness with
CTS jumped to GND. Leave the Friend's MOD/DFU pin floating. A productized version
of this adapter (a real SAO PCB that hosts the Friend), plus a modern single-board
nRF52 alternative, is designed in [`hardware/BLE-SAO-README.md`](../hardware/BLE-SAO-README.md).

### Status flash at boot

When BLE is enabled, the backlight ring flashes once at startup:
**green** = Friend detected and HID enabled, **red** = no module/unresponsive.

### Pairing

Power the badge (battery, or USB just for power), open your host's Bluetooth
settings, and pair **"MK9 Badge"**. After bonding once, keypresses type over BLE.

---

## Required CircuitPython Libraries

Place in the `lib/` folder on CIRCUITPY:

| Library | Source |
|---------|--------|
| `neopixel.mpy` | Adafruit CircuitPython NeoPixel |
| `adafruit_msa3xx.mpy` | Adafruit CircuitPython MSA3XX |
| `adafruit_hid/` | Adafruit CircuitPython HID |

All available from the [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases).

Make sure the `adafruit_hid/` folder includes `keyboard_layout_us.mpy` and
`keyboard_layout_base.mpy` — these are needed for `text` macros over USB. The
Bluetooth path uses raw AT commands and needs no extra library.

---

## Programming / Flashing

1. Hold BOOTSEL while plugging in the RP2040 — it mounts as `RPI-RP2`.
2. Drag the CircuitPython UF2 onto the drive. It reboots as `CIRCUITPY`.
3. Copy the `lib/` folder contents to `CIRCUITPY/lib/`.
4. Copy all `*.py` files *except* `boot.py` from this directory to the root of
   `CIRCUITPY`, and confirm the badge animates and types.
5. Copy `boot.py` last, then unplug and replug.

> **Note:** `boot.py` is the only place USB can be reconfigured — descriptors are
> frozen once the host enumerates the badge. It enables the HID keyboard and then
> hides the `CIRCUITPY` drive, so the badge presents as a **keyboard plus a USB
> serial port** and nothing else. Copying `boot.py` won't hide the drive
> immediately: saving a file triggers auto-reload, which re-runs `code.py` but not
> `boot.py`. It takes effect on the next hard reset.

### Getting the drive back

**Hold the bottom-left key and tap RESET (`SW3`)**, or hold it while plugging in
USB-C. A hard reset re-runs `boot.py`, which sees the held key and leaves mass
storage enabled. Edit, save, and the badge auto-reloads with your change live;
unplug and replug to return to HID-only.

The serial console stays available in HID-only mode (`usb_cdc.console` is a
separate USB interface from mass storage), so `screen /dev/tty.usbmodem* 115200`
works either way — for reading tracebacks, and as the recovery path if the gate
ever misreads. `boot.py` prints which mode it chose to both the console and
`boot_out.txt`.

The gate reads the matrix directly with `digitalio` rather than through `keypad`,
and every failure path leaves the drive **enabled** — a broken `boot.py` can't
lock you out. Change `_GATE_KEY` in `boot.py` (0-8, row-major) to use a different
key. See [DEPLOY.md](../DEPLOY.md#recovery) for the full recovery ladder.

---

## Extending / Customising

- **Add a new background pattern** — add a `_bg_yourpattern()` method to `BadgeState`, increment `_NUM_PATTERNS`, and add an `elif` branch in `update()`.
- **Remap keys / add macros** — mount the drive first (hold bottom-left, tap
  RESET), then edit **`keymap.py`** on it. Each of the 9 entries is
  `{"key": "NAME"}` (held key), `{"text": "..."}` (typed string),
  `{"combo": "CTRL-C"}` (chord), or a bare string (shorthand for text).
  Save and the badge auto-reloads; no reflash. A bad entry falls back to the
  default numpad and logs to the serial console. On a machine where you'd rather
  not mount a drive at all, edit it over the REPL instead — `Ctrl-C`, then
  `import storage; storage.remount("/", False)`.
- **Change key colours** — edit `_KEY_COLORS` in `state_badge.py`.
- **Add an SAO** — use `i2c_sao` (already initialised) and the `sao*_gpio*` pins from `setup.py`.
- **Add a new state** — subclass `State`, implement `name`, `enter`, `exit`, `update`; register it with `machine.add_state()` in `code.py`.
