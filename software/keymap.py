# ===========================================================================
# keymap.py — what each of the 9 keys sends
# ===========================================================================
# EDIT THIS FILE TO CUSTOMISE YOUR KEYS. It lives on the CIRCUITPY drive, so
# just open it in a text editor, change an entry, and save — the badge reloads
# automatically (~1-2 s) and the new mapping is live. No re-flashing needed.
#
# The 9 entries map to the keys in this physical order (row by row):
#
#     KEYMAP[0]  KEYMAP[1]  KEYMAP[2]        top-left    top-mid    top-right
#     KEYMAP[3]  KEYMAP[4]  KEYMAP[5]   →    mid-left    centre     mid-right
#     KEYMAP[6]  KEYMAP[7]  KEYMAP[8]        bot-left    bot-mid    bot-right
#
# Each entry is ONE of:
#
#   {"key": "KEYPAD_SEVEN"}   A single key, held while you hold the button
#                             (true numpad behaviour, auto-repeats). The value
#                             is any name from Adafruit's Keycode list, e.g.
#                             "A", "ENTER", "F5", "UP_ARROW", "KEYPAD_FIVE".
#
#   {"text": "hello world"}   Types the whole string once when pressed.
#
#   {"combo": "CTRL-ALT-DELETE"}   A key combo (chord) sent once when pressed.
#                             Join with "-". Modifier aliases: CTRL/CONTROL,
#                             SHIFT, ALT/OPTION, GUI/CMD/WIN. Examples:
#                             "CTRL-C", "GUI-SPACE", "SHIFT-CTRL-T".
#
#   "just a string"           Shorthand for {"text": "just a string"}.
#
# Works the same over USB and over Bluetooth. (Over Bluetooth, very long "text"
# entries type visibly slowly, and unusual punctuation in "text" may not
# translate — use "combo" for control keys.)
#
# If this file is missing or has an error, the badge falls back to the default
# numpad below and prints the reason to the serial console.
# ===========================================================================

KEYMAP = [
    {"key": "KEYPAD_SEVEN"}, {"key": "KEYPAD_EIGHT"}, {"key": "KEYPAD_NINE"},
    {"key": "KEYPAD_FOUR"},  {"key": "KEYPAD_FIVE"},  {"key": "KEYPAD_SIX"},
    {"key": "KEYPAD_ONE"},   {"key": "KEYPAD_TWO"},   {"key": "KEYPAD_THREE"},
]
