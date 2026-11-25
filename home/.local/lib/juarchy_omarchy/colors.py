"""Turn an Omarchy ``colors.toml`` palette into a Caelestia colour scheme.

Omarchy themes describe a terminal-style palette (background, foreground,
accent, the eight ANSI hues and their bright twins).  Juarchy's shell is
built on Material 3 roles, so every role is derived from that palette:

* surfaces, text and the accent come straight from the theme;
* the terminal colours use Omarchy's own ANSI mapping, unchanged;
* anything the palette does not spell out (containers, "on" colours) is
  mixed from theme colours and checked for readable contrast.
"""
import colorsys
import re
import tomllib
from pathlib import Path

HEX = re.compile(r'^[0-9a-f]{6}$')
WHITE = 'ffffff'
BLACK = '000000'

# Omarchy themes always ship these.  The rest have fallbacks below.
REQUIRED = ('background', 'foreground', 'accent')
HUES = ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')
# Palette hues offered to the Material "tertiary" role, in preference order.
TERTIARY_CANDIDATES = ('blue', 'magenta', 'cyan', 'green', 'yellow', 'orange')
# Smallest lightness step between neighbouring surface layers.
MIN_LAYER_STEP = 0.002


def normalise(value):
    """Return ``rrggbb`` for ``#rrggbb``, ``rrggbb``, ``#rgb`` or ``#rrggbbaa``."""
    text = str(value).strip().lstrip('#').lower()
    if len(text) == 3:
        text = ''.join(c * 2 for c in text)
    if len(text) == 8:
        text = text[:6]
    if not HEX.match(text):
        raise ValueError('Not a colour: %r' % (value,))
    return text


def to_rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))


def from_rgb(rgb):
    return ''.join('%02x' % max(0, min(255, round(channel))) for channel in rgb)


def mix(first, second, amount):
    """Blend ``first`` towards ``second``; 0 keeps ``first``, 1 gives ``second``."""
    a, b = to_rgb(first), to_rgb(second)
    return from_rgb(x * (1 - amount) + y * amount for x, y in zip(a, b))


def luminance(colour):
    def linear(channel):
        channel /= 255
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in to_rgb(colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first, second):
    a, b = sorted((luminance(first), luminance(second)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def saturation(colour):
    return colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(colour)))[1]


def hue_distance(first, second):
    a = colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(first)))[0] * 360
    b = colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(second)))[0] * 360
    gap = abs(a - b) % 360
    return min(gap, 360 - gap)


def best_on(colour, options, wanted=4.5):
    """The first option readable on ``colour``, else whichever reads best."""
    for option in options:
        if contrast(colour, option) >= wanted:
            return option
    return max(options, key=lambda option: contrast(colour, option))


def with_contrast(colour, against, minimum, towards):
    """Push ``colour`` towards ``towards`` until it contrasts enough with ``against``."""
    for step in range(21):
        candidate = mix(colour, towards, step / 20)
        if contrast(candidate, against) >= minimum:
            return candidate
    return towards


def load_palette(path):
    """Read and complete an Omarchy ``colors.toml``.

    Returns a dict of ``rrggbb`` strings plus ``mode`` ('dark' or 'light').
    """
    with Path(path).open('rb') as stream:
        raw = tomllib.load(stream)
    palette = {}
    for key, value in raw.items():
        if key == 'mode':
            continue
        if isinstance(value, str):
            try:
                palette[key] = normalise(value)
            except ValueError:
                continue  # Border gradients and similar are not plain colours.
    for key in REQUIRED:
        if key not in palette:
            raise ValueError('colors.toml is missing "%s"' % key)
    mode = raw.get('mode')
    if mode not in ('dark', 'light'):
        mode = 'dark' if luminance(palette['background']) < 0.5 else 'light'
    palette['mode'] = mode
    return complete(palette)


def complete(palette):
    """Fill the optional keys Omarchy themes may leave out."""
    p = dict(palette)
    bg, fg = p['background'], p['foreground']
    dark = p['mode'] == 'dark'
    p.setdefault('dark_background', mix(bg, BLACK, 0.25 if dark else 0.06))
    p.setdefault('darker_background', mix(bg, BLACK, 0.45 if dark else 0.12))
    p.setdefault('lighter_background', mix(bg, fg, 0.08))
    p.setdefault('selection', mix(bg, fg, 0.16))
    p.setdefault('muted', mix(bg, fg, 0.38))
    p.setdefault('dark_foreground', mix(fg, bg, 0.4))
    p.setdefault('light_foreground', mix(fg, WHITE, 0.15))
    p.setdefault('bright_foreground', mix(fg, WHITE, 0.3))
    defaults = {'red': 'e06c75', 'green': '98c379', 'yellow': 'e5c07b',
                'blue': '61afef', 'magenta': 'c678dd', 'cyan': '56b6c2'}
    for hue in HUES:
        p.setdefault(hue, defaults[hue])
        p.setdefault('bright_' + hue, mix(p[hue], WHITE, 0.25))
    p.setdefault('orange', p['bright_yellow'])
    p.setdefault('brown', mix(p['red'], p['yellow'], 0.5))
    return p


def separated(anchors, foreground):
    """Keep the theme's own surface colours, nudging one only if it would merge with the last.

    Some themes give two layers the same colour (vantablack, solitude).  The
    ramp has to keep rising for dark themes and falling for light ones, so a
    colour too close to the one before it moves towards the text colour.
    """
    result = [anchors[0]]
    rising = luminance(foreground) > luminance(anchors[0])
    for colour in anchors[1:]:
        previous = luminance(result[-1])
        for step in range(41):
            candidate = mix(colour, foreground, step / 40 * 0.6)
            gap = luminance(candidate) - previous
            if (gap >= MIN_LAYER_STEP) if rising else (gap <= -MIN_LAYER_STEP):
                colour = candidate
                break
        result.append(colour)
    return result


def surface_layers(p):
    """Material surface ramp, ordered from the surface outwards.

    Dark themes get lighter layers, light themes darker ones.  Omarchy's
    ``lighter_background`` and ``selection`` (``dark_background`` and
    ``darker_background`` for light themes) are the container and highest
    layers exactly; the layers between are halfway.
    """
    bg, fg = p['background'], p['foreground']
    if p['mode'] == 'dark':
        lowest = p['darker_background']
        if luminance(lowest) >= luminance(bg):
            lowest = bg
        dim = p['dark_background'] if luminance(p['dark_background']) <= luminance(bg) else bg
        container, highest = separated([bg, p['lighter_background'], p['selection']], fg)[1:]
        bright = highest
    else:
        lowest = mix(bg, WHITE, 0.6)
        dim = p['dark_background'] if luminance(p['dark_background']) <= luminance(bg) else bg
        container, highest = separated([bg, p['dark_background'], p['darker_background']], fg)[1:]
        bright = bg
    return {'lowest': lowest, 'dim': dim, 'bright': bright,
            'low': mix(bg, container, 0.5), 'container': container,
            'high': mix(container, highest, 0.5), 'highest': highest}


def pick_tertiary(p):
    """A palette hue that stands apart from the accent, for Material's tertiary."""
    accent, bg = p['accent'], p['background']
    chosen = []
    for name in TERTIARY_CANDIDATES:
        colour = p[name]
        if contrast(colour, bg) < 3 or saturation(colour) < 0.2:
            continue
        if saturation(accent) >= 0.2 and hue_distance(colour, accent) < 40:
            continue
        chosen.append(colour)
        break
    return chosen[0] if chosen else p['bright_magenta']


def build_colours(palette):
    """Every colour a Caelestia scheme carries, from a completed palette."""
    p = palette
    dark = p['mode'] == 'dark'
    bg, fg, accent = p['background'], p['foreground'], p['accent']
    layers = surface_layers(p)
    readable = [bg, fg, BLACK, WHITE]

    def on(colour):
        return best_on(colour, readable)

    def container(colour):
        tint = mix(colour, bg, 0.7)
        return tint, best_on(tint, [fg, bg, WHITE, BLACK])

    secondary = mix(accent, fg, 0.35)
    tertiary = pick_tertiary(p)
    error = p['red']
    success = p['green']
    primary_container, on_primary_container = container(accent)
    secondary_container, on_secondary_container = container(secondary)
    tertiary_container, on_tertiary_container = container(tertiary)
    error_container, on_error_container = container(error)
    success_container, on_success_container = container(success)
    on_surface_variant = with_contrast(mix(fg, bg, 0.2), bg, 5.0, fg)
    outline = with_contrast(p['muted'], bg, 2.6, fg)
    outline_variant = p['selection'] if abs(luminance(p['selection']) - luminance(bg)) > MIN_LAYER_STEP \
        else mix(bg, fg, 0.18)
    fixed_dark = mix(accent, BLACK, 0.6)
    neutral = mix(fg, bg, 0.55)

    colours = {
        'primary_paletteKeyColor': accent,
        'secondary_paletteKeyColor': secondary,
        'tertiary_paletteKeyColor': tertiary,
        'neutral_paletteKeyColor': neutral,
        'neutral_variant_paletteKeyColor': mix(neutral, accent, 0.15),
        'background': bg,
        'onBackground': fg,
        'surface': bg,
        'surfaceDim': layers['dim'],
        'surfaceBright': layers['bright'],
        'surfaceContainerLowest': layers['lowest'],
        'surfaceContainerLow': layers['low'],
        'surfaceContainer': layers['container'],
        'surfaceContainerHigh': layers['high'],
        'surfaceContainerHighest': layers['highest'],
        'onSurface': fg,
        'surfaceVariant': outline_variant,
        'onSurfaceVariant': on_surface_variant,
        'inverseSurface': fg,
        'inverseOnSurface': bg,
        'outline': outline,
        'outlineVariant': outline_variant,
        'shadow': BLACK,
        'scrim': BLACK,
        'surfaceTint': accent,
        'primary': accent,
        'onPrimary': on(accent),
        'primaryContainer': primary_container,
        'onPrimaryContainer': on_primary_container,
        'inversePrimary': mix(accent, bg, 0.45),
        'secondary': secondary,
        'onSecondary': on(secondary),
        'secondaryContainer': secondary_container,
        'onSecondaryContainer': on_secondary_container,
        'tertiary': tertiary,
        'onTertiary': on(tertiary),
        'tertiaryContainer': tertiary_container,
        'onTertiaryContainer': on_tertiary_container,
        'error': error,
        'onError': on(error),
        'errorContainer': error_container,
        'onErrorContainer': on_error_container,
        'primaryFixed': mix(accent, WHITE, 0.7),
        'primaryFixedDim': accent,
        'onPrimaryFixed': fixed_dark,
        'onPrimaryFixedVariant': mix(accent, BLACK, 0.45),
        'secondaryFixed': mix(secondary, WHITE, 0.7),
        'secondaryFixedDim': secondary,
        'onSecondaryFixed': mix(secondary, BLACK, 0.6),
        'onSecondaryFixedVariant': mix(secondary, BLACK, 0.45),
        'tertiaryFixed': mix(tertiary, WHITE, 0.7),
        'tertiaryFixedDim': tertiary,
        'onTertiaryFixed': mix(tertiary, BLACK, 0.6),
        'onTertiaryFixedVariant': mix(tertiary, BLACK, 0.45),
        # Omarchy's own ANSI mapping (default/themed/alacritty.toml.tpl).
        'term0': bg,
        'term1': p['red'],
        'term2': p['green'],
        'term3': p['yellow'],
        'term4': p['blue'],
        'term5': p['magenta'],
        'term6': p['cyan'],
        'term7': fg,
        'term8': p['muted'],
        'term9': p['bright_red'],
        'term10': p['bright_green'],
        'term11': p['bright_yellow'],
        'term12': p['bright_blue'],
        'term13': p['bright_magenta'],
        'term14': p['bright_cyan'],
        'term15': p['bright_foreground'],
        # Catppuccin-style names some app templates look for.
        'rosewater': mix(p['red'], fg, 0.55),
        'flamingo': mix(p['red'], fg, 0.3),
        'pink': mix(p['magenta'], p['red'], 0.35),
        'mauve': p['magenta'],
        'red': p['red'],
        'maroon': mix(p['red'], p['brown'], 0.4),
        'peach': p['orange'],
        'yellow': p['yellow'],
        'green': p['green'],
        'teal': p['cyan'],
        'sky': p['bright_cyan'],
        'sapphire': mix(p['cyan'], p['blue'], 0.5),
        'blue': p['blue'],
        'lavender': mix(p['blue'], p['magenta'], 0.4),
        'klink': p['blue'],
        'klinkSelection': p['bright_blue'],
        'kvisited': p['magenta'],
        'kvisitedSelection': p['bright_magenta'],
        'knegative': p['red'],
        'knegativeSelection': p['bright_red'],
        'kneutral': p['yellow'],
        'kneutralSelection': p['bright_yellow'],
        'kpositive': p['green'],
        'kpositiveSelection': p['bright_green'],
        'text': fg,
        'subtext1': mix(fg, bg, 0.15),
        'subtext0': mix(fg, bg, 0.3),
        'overlay2': mix(fg, bg, 0.45),
        'overlay1': mix(fg, bg, 0.55),
        'overlay0': mix(fg, bg, 0.65),
        'surface2': layers['highest'],
        'surface1': layers['container'],
        'surface0': layers['low'],
        'base': bg,
        'mantle': layers['dim'],
        'crust': layers['lowest'],
        'success': success,
        'onSuccess': on(success),
        'successContainer': success_container,
        'onSuccessContainer': on_success_container,
    }
    return colours


def scheme_for(theme_id, palette):
    """A complete Caelestia ``scheme.json`` payload for an Omarchy theme."""
    return {
        'name': theme_id,
        'flavour': 'omarchy',
        'mode': palette['mode'],
        'variant': 'tonalspot',
        'colours': build_colours(palette),
    }
