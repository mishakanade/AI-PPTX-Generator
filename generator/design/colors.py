"""Colour maths: turning the four colours of a theme into everything a design needs.

A theme only defines bg / title / text / accent. A real design also needs a card
background, a muted colour for captions, a thin line colour, a text colour that is
readable on top of the accent... `make_palette` derives all of those, so they work
for any of the themes, light or dark.

Colours are plain (r, g, b) tuples with values 0-255.
"""
from dataclasses import dataclass

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def mix(a, b, t):
    """Blend colour a towards colour b: t=0 gives a, t=1 gives b."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def luminance(color):
    """Perceived brightness from 0 (black) to 1 (white), by the WCAG formula."""
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """Contrast ratio between two colours: 1 = identical, 21 = black on white."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def readable_on(background, dark=(22, 24, 30), light=WHITE):
    """Pick the dark or the light text colour, whichever is easier to read on the background."""
    return dark if contrast(dark, background) >= contrast(light, background) else light


def ensure_contrast(color, background, toward, target=3.5):
    """Move `color` step by step towards `toward` until it is readable on `background`."""
    for step in range(11):
        candidate = mix(color, toward, step / 10)
        if contrast(candidate, background) >= target:
            return candidate
    return toward


def from_hex(value):
    """'#1A2B3C' -> (26, 43, 60)."""
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def readable_theme(bg, title, text, accent):
    """A theme from colours the user picked, adjusted where they would be hard to read.

    Titles and body text need a contrast of 4.5 against the background (the usual
    accessibility level for text), the accent 3. A colour that falls short is moved step
    by step towards black or white, whichever the background needs.
    Returns (theme dict, names of the colours that were changed).
    """
    toward = BLACK if luminance(bg) > 0.35 else WHITE
    theme = {
        "bg": bg,
        "title": ensure_contrast(title, bg, toward, target=4.5),
        "text": ensure_contrast(text, bg, toward, target=4.5),
        "accent": ensure_contrast(accent, bg, toward, target=3.0),
    }
    changed = [name for name, picked in (("title", title), ("text", text), ("accent", accent))
               if theme[name] != picked]
    return theme, changed


def to_hex(color):
    return "#{:02x}{:02x}{:02x}".format(*color)


@dataclass(frozen=True)
class Palette:
    # the four colours of the theme
    bg: tuple
    title: tuple
    text: tuple
    accent: tuple
    # derived colours
    is_dark: bool          # is the background dark?
    surface: tuple         # card background, slightly different from bg
    surface_strong: tuple  # a more noticeable block (table header stripes, tags)
    accent_soft: tuple     # a pale tint of the accent, for large decorative areas
    muted: tuple           # captions, page numbers
    line: tuple            # thin separators and outlines
    on_accent: tuple       # text placed on top of the accent colour
    deep: tuple            # a dark, saturated block colour for covers and header bands
    on_deep: tuple         # text placed on top of `deep`
    accent_on_deep: tuple  # the accent, lightened if needed so it stays visible on `deep`
    accent_end: tuple      # second colour of accent gradients: a darker accent, or a lighter one
                           # for very bright accents (dark yellow or dark neon green look muddy)
    on_accent_end: tuple   # text placed on an accent -> accent_end gradient (readable on both ends)
    bg_tint: tuple         # the background with a hint of the accent, for background gradients


def make_palette(theme):
    """Build a Palette from a theme dict {"bg", "title", "text", "accent"}."""
    bg, title, text, accent = (tuple(theme[key]) for key in ("bg", "title", "text", "accent"))
    is_dark = luminance(bg) < 0.25
    if is_dark:
        surface = mix(bg, WHITE, 0.07)
        surface_strong = mix(bg, WHITE, 0.14)
        # On a dark background a darker block would be invisible (nothing is darker than
        # black), so the "deep" block is the background lifted with a little accent colour.
        deep = mix(mix(bg, WHITE, 0.06), accent, 0.16)
    else:
        surface = mix(bg, title, 0.05)
        surface_strong = mix(bg, title, 0.11)
        deep = title
    on_deep = readable_on(deep)
    if luminance(accent) > 0.35:
        accent_end = mix(accent, WHITE, 0.35)
    else:
        accent_end = mix(accent, deep if not is_dark else BLACK, 0.35)
    return Palette(
        bg=bg, title=title, text=text, accent=accent,
        is_dark=is_dark,
        surface=surface,
        surface_strong=surface_strong,
        accent_soft=mix(bg, accent, 0.14),
        # small text (captions, page numbers): WCAG asks 4.5 for text this size
        muted=ensure_contrast(mix(text, bg, 0.38), bg, toward=text, target=4.5),
        line=mix(bg, text, 0.22),
        on_accent=readable_on(accent),
        deep=deep,
        on_deep=on_deep,
        accent_on_deep=ensure_contrast(accent, deep, toward=on_deep),
        accent_end=accent_end,
        on_accent_end=max((WHITE, (22, 24, 30)),
                          key=lambda ink: min(contrast(ink, accent), contrast(ink, accent_end))),
        bg_tint=mix(bg, accent, 0.12 if is_dark else 0.22),
    )


def series_colors(palette, count):
    """Colours for chart series or pie slices: the accent first, then calmer relatives of it."""
    p = palette
    strong = p.title if contrast(p.title, p.bg) >= 3 else p.text
    base = [
        p.accent, strong, mix(p.accent, p.bg, 0.45), mix(strong, p.bg, 0.45),
        mix(p.accent, strong, 0.5), mix(p.accent, p.bg, 0.7), p.muted, mix(strong, p.bg, 0.7),
    ]
    return [base[i % len(base)] for i in range(count)]
