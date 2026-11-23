"""Small building blocks shared by the styles and the slide layouts."""
from dataclasses import dataclass

from generator.design.colors import Palette
from generator.render.primitives import Box, Para, Text
from generator.render.textfit import count_lines, text_height

MARGIN = 0.8   # distance from the slide edge to the content, in inches


@dataclass
class Area:
    """A rectangle on the slide that a layout is allowed to fill."""
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h


@dataclass
class Ctx:
    """Everything a layout needs to know besides the slide's own content."""
    palette: Palette
    style: object           # a Style from design/styles.py
    number: int             # position of the slide in the deck, the title slide is 1
    total: int              # number of slides in the deck
    deck_title: str
    images: set[str]        # keys of the pictures that were actually downloaded
    variant: int = 0        # 0 for the first slide of its type in the deck, 1 for the second...
    footer_reserve: float = 0.0   # inches kept free at the bottom of content areas (for a logo)


@dataclass
class CardLook:
    """How a style draws one card: its shapes, where the text goes and which colours to use."""
    items: list
    inner: Area
    heading_color: tuple
    text_color: tuple
    accent_color: tuple


def heading(text, x, y, w, font, size, color, bold=True, max_lines=2, min_size=None, align="left"):
    """A title that shrinks until it fits into `max_lines`; its height is measured and stored in .h."""
    min_size = min_size or round(size * 0.68)
    while size > min_size and count_lines(text, font, size, w, bold) > max_lines:
        size -= 1
    block = Text(x, y, w, 0, [Para(text)], font=font, size=size, color=color, bold=bold,
                 align=align, line_spacing=0.95)
    block.h = text_height(block)
    return block


def measured(block):
    """Set a Text block's height to exactly what its content needs."""
    block.h = text_height(block)
    return block


def stack(parts, top, bottom, valign="middle"):
    """Place blocks under each other between `top` and `bottom`.

    parts is a list of (block, gap_after) pairs; every block already knows its height.
    The group as a whole is aligned to the top, the middle or the bottom of the range.
    Returns the blocks in order.
    """
    total = sum(block.h + gap for block, gap in parts) - (parts[-1][1] if parts else 0)
    if valign == "top":
        y = top
    elif valign == "bottom":
        y = bottom - total
    else:
        y = top + (bottom - top - total) / 2
    y = max(top, y)
    placed = []
    for block, gap in parts:
        block.y = y
        y += block.h + gap
        placed.append(block)
    return placed


def shorten(text, limit=64):
    """Cut a long text for small labels such as the deck title in a footer."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def rule(x, y, w, color, thickness=0.02):
    """A horizontal line."""
    return Box(x, y, w, thickness, fill=color)
