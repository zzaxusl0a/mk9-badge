"""
MK9 Badge — Accelerometer Level Test

Turns the badge into a bubble level so you can see, at a glance, whether the
accelerometer is alive and which way it thinks "down" is.

    flat on the desk  ->  centre key (LED 4) glows green
    tilt the badge    ->  the *downhill* key lights up
                          (edges for edge tilts, corners for corner tilts)
    backlight ring    ->  green when level, ramping to red as tilt increases

Serial console prints the raw sensor axes twice a second, so you can watch the
numbers directly. If the sensor can't be reached at all, the whole board
flashes red and the console prints an I2C scan of the bus.

    Hold the CENTRE key for ~1.5 s to run a guided axis calibration.

Copy this file to the root of CIRCUITPY as `code.py`.
"""

import math
import time

import board
import busio
import keypad
import neopixel

# ---------------------------------------------------------------------------
# Axis mapping — the only thing you should need to change
#
# The accelerometer (U1) is placed at 90 deg on the PCB, so its raw X/Y axes do
# not line up with the badge's left/right and top/bottom. Each entry below is
# (raw axis index, multiplier) chosen so the result is POSITIVE when that edge
# of the badge is the low one:
#
#   RIGHT_FROM -> positive when the right-hand edge dips
#   DOWN_FROM  -> positive when the bottom edge (nearest you) dips
#
# If the lit key is rotated or mirrored from the edge you actually tipped down,
# hold the centre key to run the calibration and paste back the two lines it
# prints.
# ---------------------------------------------------------------------------
RIGHT_FROM = (1, +1.0)      # raw Y, as-is
DOWN_FROM = (0, -1.0)       # raw X, negated

LEVEL_DEAD = 1.5            # m/s^2 — below this on both axes = "level"
FULL_TILT = 6.0             # m/s^2 — tilt that shows full red
BRIGHTNESS = 0.4

CAL_HOLD = 1.5              # s — centre-key hold that starts calibration
CAL_MIN_TILT = 5.0          # m/s^2 — tilt that counts as a deliberate dip
CAL_STEADY = 0.8            # s — how long that dip must be held

STANDARD_GRAVITY = 9.80665

# ---------------------------------------------------------------------------
# Hardware — pins taken from the PCB netlist (hardware/mk9-badge.kicad_pcb)
# ---------------------------------------------------------------------------
NUM_PIXELS = 15
NUM_KEYS = 9
BACKLIGHT = range(9, 15)
CENTRE_KEY = 4

pixels = neopixel.NeoPixel(
    board.GP21, NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.GRB,
)

keys = keypad.KeyMatrix(
    (board.GP27, board.GP26, board.GP16),   # R0, R1, R2
    (board.GP17, board.GP13, board.GP0),    # C0, C1, C2
    columns_to_anodes=True,
)

i2c = busio.I2C(board.GP19, board.GP18)     # I2C1: SCL=GP19, SDA=GP18


def scan_i2c():
    """Return the addresses answering on the accelerometer bus."""
    while not i2c.try_lock():
        pass
    try:
        return i2c.scan()
    finally:
        i2c.unlock()


class RawAccelerometer:
    """Minimal MSA301 / GSDA213 driver.

    The badge's U1 is a GoodArk GSDA213, which shares the MSA301 register map:
    part ID 0x13 at register 0x01, then six data bytes at 0x02 holding signed,
    left-aligned 14-bit samples. Used when `adafruit_msa3xx` isn't installed.
    """

    ADDRESS = 0x26
    PART_ID = 0x13

    def __init__(self, bus, address=ADDRESS):
        self.bus = bus
        self.address = address
        part = self._read(0x01, 1)[0]
        if part != self.PART_ID:
            raise RuntimeError(
                "part ID 0x{:02x} at 0x{:02x}, expected 0x13".format(part, address)
            )
        self._update(0x10, 0x10, 0x07)   # all axes enabled, 125 Hz sample rate
        self._update(0x11, 0x21, 0x0E)   # normal power mode, 62.5 Hz bandwidth
        self._update(0x0F, 0xF0, 0x01)   # 14-bit resolution, +/-4 g range
        self._counts_per_g = 2048.0

    def _read(self, register, length):
        buf = bytearray(length)
        while not self.bus.try_lock():
            pass
        try:
            self.bus.writeto_then_readfrom(self.address, bytes([register]), buf)
        finally:
            self.bus.unlock()
        return buf

    def _update(self, register, keep, bits):
        value = (self._read(register, 1)[0] & keep) | bits
        while not self.bus.try_lock():
            pass
        try:
            self.bus.writeto(self.address, bytes([register, value]))
        finally:
            self.bus.unlock()

    @property
    def acceleration(self):
        data = self._read(0x02, 6)
        out = []
        for i in (0, 2, 4):
            raw = data[i] | (data[i + 1] << 8)
            if raw & 0x8000:
                raw -= 0x10000
            out.append((raw >> 2) / self._counts_per_g * STANDARD_GRAVITY)
        return tuple(out)


def open_sensor():
    """Try the Adafruit driver, then the built-in one. Returns (sensor, note)."""
    try:
        import adafruit_msa3xx
        return adafruit_msa3xx.MSA301(i2c), "adafruit_msa3xx.MSA301"
    except ImportError:
        pass
    except Exception as error:      # present but unhappy — fall through and retry raw
        print("adafruit_msa3xx failed: {}".format(error))
    try:
        return RawAccelerometer(i2c), "built-in raw driver"
    except Exception as error:
        print("raw driver failed: {}".format(error))
        return None, None


# ---------------------------------------------------------------------------
# Level maths
# ---------------------------------------------------------------------------

def downhill(reading):
    """Map a raw (x, y, z) reading to (toward_right, toward_bottom)."""
    right = reading[RIGHT_FROM[0]] * RIGHT_FROM[1]
    down = reading[DOWN_FROM[0]] * DOWN_FROM[1]
    return right, down


def downhill_key(right, down):
    """Which of the 9 keys sits at the low corner/edge. 4 = level."""
    col = 1
    row = 1
    if abs(right) >= LEVEL_DEAD:
        col = 2 if right > 0 else 0
    if abs(down) >= LEVEL_DEAD:
        row = 2 if down > 0 else 0
    return row * 3 + col


def tilt_color(magnitude):
    """Green at level, through amber, to red at FULL_TILT and beyond."""
    span = FULL_TILT - LEVEL_DEAD
    fraction = (magnitude - LEVEL_DEAD) / span if span > 0 else 1.0
    fraction = min(1.0, max(0.0, fraction))
    return (int(255 * fraction), int(230 * (1.0 - fraction)), 0)


def tilt_degrees(right, down, vertical):
    """Angle between the badge's face and horizontal, in degrees."""
    planar = math.sqrt(right * right + down * down)
    return math.degrees(math.atan2(planar, abs(vertical) + 1e-6))


# ---------------------------------------------------------------------------
# Guided calibration
# ---------------------------------------------------------------------------
_CAL_CUES = {
    "right": (2, 5, 8),
    "bottom": (6, 7, 8),
}


def _capture_axis(sensor, label):
    """Wait for the named edge to be dipped and held; return (index, multiplier)."""
    print("  Tip the {} edge of the badge DOWN and hold it steady...".format(label))
    cue = _CAL_CUES[label]
    steady_from = None
    locked = None
    while True:
        now = time.monotonic()
        try:
            reading = sensor.acceleration
        except Exception as error:
            print("  read failed: {}".format(error))
            return None

        index = 0 if abs(reading[0]) >= abs(reading[1]) else 1
        value = reading[index]

        if abs(value) >= CAL_MIN_TILT:
            candidate = (index, 1.0 if value > 0 else -1.0)
            if candidate != locked:
                locked = candidate
                steady_from = now
            elif now - steady_from >= CAL_STEADY:
                print("    got it: raw {} {}".format(
                    "xyz"[index], "as-is" if candidate[1] > 0 else "negated"))
                return candidate
        else:
            locked = None
            steady_from = None

        # Pulse the cue LEDs so it's obvious which edge is being asked for.
        on = int(now * 3) % 2 == 0
        pixels.fill((0, 0, 0))
        for led in cue:
            pixels[led] = (0, 90, 160) if on else (0, 20, 40)
        if locked is not None:
            held = min(1.0, (now - steady_from) / CAL_STEADY)
            for led in BACKLIGHT:
                pixels[led] = (0, int(200 * held), 0)
        pixels.show()
        time.sleep(0.02)


def calibrate(sensor):
    """Derive RIGHT_FROM / DOWN_FROM from two guided tilts."""
    global RIGHT_FROM, DOWN_FROM

    print("\n--- axis calibration ---")
    print("  Lay the badge FLAT, keycaps up...")
    flat_from = None
    while flat_from is None or time.monotonic() - flat_from < 1.0:
        try:
            reading = sensor.acceleration
        except Exception as error:
            print("  read failed: {}".format(error))
            return
        if abs(reading[0]) < 2.0 and abs(reading[1]) < 2.0 and abs(reading[2]) > 8.0:
            if flat_from is None:
                flat_from = time.monotonic()
        else:
            flat_from = None
        pixels.fill((0, 0, 0))
        pixels[CENTRE_KEY] = (0, 120, 0) if flat_from else (60, 40, 0)
        pixels.show()
        time.sleep(0.02)
    print("  flat: x={:+.2f} y={:+.2f} z={:+.2f} m/s^2  (z near +/-9.8 = good)".format(
        *sensor.acceleration))

    right = _capture_axis(sensor, "right")
    if right is None:
        return
    time.sleep(0.6)
    down = _capture_axis(sensor, "bottom")
    if down is None:
        return

    if right[0] == down[0]:
        print("  Both tilts moved the same axis — one of them probably wasn't")
        print("  held far enough over. Try again, and tilt further.")
        return

    RIGHT_FROM, DOWN_FROM = right, down
    print("\n  Calibrated. Paste these into the top of level.py to keep it:")
    print("    RIGHT_FROM = ({}, {:+.1f})".format(*RIGHT_FROM))
    print("    DOWN_FROM = ({}, {:+.1f})".format(*DOWN_FROM))
    print("--- calibration done ---\n")


# ---------------------------------------------------------------------------
# Fault display — sensor unreachable
# ---------------------------------------------------------------------------

def fault_loop(message):
    print("\n*** accelerometer not usable: {}".format(message))
    found = scan_i2c()
    if found:
        print("*** I2C1 (GP18/GP19) answered at: {}".format(
            ", ".join("0x{:02x}".format(a) for a in found)))
        print("*** expected 0x26 for the GSDA213/MSA301")
    else:
        print("*** nothing answered on I2C1 (GP18/GP19) at all.")
        print("*** U1 is likely misaligned on its pads — see the troubleshooting")
        print("*** section of buildguide.md.")
    while True:
        on = int(time.monotonic() * 2) % 2 == 0
        pixels.fill((120, 0, 0) if on else (0, 0, 0))
        pixels.show()
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
sensor, driver = open_sensor()
if sensor is None:
    fault_loop("no driver could talk to it")

print("MK9 Badge level test — using {}".format(driver))
print("I2C1 devices: {}".format(
    ", ".join("0x{:02x}".format(a) for a in scan_i2c()) or "none"))
print("Lay it flat: the centre key should be the only one lit.")
print("Hold the centre key for {:.1f} s to calibrate the axes.\n".format(CAL_HOLD))

last_print = time.monotonic()
centre_down_at = None

while True:
    now = time.monotonic()

    try:
        reading = sensor.acceleration
    except Exception as error:
        fault_loop("read error: {}".format(error))

    right, down = downhill(reading)
    lit = downhill_key(right, down)
    offset = max(abs(right), abs(down))
    level = lit == CENTRE_KEY

    # --- render ---
    pixels.fill((0, 0, 0))
    if level:
        pixels[CENTRE_KEY] = (0, 200, 0)
        edge = (0, 40, 0)
    else:
        pixels[lit] = tilt_color(offset)
        edge = tilt_color(offset)
    for led in BACKLIGHT:
        pixels[led] = edge
    pixels.show()

    # --- centre-key hold starts calibration ---
    event = keys.events.get()
    if event:
        if event.key_number == CENTRE_KEY:
            centre_down_at = now if event.pressed else None
        print("key {} {}".format(event.key_number, "down" if event.pressed else "up"))
    if centre_down_at is not None and now - centre_down_at >= CAL_HOLD:
        centre_down_at = None
        calibrate(sensor)
        keys.events.clear()
        last_print = time.monotonic()

    # --- 2 Hz readout ---
    if now - last_print >= 0.5:
        last_print = now
        print(
            "raw x={:+6.2f} y={:+6.2f} z={:+6.2f} | "
            "right={:+5.2f} bottom={:+5.2f} | tilt={:4.1f} deg | key {} {}".format(
                reading[0], reading[1], reading[2],
                right, down, tilt_degrees(right, down, reading[2]),
                lit, "(level)" if level else "",
            )
        )

    time.sleep(0.01)
