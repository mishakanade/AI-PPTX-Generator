"""Predicting how much room a text needs, and shrinking it until it fits.

PowerPoint decides where lines wrap only when it opens the file, so by then it is too
late to notice that a title takes three lines and runs into the text below. This module
imitates the wrapping in advance: it knows the width of every character (font_metrics.json)
and breaks text into lines the same way PowerPoint does. Layouts use it to choose font
sizes and to stack blocks under each other without overlaps.
"""
import json
from functools import lru_cache
from pathlib import Path

from generator.render.primitives import Para, Text

POINTS_PER_INCH = 72
# Wrapping is computed for a slightly narrower box, as a margin for small differences
# between our character table and the fonts on the user's computer.
SAFETY = 0.96
BULLET_INDENT_EM = 1.1   # space reserved for the bullet mark, in units of the font size


@lru_cache(maxsize=1)
def _metrics():
    data = json.loads((Path(__file__).parent / "font_metrics.json").read_text(encoding="utf-8"))
    index = {ch: i for i, ch in enumerate(data["chars"])}
    return index, data["fonts"]


def _font_table(font, bold):
    index, fonts = _metrics()
    entry = fonts.get(font) or fonts["Arial"]    # unknown font: Arial is a slightly wide, safe guess
    return index, entry["bold" if bold else "regular"], entry["line_height"]


def line_height(font):
    """Height of one text line at single spacing, as a multiple of the font size."""
    return _font_table(font, False)[2]


def text_width(text, font, size, bold=False):
    """Width of a single unwrapped line of text, in inches."""
    index, widths, _ = _font_table(font, bold)
    default = 1000 if any(ord(ch) > 0x2E80 for ch in text) else 560   # CJK characters are square
    total = sum(widths[index[ch]] if ch in index else default for ch in text)
    return total / 1000 * size / POINTS_PER_INCH


def count_lines(text, font, size, width, bold=False):
    """How many lines the text takes when wrapped into the given width (inches)."""
    width *= SAFETY
    space = text_width(" ", font, size, bold)
    lines, current = 1, 0.0
    for word in text.split():
        w = text_width(word, font, size, bold)
        if w > width:
            # a single word longer than the line gets broken across several lines
            if current > 0:
                lines += 1
            lines += int(w // width)
            current = w % width
            continue
        needed = w if current == 0 else current + space + w
        if needed <= width:
            current = needed
        else:
            lines += 1
            current = w
    return lines


def _resolved(block, para, scale):
    """The actual font, size and boldness of a paragraph inside a Text block."""
    size = (para.size or block.size) * scale
    bold = block.bold if para.bold is None else para.bold
    return para.font or block.font, size, bold


def text_height(block, scale=1.0):
    """Height in inches that a Text block needs for all its paragraphs."""
    total = 0.0
    for i, para in enumerate(block.paragraphs):
        font, size, bold = _resolved(block, para, scale)
        width = block.w - (BULLET_INDENT_EM * size / POINTS_PER_INCH if para.bullet else 0)
        lines = count_lines(para.text, font, size, width, bold)
        total += lines * size * line_height(font) * block.line_spacing / POINTS_PER_INCH
        if i < len(block.paragraphs) - 1:
            gap = block.space_after if para.space_after is None else para.space_after
            total += gap * scale / POINTS_PER_INCH
    return total


def best_scale(block, limit=None, min_scale=0.55, max_scale=1.0, fill=0.85):
    """The factor by which a Text block's font sizes should be multiplied.

    Too much text: the factor goes below 1 until the text fits into `limit` (default: the
    block's own height). Little text and max_scale above 1: the factor grows, so that the
    text fills about `fill` of the available height instead of leaving the slide empty.
    """
    limit = block.h if limit is None else limit
    scale = 1.0
    if text_height(block, scale) > limit:
        while scale > min_scale and text_height(block, scale) > limit:
            scale -= 0.04
    else:
        while scale + 0.05 <= max_scale + 1e-9 and text_height(block, scale + 0.05) <= limit * fill:
            scale += 0.05
    return scale


def apply_scale(block, scale):
    """Multiply every font size and paragraph gap of a Text block by `scale`."""
    if abs(scale - 1.0) > 1e-9:
        block.size = round(block.size * scale, 1)
        block.space_after = round(block.space_after * scale, 1)
        for para in block.paragraphs:
            if para.size:
                para.size = round(para.size * scale, 1)
            if para.space_after:
                para.space_after = round(para.space_after * scale, 1)
    return block


def fit(block, min_scale=0.55, max_scale=1.0, fill=0.85):
    """Resize the text of a block so that it fits (and, if allowed, fills) its height."""
    return apply_scale(block, best_scale(block, None, min_scale, max_scale, fill))


def fit_single_line(text, font, size, width, bold=False, min_size=10):
    """Largest font size (not above `size`) at which the text fits on one line."""
    while size > min_size and text_width(text, font, size, bold) > width * SAFETY:
        size -= 1
    return size


def simple_text(x, y, w, h, text, **kwargs):
    """Shortcut: a Text block with a single paragraph."""
    return Text(x, y, w, h, [Para(str(text))], **kwargs)
