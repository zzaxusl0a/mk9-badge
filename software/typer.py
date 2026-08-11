# ===========================================================================
# typer.py — send keystrokes over USB HID and/or a Bluefruit LE UART Friend
# ===========================================================================
# Presents one uniform interface (press / release / release_all / type_text /
# combo) so the rest of the firmware never has to care whether it is typing
# over USB or Bluetooth.
#
#   UsbTyper  — wraps adafruit_hid.Keyboard (+ US layout for text macros)
#   BleTyper  — wraps setup.ble_uart, talking to the Friend with AT commands
#
# Two module-level singletons are created and the Bluetooth link is probed at
# import time:  usb_typer, ble_typer
# ===========================================================================

import time

from setup import ble_uart, BLE_UART_AVAILABLE

try:
    from adafruit_hid.keycode import Keycode
    _HAVE_KEYCODE = True
except Exception:      # pragma: no cover
    Keycode = None
    _HAVE_KEYCODE = False


# ---------------------------------------------------------------------------
# Key-name resolution (shared by keymap parsing and both typers)
# ---------------------------------------------------------------------------
_MOD_ALIASES = {
    "CTRL": "CONTROL", "CONTROL": "CONTROL", "CTL": "CONTROL",
    "SHIFT": "SHIFT",
    "ALT": "ALT", "OPTION": "ALT", "OPT": "ALT",
    "GUI": "GUI", "CMD": "GUI", "COMMAND": "GUI", "WIN": "GUI",
    "WINDOWS": "GUI", "SUPER": "GUI", "META": "GUI",
}

_KEY_ALIASES = {
    "ESC": "ESCAPE", "DEL": "DELETE", "SPACE": "SPACEBAR",
    "ENTER": "ENTER", "RETURN": "RETURN",
    "PGUP": "PAGE_UP", "PGDN": "PAGE_DOWN",
    "UP": "UP_ARROW", "DOWN": "DOWN_ARROW",
    "LEFT": "LEFT_ARROW", "RIGHT": "RIGHT_ARROW",
}

_DIGIT_NAMES = {
    "0": "ZERO", "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR",
    "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE",
}


def resolve_keycode(name):
    """Return the integer Keycode for a friendly name, or None if unknown."""
    if name is None or not _HAVE_KEYCODE:
        return None
    key = str(name).strip().upper()
    if key in _MOD_ALIASES:
        key = _MOD_ALIASES[key]
    elif key in _KEY_ALIASES:
        key = _KEY_ALIASES[key]
    elif key in _DIGIT_NAMES:
        key = _DIGIT_NAMES[key]
    try:
        return getattr(Keycode, key)
    except AttributeError:
        print("keymap: unknown key name:", name)
        return None


def parse_combo(spec):
    """Turn 'CTRL-ALT-DELETE' into a list of Keycode ints (modifiers + keys)."""
    codes = []
    for token in str(spec).split("-"):
        token = token.strip()
        if not token:
            continue
        code = resolve_keycode(token)
        if code is not None:
            codes.append(code)
    return codes


def _split_modifiers(codes):
    """Split keycodes into (HID modifier bitmask, list of normal keycodes)."""
    mod = 0
    keys = []
    for c in codes:
        if 0xE0 <= c <= 0xE7:
            mod |= 1 << (c - 0xE0)
        else:
            keys.append(c)
    return mod, keys


# ---------------------------------------------------------------------------
# USB HID
# ---------------------------------------------------------------------------
class UsbTyper:
    def __init__(self):
        self.available = False
        self._kbd = None
        self._layout = None
        try:
            import usb_hid
            from adafruit_hid.keyboard import Keyboard
            self._kbd = Keyboard(usb_hid.devices)
            self.available = True
            try:
                from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
                self._layout = KeyboardLayoutUS(self._kbd)
            except Exception as e:
                print("typer: US layout unavailable, text macros disabled on USB:", e)
        except Exception as e:
            print("typer: USB HID unavailable:", e)

    def press(self, code):
        if self.available and code is not None:
            try:
                self._kbd.press(code)
            except Exception:
                pass

    def release(self, code):
        if self.available and code is not None:
            try:
                self._kbd.release(code)
            except Exception:
                pass

    def release_all(self):
        if self.available:
            try:
                self._kbd.release_all()
            except Exception:
                pass

    def type_text(self, text):
        if self.available and self._layout is not None:
            try:
                self._layout.write(text)
            except Exception:
                pass

    def combo(self, codes):
        if self.available and codes:
            try:
                self._kbd.send(*codes)   # presses then releases modifiers + keys
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Bluetooth (Bluefruit LE UART Friend, AT command set)
# ---------------------------------------------------------------------------
class BleTyper:
    def __init__(self):
        self._uart = ble_uart
        self.ble_ready = False     # True only after a module actually answers
        self._pressed = []         # currently-held keycodes (max 6)

    # -- low-level AT helpers ------------------------------------------------
    def _write(self, cmd):
        if self._uart is None:
            return
        try:
            self._uart.reset_input_buffer()   # drop any stale "OK" replies
        except Exception:
            pass
        try:
            self._uart.write((cmd + "\r\n").encode())
        except Exception:
            pass

    def _read_reply(self, timeout=0.3):
        if self._uart is None:
            return b""
        deadline = time.monotonic() + timeout
        buf = b""
        while time.monotonic() < deadline:
            try:
                chunk = self._uart.read(32)
            except Exception:
                chunk = None
            if chunk:
                buf += chunk
                if b"OK" in buf or b"ERROR" in buf:
                    break
        return buf

    # -- lifecycle -----------------------------------------------------------
    def begin(self):
        """Probe for a Friend and, if present, enable BLE HID keyboard mode."""
        self.ble_ready = False
        if not BLE_UART_AVAILABLE or self._uart is None:
            return
        if self._probe():
            self._write("AT+GAPDEVNAME=MK9 Badge")
            self._read_reply()
            self._write("AT+BLEKEYBOARDEN=1")
            self._read_reply()
            self._write("ATZ")                 # reset so the HID service advertises
            self._read_reply(timeout=1.0)
            self.ble_ready = True
        else:
            print("typer: no Bluefruit module detected on SAO1 (BLE disabled)")

    def _probe(self):
        for _ in range(3):
            self._write("AT")
            if b"OK" in self._read_reply(timeout=0.4):
                return True
        return False

    # -- typing --------------------------------------------------------------
    def _send_report(self):
        mod, keys = _split_modifiers(self._pressed)
        parts = ["%02X" % mod, "00"]
        for k in keys[:6]:
            parts.append("%02X" % k)
        self._write("AT+BLEKEYBOARDCODE=" + "-".join(parts))

    def press(self, code):
        if not self.ble_ready or code is None:
            return
        if code not in self._pressed and len(self._pressed) < 6:
            self._pressed.append(code)
        self._send_report()

    def release(self, code):
        if not self.ble_ready or code is None:
            return
        if code in self._pressed:
            self._pressed.remove(code)
        self._send_report()

    def release_all(self):
        self._pressed = []
        if self.ble_ready:
            self._write("AT+BLEKEYBOARDCODE=00-00")

    def type_text(self, text):
        if self.ble_ready:
            self._write("AT+BLEKEYBOARD=" + text)

    def combo(self, codes):
        if not self.ble_ready or not codes:
            return
        mod, keys = _split_modifiers(codes)
        parts = ["%02X" % mod, "00"]
        for k in keys[:6]:
            parts.append("%02X" % k)
        self._write("AT+BLEKEYBOARDCODE=" + "-".join(parts))
        self._write("AT+BLEKEYBOARDCODE=00-00")   # release


# ---------------------------------------------------------------------------
# Singletons — created and probed once at import
# ---------------------------------------------------------------------------
usb_typer = UsbTyper()
ble_typer = BleTyper()
ble_typer.begin()
