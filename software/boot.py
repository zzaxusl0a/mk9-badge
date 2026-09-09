# Runs once per hard reset, before code.py, and is the only place USB can be
# reconfigured — descriptors are frozen once the host enumerates us.
#
# Default: HID keyboard + USB serial console only. No mass storage, so the
# badge is a plain keyboard on machines whose policy blocks USB drives.
#
# To get the CIRCUITPY drive back: hold the bottom-left key and tap RESET (SW3),
# or hold it while plugging in USB-C. A hard reset re-runs this file; auto-reload
# after a file save does NOT, so the drive stays as it is until the next reset.
#
# If anything below fails, the drive is left enabled — see _expose.

import board
import digitalio
import time
import usb_hid

usb_hid.enable((usb_hid.Device.KEYBOARD,))

# Matrix pins and numbering mirror setup.py: key_number = row * 3 + col.
_ROW_PINS = (board.GP27, board.GP26, board.GP16)   # R0, R1, R2
_COL_PINS = (board.GP17, board.GP13, board.GP0)    # C0, C1, C2
_GATE_KEY = 6                                      # bottom-left (C0R2)

_SAMPLES = 6        # every sample must read pressed
_SAMPLE_GAP = 0.005 # ~30 ms total, plenty for an already-held key


def _key_held(key_number):
    """True if key_number is held right now, read without the keypad module.

    setup.py uses columns_to_anodes=True, i.e. the diode anode is on the column,
    so conduction is column -> row: drive the column high, pull the row down,
    and pressed reads high. Only one column and one row are ever claimed, so no
    ghosting is possible and the other four matrix pins stay high-Z.
    """
    col = None
    row = None
    try:
        col = digitalio.DigitalInOut(_COL_PINS[key_number % 3])
        row = digitalio.DigitalInOut(_ROW_PINS[key_number // 3])
        col.switch_to_output(value=True, drive_mode=digitalio.DriveMode.PUSH_PULL)
        row.switch_to_input(pull=digitalio.Pull.DOWN)
        time.sleep(0.001)
        for _ in range(_SAMPLES):
            if not row.value:
                return False
            time.sleep(_SAMPLE_GAP)
        return True
    finally:
        # Must release both pins or setup.py's KeyMatrix hits "pin in use" —
        # a crash after the drive is already hidden is the worst ordering.
        if row is not None:
            row.deinit()
        if col is not None:
            col.deinit()


# Fail-safe default: only a clean run of the gate hides the drive.
_expose = True
try:
    _expose = _key_held(_GATE_KEY)
    if not _expose:
        import storage
        storage.disable_usb_drive()
        # Nothing here uses MIDI, but CircuitPython advertises it by default.
        import usb_midi
        usb_midi.disable()
except Exception as err:  # never let this file lock anyone out
    _expose = True
    print("boot: storage gate failed, leaving CIRCUITPY enabled:", err)

# The only diagnostic once the drive is hidden. Lands in boot_out.txt too.
print("boot: CIRCUITPY drive", "ENABLED" if _expose else "hidden (HID-only)")
