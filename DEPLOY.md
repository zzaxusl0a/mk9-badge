# Deploying code to the MK9 badge

## The short version

Everything on this badge is flashed by **dragging a `.uf2` file onto a USB drive**.
There is no toolchain, no compiler, and nothing to install on the badge itself.

| I want to… | Do this |
|---|---|
| Run the accelerometer level test | Flash [`uf2/badge_test.uf2`](uf2/badge_test.uf2), then copy [`testing/level.py`](testing/level.py) to the drive as `code.py` |
| Run the hardware self-test | Flash [`uf2/badge_test.uf2`](uf2/badge_test.uf2) — the test is already on it |
| Run the `software/` badge firmware | Flash plain CircuitPython, then copy `software/*.py` + `lib/` |
| Put it back the way it shipped | Flash [`uf2/badge_firmware_1.0.uf2`](uf2/badge_firmware_1.0.uf2) |
| Get the `CIRCUITPY` drive back on a HID-only badge | Hold the **bottom-left key** and tap RESET (`SW3`) — see [Getting the drive back](#getting-the-drive-back) |

---

## Do I need CircuitPython?

**Only if you want to run the code in `software/` or `testing/`.** Those are
CircuitPython. The badge as shipped is *not* — `uf2/badge_firmware_1.0.uf2` is a
**MicroPython** image with its own separate firmware inside it. The two are
different Python runtimes and their code is not interchangeable.

You never install CircuitPython "onto" the badge as a separate step from your
code, though. A `.uf2` is a whole flash image, and both files in `uf2/` are full
2 MB images that already contain a Python runtime:

| File | Contains |
|---|---|
| `uf2/badge_firmware_1.0.uf2` | MicroPython + the badge firmware it shipped with |
| `uf2/badge_test.uf2` | CircuitPython 10.2.1 + `testing/code.py` + all required libraries |

So `badge_test.uf2` **is** your CircuitPython install. Flash it once and the
badge comes up with a working CircuitPython, a `lib/` folder that already has
`neopixel`, `adafruit_msa3xx`, `adafruit_bus_device` and `adafruit_register`, and
a `CIRCUITPY` drive you can drop `.py` files onto. That is the path to use for
anything in `testing/`.

---

## Getting into bootloader mode

Same for every flash, and it's the only fiddly part:

1. Unplug the badge and switch off battery power.
2. Press and **hold** the **BOOT** button (`SW1`). You'll want a pen tip or a
   toothpick — it's a small tactile switch on the back.
3. While still holding it, plug in the USB-C cable.
4. Release. A drive named **`RPI-RP2`** appears.

If `RPI-RP2` doesn't show up, you missed the timing — unplug and try again. If
the badge is already running CircuitPython, double-tapping **RESET** (`SW3`) gets
you there too, no BOOT button needed.

---

## Flashing a UF2

Drag the `.uf2` onto the `RPI-RP2` drive.

The drive will disconnect partway through the copy and your OS may complain that
the disk was ejected improperly. **That is normal** — the chip reboots the
instant it has the whole image. It is not a failed copy.

Verify it worked: a drive named `CIRCUITPY` appears (for CircuitPython images),
and the LEDs start doing something.

If you're flashing a pile of badges, [`uf2/auto_flash.py`](uf2/auto_flash.py)
watches for bootloader drives and flashes each one as it appears, several at a
time:

```bash
python3 uf2/auto_flash.py uf2/badge_test.uf2
```

---

## Path A — run the level test (or anything in `testing/`)

1. Flash `uf2/badge_test.uf2` as above. Wait for `CIRCUITPY` to mount.
2. Copy `testing/level.py` onto `CIRCUITPY` **renamed to `code.py`**:

   ```bash
   cp testing/level.py /Volumes/CIRCUITPY/code.py
   ```

3. The badge reboots the moment the file finishes saving. Lay it flat: the
   centre key should be the only key lit, in green.

That's it — no `lib/` step, because `badge_test.uf2` already ships the libraries.

To watch the serial output (this is where the interesting diagnostics go):

```bash
ls /dev/tty.usbmodem*
screen /dev/tty.usbmodem<TAB> 115200
```

Exit `screen` with `Ctrl-A` then `K`. [Thonny](https://thonny.org) or the VS Code
CircuitPython extension both give you the same console with less ceremony.

---

## Path B — run the `software/` badge firmware

This one needs a plain CircuitPython install plus a manual library copy.

1. Download the **Raspberry Pi Pico** CircuitPython UF2 from
   [circuitpython.org/board/raspberry_pi_pico](https://circuitpython.org/board/raspberry_pi_pico/).
   The badge's RP2040 is not a real Pico, but the Pico build is what the badge's
   own test image uses and every pin this firmware touches is present in it.
2. Flash it. `CIRCUITPY` appears, empty.
3. Download the matching [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases)
   and copy into `CIRCUITPY/lib/`:
   - `neopixel.mpy`
   - `adafruit_msa3xx.mpy`
   - `adafruit_bus_device/`
   - `adafruit_register/`
   - `adafruit_hid/` (including `keyboard_layout_us.mpy` and `keyboard_layout_base.mpy`)
4. Copy every `.py` file from `software/` to the root of `CIRCUITPY` — but hold
   back `boot.py` until the rest is confirmed working, because `boot.py` is what
   hides the drive.

   ```bash
   cp software/*.py /Volumes/CIRCUITPY/
   rm /Volumes/CIRCUITPY/boot.py
   ```

   Copying then removing `boot.py` is the least fiddly way to do this, and it's
   safe: `boot.py` has no effect until the next hard reset, so removing it before
   then changes nothing.

5. The badge restarts and runs `code.py`. Watch the LEDs do the startup sweep and
   check a keypress types before continuing.
6. Now copy `boot.py`.

   ```bash
   cp software/boot.py /Volumes/CIRCUITPY/
   ```

   **The drive will still be there.** Saving a file triggers auto-reload, which
   re-runs `code.py` but *not* `boot.py`. Unplug and replug — the drive is gone
   and the badge is a plain keyboard. That's the feature working, not a failure.

### Getting the drive back

`boot.py` hides the `CIRCUITPY` drive on every boot, so the badge enumerates as a
**HID keyboard plus a USB serial port** and nothing else — no mass storage for a
work machine's device policy to object to.

To mount it again: **hold the bottom-left key and tap RESET (`SW3`)**, or hold
that key while plugging in USB-C. Edit what you need, save, and the badge
auto-reloads with your change live. Unplug and replug to return to HID-only.

To edit `keymap.py` without ever exposing a drive, use the serial console
instead — it stays available in HID-only mode:

```bash
screen /dev/tty.usbmodem* 115200
```

Then `Ctrl-C` to break into the REPL, `import storage; storage.remount("/", False)`
to make the filesystem writable, rewrite the file, and `Ctrl-D` to reload.

To change which key is the gate, edit `_GATE_KEY` in `boot.py` (0-8, row-major).
To go back to a permanently visible drive, delete `boot.py` — but note that also
turns off USB HID, so the badge stops typing over USB.

### Recovery

Nothing here can permanently brick the badge, but a hidden drive changes how you
dig yourself out. Work down this list:

| Situation | Way back in |
|---|---|
| Drive hidden, badge otherwise fine | Hold bottom-left + tap RESET |
| Drive hidden, `code.py` crashed (dark LEDs, no typing) | Same gesture. `boot.py` runs before `code.py`, so the gate is unaffected by anything `code.py` does |
| `boot.py` itself is broken | The drive is *enabled* — the gate fails safe. Read the traceback in `boot_out.txt` on the drive |
| The gate won't read the key | Serial REPL: `Ctrl-C`, then `import storage; storage.remount("/", False)`, `import os; os.rename("boot.py", "boot.py.bak")`, `import microcontroller; microcontroller.reset()` |
| Nothing above works | Hold BOOT (`SW1`) while plugging in → `RPI-RP2` → flash [`flash_nuke.uf2`](https://learn.adafruit.com/circuitpython-with-raspberry-pi-pico/troubleshooting), then re-flash CircuitPython |

Two things worth knowing before you reach for the bootloader:

- **Re-flashing the same CircuitPython UF2 preserves the filesystem**, so it will
  boot you straight back into whatever `boot.py` you were trying to escape. Only
  `flash_nuke.uf2` erases it — and that takes your `keymap.py` with it.
- **Safe mode does not run `boot.py`** and comes up with the drive visible, but
  it isn't a practical route on this badge: the Pico build's status LED is GP25,
  which isn't wired here, so the timing cue for entering safe mode is invisible,
  and a fast double-tap on RP2040 lands in the UF2 bootloader instead. A `boot.py`
  exception doesn't trigger safe mode either — it prints and `code.py` runs anyway.

---

## Restoring the shipped firmware

Flash `uf2/badge_firmware_1.0.uf2`. Because it's a full image it wipes
CircuitPython and the `CIRCUITPY` drive along with it, so save anything you've
edited on the badge first.

---

## Hardware map

Verified against the PCB netlist in `hardware/mk9-badge.kicad_pcb`. Use these,
not any other table you find:

| Function | GPIO |
|---|---|
| 15-LED chain (9 key WS2812B + 6 side SK6812) | **GP21** |
| Matrix rows R0/R1/R2 | GP27, GP26, GP16 |
| Matrix columns C0/C1/C2 | GP17, GP13, GP0 |
| Accelerometer (GSDA213) SDA/SCL — I2C1 | GP18, GP19 |
| SAO SDA/SCL — I2C0 | GP9, GP10 |
| SAO1 GPIO1/GPIO2 | GP29, GP28 |
| SAO2 GPIO1/GPIO2 | GP12, GP11 |

Note `GP22` is **not** connected to anything. Earlier revisions of the
CircuitPython firmware and its README said the LED chain was on GP22; a badge
running that will simply be dark.

The accelerometer at U1 is a **GoodArk GSDA213**, not a genuine Adafruit MSA301.
It shares the MSA301 register map — part ID `0x13` at register `0x01`, I²C
address `0x26` — so `adafruit_msa3xx.MSA301` drives it correctly.
