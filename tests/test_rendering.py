"""The layout checked against a real renderer: LibreOffice draws the slides, the PDF is read back.

test_layouts.py checks the layout engine's arithmetic; this checks that a real program
agrees with it (see render_check.py for how). Skipped where LibreOffice or PyMuPDF is
missing; on GitHub it runs in a job of its own that installs them.
"""
import copy
import io
import os

import pytest
from PIL import Image

from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU, SAMPLE_IMAGE, sample_photo
from generator.design.styles import STYLES
from generator.export import find_soffice
from generator.render.builder import build_slides
from generator.render.logo import LOGO_KEY
from generator.render.primitives import Text
from tests.render_check import contrast_problems, fonts_are_known, render_problems
from tests.stress_deck import IMG, STRESS_DECK
from tests.test_layouts import WIDE_LOGO, doubled

# On GitHub the job made for this check sets REQUIRE_RENDERING, so that there a missing
# program or font fails the check instead of quietly skipping it.
REQUIRED = bool(os.environ.get("REQUIRE_RENDERING"))


def skip(reason):
    if REQUIRED:
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(autouse=True)
def renderer():
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        skip("PyMuPDF is not installed")
    if not find_soffice():
        skip("LibreOffice is not installed")

IMAGES = {SAMPLE_IMAGE: sample_photo(), IMG: sample_photo(), LOGO_KEY: WIDE_LOGO}


def all_slides(style):
    """One long deck per style: long texts, every layout variant, a logo, and Russian text."""
    return (build_slides(STRESS_DECK, style, "Corporate Blue", IMAGES.keys(), logo=WIDE_LOGO)
            + build_slides(doubled(STRESS_DECK), style, "Dark Modern", IMAGES.keys())
            + build_slides(SAMPLE_DECK_RU, style, "Retro Cream", IMAGES.keys()))


@pytest.mark.parametrize("style", STYLES)
def test_libreoffice_draws_every_text_inside_its_box(style):
    fonts = {STYLES[style].heading_font, STYLES[style].body_font}
    if not fonts_are_known(fonts):
        skip(f"LibreOffice here would draw {fonts} with a font of other widths")
    problems = render_problems(all_slides(style), IMAGES)
    assert not problems, "\n".join(f"slide {n}: {p}" for n, p in problems)


def test_the_check_notices_text_that_does_not_fit():
    specs = build_slides(SAMPLE_DECK, "minimal", "Corporate Blue", [SAMPLE_IMAGE])
    broken = copy.deepcopy(specs[2])
    body = max((item for item in broken.items if isinstance(item, Text)), key=lambda t: t.h)
    body.h /= 3                                   # the same text, a third of the room
    moved = copy.deepcopy(specs[1])
    number = next(item for item in moved.items if isinstance(item, Text))   # the page number "02"
    number.x += 12                                # pushed beyond the right edge of the slide
    problems = [p for _, p in render_problems([broken, moved], IMAGES)]
    assert any("below its box" in p for p in problems)
    assert any("not drawn" in p and "02" in p for p in problems)    # LibreOffice drops it


def flat_photo(color):
    """The hardest photo for text on top of it: one flat colour, e.g. a white sky."""
    buffer = io.BytesIO()
    Image.new("RGB", (1600, 1000), color).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("theme, photo", [("Corporate Blue", (250, 250, 250)), ("Dark Modern", (5, 5, 5))])
def test_every_text_can_be_read_against_what_is_really_behind_it(style, theme, photo):
    """WCAG contrast (4.5, or 3 for large text) against the drawn background, photos included."""
    images = {SAMPLE_IMAGE: flat_photo(photo)}
    problems = contrast_problems(build_slides(SAMPLE_DECK, style, theme, images.keys()), images)
    assert not problems, "\n".join(f"slide {n}: {p}" for n, p in problems)


def test_the_contrast_check_notices_faint_text():
    spec = copy.deepcopy(build_slides(SAMPLE_DECK, "minimal", "Corporate Blue", [SAMPLE_IMAGE])[3])
    title = next(item for item in spec.items if isinstance(item, Text) and item.size > 20)
    title.color = (235, 238, 245)                      # nearly the colour of the background
    for para in title.paragraphs:
        para.color = None
    problems = contrast_problems([spec], IMAGES)
    assert any(title.paragraphs[0].text[:20] in p for _, p in problems)
