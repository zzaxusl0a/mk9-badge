current_brightness = 0.3
pattern_index = 0

from rainbowio import colorwheel


def wheel_rgb(hue):
    """colorwheel() returns a packed 0xRRGGBB int; unpack it to an (r, g, b)
    tuple so the animation code can scale the channels."""
    c = colorwheel(hue)
    return ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
