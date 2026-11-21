"""Putting the user's logo on every slide, in a corner where it covers nothing.

The logo is not part of any style: after a slide has been laid out, the corners are tried
in order (bottom right, bottom left, the same two a little higher, top right, top left) and
the logo goes into the first one that does not touch any text, photo or chart of that
slide. Decorative shapes (lines, bands, circles) and full-slide background photos may sit
under it. When there is a logo, content areas end a little higher (FOOTER_RESERVE) so that
the bottom corners are usually free. If every corner is taken, the slide has no logo.
"""
from io import BytesIO

from PIL import Image

from generator.render.primitives import SLIDE_H, SLIDE_W, ChartShape, Picture, Text
from generator.render.textfit import count_lines, text_height, text_width

LOGO_KEY = "__logo__"     # the key of the logo in the images dict
MAX_H = 0.36              # inches
MAX_W = 1.5
EDGE = 0.35               # distance from the slide edge
CLEARANCE = 0.12          # minimum gap to anything the logo must not touch
FOOTER_RESERVE = 0.45     # how much higher content areas end when there is a logo
RAISED = 0.45             # the extra corner positions sit this much above the bottom ones


def logo_aspect(data):
    """Width divided by height of the logo image. Raises ValueError if it is not an image."""
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as e:
        raise ValueError("not an image") from e
    return image.width / image.height


def occupied(item):
    """The rectangle (x, y, right, bottom) an item really covers.

    For a text block that is only the part its lines fill, which depends on its vertical
    alignment; pictures and charts cover their whole rectangle.
    """
    if isinstance(item, Text):
        used = min(text_height(item), item.h) if item.h else text_height(item)
        left, right = item.x, item.x + item.w
        if len(item.paragraphs) == 1:
            # a one-line label (a page number, a footer) covers only its real width, not its box
            para = item.paragraphs[0]
            font, size = para.font or item.font, para.size or item.size
            bold = item.bold if para.bold is None else para.bold
            if count_lines(para.text, font, size, item.w, bold) == 1:
                width = text_width(para.text, font, size, bold)
                if item.align == "right":
                    left = right - width
                elif item.align == "center":
                    left = item.x + (item.w - width) / 2
                right = left + width
        if item.valign == "middle":
            top = item.y + (item.h - used) / 2
        elif item.valign == "bottom":
            top = item.y + item.h - used
        else:
            top = item.y
        return left, top, right, top + used
    return item.x, item.y, item.x + item.w, item.y + item.h


def _overlaps(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def place_logo(spec, aspect):
    """Add the logo to one slide description, if a corner is free. Returns True if placed."""
    h = MAX_H
    w = h * aspect
    if w > MAX_W:                       # a very wide logo is limited by width instead
        w, h = MAX_W, MAX_W / aspect
    bottom, raised = SLIDE_H - EDGE - h, SLIDE_H - EDGE - h - RAISED
    corners = [
        (SLIDE_W - EDGE - w, bottom),   # bottom right
        (EDGE, bottom),                 # bottom left
        (SLIDE_W - EDGE - w, raised),   # a little higher: above a footer line
        (EDGE, raised),
        (SLIDE_W - EDGE - w, EDGE),     # top right
        (EDGE, EDGE),                   # top left
    ]
    taken = [occupied(item) for item in spec.items
             if isinstance(item, (Text, Picture, ChartShape)) and not _is_ornament(item)
             and not _is_background_photo(item)]
    for x, y in corners:
        rect = (x, y, x + w, y + h)
        if not any(_overlaps(rect, other, CLEARANCE) for other in taken):
            spec.items.append(Picture(x, y, w, h, LOGO_KEY, alt="Logo"))
            return True
    return False


def _is_background_photo(item):
    """A photo covering most of the slide is a background: a logo may sit on it, like on a cover."""
    return isinstance(item, Picture) and item.w * item.h > 0.6 * SLIDE_W * SLIDE_H


def _is_ornament(item):
    """Single big characters (the decorative quotation mark) do not block a corner."""
    return isinstance(item, Text) and len(item.paragraphs) == 1 and len(item.paragraphs[0].text.strip()) <= 1
