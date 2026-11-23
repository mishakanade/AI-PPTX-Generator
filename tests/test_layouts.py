"""Geometry checks for every slide type in every style and several colour themes.

A slide description (SlideSpec) is just a list of rectangles, so its layout can be
checked with arithmetic, without drawing anything:
  - text and pictures stay inside the slide,
  - every text fits into its own box,
  - no two texts overlap.
"""
import itertools

import pytest

from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU, SAMPLE_IMAGE
from generator.design.styles import STYLES
from generator.render.builder import build_slides
from generator.render.primitives import SLIDE_H, SLIDE_W, ChartShape, Picture, Text
from generator.render.textfit import text_height
from tests.stress_deck import IMG, STRESS_DECK

THEMES = ["Corporate Blue", "Pure Black", "Retro Cream", "Cyberpunk"]


def doubled(deck):
    """Every slide twice in a row, so the second layout variant of every type is drawn too."""
    copy = deck.model_copy(deep=True)
    copy.slides = [slide for slide in deck.slides for _ in range(2)]
    return copy


DECKS = {
    "sample": (SAMPLE_DECK, [SAMPLE_IMAGE]),
    "sample-ru": (SAMPLE_DECK_RU, [SAMPLE_IMAGE]),
    "stress": (STRESS_DECK, [IMG]),
    "sample-x2": (doubled(SAMPLE_DECK), [SAMPLE_IMAGE]),
    "stress-x2": (doubled(STRESS_DECK), [IMG]),
}
EPS = 0.02   # inches; rounding tolerance


def occupied(block):
    """The part of a Text block's rectangle that its lines actually cover (y, bottom).

    Charts cover their whole rectangle.
    """
    if isinstance(block, (ChartShape, Picture)):
        return block.y, block.y + block.h
    used = min(text_height(block), block.h) if block.h else text_height(block)
    if block.valign == "middle":
        top = block.y + (block.h - used) / 2
    elif block.valign == "bottom":
        top = block.y + block.h - used
    else:
        top = block.y
    return top, top + used


def is_decoration(block):
    """Single characters (the big quotation mark) are ornaments drawn deliberately oversized."""
    return len(block.paragraphs) == 1 and len(block.paragraphs[0].text.strip()) <= 1


def describe(item):
    if isinstance(item, Picture):
        return "the logo"
    return "a chart" if isinstance(item, ChartShape) else repr(item.paragraphs[0].text[:30])


CASES = list(itertools.product(DECKS, STYLES, THEMES))


def logo_png(width, height):
    from io import BytesIO

    from PIL import Image
    buffer = BytesIO()
    Image.new("RGBA", (width, height), (200, 30, 30, 255)).save(buffer, "PNG")
    return buffer.getvalue()


WIDE_LOGO, SQUARE_LOGO = logo_png(600, 150), logo_png(200, 200)


@pytest.fixture(scope="module", params=CASES, ids=["-".join(c) for c in CASES])
def slides(request):
    deck_name, style, theme = request.param
    deck, images = DECKS[deck_name]
    # every other case has a logo, so its placement is checked by the same geometry tests
    logo = [None, WIDE_LOGO, SQUARE_LOGO][CASES.index(request.param) % 3]
    return build_slides(deck, style, theme, images, logo=logo)


def test_text_and_pictures_stay_on_the_slide(slides):
    for number, spec in enumerate(slides, 1):
        for item in spec.items:
            if isinstance(item, (Text, Picture, ChartShape)) and not (isinstance(item, Text) and is_decoration(item)):
                assert item.x >= -EPS and item.y >= -EPS, (number, item)
                assert item.x + item.w <= SLIDE_W + EPS, (number, item)
                bottom = occupied(item)[1] if isinstance(item, Text) else item.y + item.h
                assert bottom <= SLIDE_H + EPS, (number, item)


def test_every_text_fits_its_box(slides):
    for number, spec in enumerate(slides, 1):
        for item in spec.items:
            if isinstance(item, Text) and item.h > 0 and not is_decoration(item):
                needed = text_height(item)
                assert needed <= item.h + EPS, (
                    f"slide {number}: text needs {needed:.2f} in, box is {item.h:.2f} in: "
                    f"{item.paragraphs[0].text[:40]!r}"
                )


def test_texts_do_not_overlap(slides):
    for number, spec in enumerate(slides, 1):
        texts = [t for t in spec.items if isinstance(t, Text) and not is_decoration(t)]
        texts += [c for c in spec.items if isinstance(c, ChartShape)]   # nothing may be written over a chart
        texts += [p for p in spec.items if isinstance(p, Picture) and p.key == "__logo__"]   # nor over the logo
        for a, b in itertools.combinations(texts, 2):
            a_top, a_bottom = occupied(a)
            b_top, b_bottom = occupied(b)
            overlap_x = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            overlap_y = min(a_bottom, b_bottom) - max(a_top, b_top)
            assert overlap_x <= EPS or overlap_y <= EPS, (
                f"slide {number}: {describe(a)} overlaps {describe(b)}"
            )


def test_missing_photo_does_not_leave_a_hole():
    """A slide whose photo was not downloaded must not contain a Picture."""
    for style in STYLES:
        for spec in build_slides(STRESS_DECK, style, "Corporate Blue", []):
            assert not any(isinstance(item, Picture) for item in spec.items)


def test_the_logo_is_placed_on_most_slides_and_never_on_photos():
    from generator.render.logo import occupied
    placed = total = 0
    for style in STYLES:
        for spec in build_slides(STRESS_DECK, style, "Corporate Blue", [IMG], logo=WIDE_LOGO):
            total += 1
            logos = [p for p in spec.items if isinstance(p, Picture) and p.key == "__logo__"]
            placed += len(logos)
            photos = [p for p in spec.items if isinstance(p, Picture) and p.key != "__logo__"
                      and p.w * p.h < 0.6 * 13.333 * 7.5]          # full-slide background photos may hold it
            for logo in logos:
                assert logo.w <= 1.5 + EPS and logo.h <= 0.36 + EPS
                for photo in photos:
                    a, b = occupied(logo), occupied(photo)
                    assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
    assert placed / total > 0.95, f"logo on only {placed} of {total} slides"
