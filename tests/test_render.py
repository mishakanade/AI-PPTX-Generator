"""The finished outputs: the .pptx file and the HTML preview."""
from io import BytesIO

import pytest
from pptx import Presentation

from generator.content.schema import Deck, Slide
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo, sample_photo_url
from generator.design.styles import STYLES
from generator.export import find_soffice, to_pdf
from generator.render.builder import build_pptx, build_preview


def test_pptx_opens_and_has_a_slide_per_content_slide_plus_title():
    for style in STYLES:
        data = build_pptx(SAMPLE_DECK, style, "Corporate Blue", {SAMPLE_IMAGE: sample_photo()})
        presentation = Presentation(BytesIO(data))
        assert len(presentation.slides) == len(SAMPLE_DECK.slides) + 1
        assert presentation.core_properties.title == SAMPLE_DECK.title


def test_photo_credits_go_into_speaker_notes():
    data = build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {SAMPLE_IMAGE: sample_photo()},
                      credits={SAMPLE_IMAGE: "Photo by Jane Doe on Unsplash"})
    notes = [s.notes_slide.notes_text_frame.text for s in Presentation(BytesIO(data)).slides if s.has_notes_slide]
    assert "Photo by Jane Doe on Unsplash" in notes


def test_unknown_style_and_theme_fall_back_to_defaults():
    data = build_pptx(SAMPLE_DECK, "no-such-style", "no-such-theme", {})
    assert len(Presentation(BytesIO(data)).slides) == len(SAMPLE_DECK.slides) + 1


def test_preview_escapes_text_from_the_model():
    deck = Deck(title="<script>alert(1)</script>", subtitle="",
                slides=[Slide(type="bullets", title="<b>x</b>", bullets=["<img src=x onerror=alert(1)>"])])
    html = "".join(build_preview(deck, "minimal", "Corporate Blue", {}))
    assert "<script>" not in html and "<img" not in html and "<b>" not in html
    assert "&lt;script&gt;" in html


def test_preview_has_one_snippet_per_slide_and_shows_the_photo():
    slides = build_preview(SAMPLE_DECK, "soft", "Dark Modern", {SAMPLE_IMAGE: sample_photo_url()})
    assert len(slides) == len(SAMPLE_DECK.slides) + 1
    assert any("data:image/jpeg;base64," in s for s in slides)


def test_speaker_notes_come_before_the_photo_credit():
    deck = SAMPLE_DECK.model_copy(deep=True)
    deck.notes = "Welcome everyone."
    index = next(i for i, slide in enumerate(deck.slides) if slide.image_keyword == SAMPLE_IMAGE)
    deck.slides[index].notes = "Cities are growing fast."
    data = build_pptx(deck, "minimal", "Corporate Blue", {SAMPLE_IMAGE: sample_photo()},
                      credits={SAMPLE_IMAGE: "Photo by Jane Doe on Unsplash"})
    slides = Presentation(BytesIO(data)).slides
    assert slides[0].notes_slide.notes_text_frame.text == "Welcome everyone."
    photo_slide = slides[index + 1]                     # +1: the title slide comes first
    assert photo_slide.notes_slide.notes_text_frame.text == "Cities are growing fast.\n\nPhoto by Jane Doe on Unsplash"


def test_charts_are_embedded_as_pictures_in_the_preview():
    """Streamlit removes inline <svg>; the chart must travel as an <img> with an SVG data URL."""
    index = next(i for i, slide in enumerate(SAMPLE_DECK.slides) if slide.type == "chart")
    html = build_preview(SAMPLE_DECK, "minimal", "Corporate Blue", {})[index + 1]
    assert "<svg" not in html and 'src="data:image/svg+xml;base64,' in html


def test_custom_colours_are_used_and_made_readable():
    from generator.design.colors import contrast, readable_theme
    theme, changed = readable_theme((240, 240, 240), (200, 200, 200), (180, 180, 180), (230, 230, 120))
    assert set(changed) == {"title", "text", "accent"}
    assert contrast(theme["text"], theme["bg"]) >= 4.5 and contrast(theme["accent"], theme["bg"]) >= 3
    data = build_pptx(SAMPLE_DECK, "minimal", theme, {})
    background = Presentation(BytesIO(data)).slides[0].background.fill.fore_color.rgb
    assert tuple(background) == (240, 240, 240)


def test_photos_have_alternative_text():
    data = build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {SAMPLE_IMAGE: sample_photo()})
    descriptions = [shape._element.nvPicPr.cNvPr.get("descr")
                    for slide in Presentation(BytesIO(data)).slides for shape in slide.shapes
                    if shape.shape_type == 13]
    assert descriptions and all(d == SAMPLE_IMAGE for d in descriptions)


def test_transitions_are_written_into_every_slide():
    data = build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {}, transition="push")
    for slide in Presentation(BytesIO(data)).slides:
        transition = slide._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}transition")
        assert transition is not None and transition[0].tag.endswith("push")
    plain = build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {})
    assert b"transition" not in b"".join(
        s._element.xml.encode() for s in Presentation(BytesIO(plain)).slides)


@pytest.mark.skipif(not find_soffice(), reason="LibreOffice is not installed")
def test_pdf_export_has_a_page_per_slide():
    import pypdf
    pdf = to_pdf(build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {SAMPLE_IMAGE: sample_photo()}))
    assert pdf.startswith(b"%PDF") and len(pypdf.PdfReader(BytesIO(pdf)).pages) == len(SAMPLE_DECK.slides) + 1


def test_pdf_export_without_libreoffice_raises_a_clear_error(monkeypatch):
    from generator import export
    monkeypatch.setattr(export, "find_soffice", lambda: None)
    with pytest.raises(export.ExportError):
        export.to_pdf(b"x")


# ----- accessibility: real slide titles, decorative shapes -----------------------------------

@pytest.mark.parametrize("style", STYLES)
def test_every_slide_has_a_real_title_placeholder(style):
    data = build_pptx(SAMPLE_DECK, style, "Corporate Blue", {SAMPLE_IMAGE: sample_photo()})
    slides = list(Presentation(BytesIO(data)).slides)
    titles = [slide.shapes.title for slide in slides]
    assert all(title is not None for title in titles)
    assert titles[0].text_frame.paragraphs[0].text == SAMPLE_DECK.title
    for slide, title in zip(SAMPLE_DECK.slides, titles[1:]):
        assert title.text_frame.paragraphs[0].text == slide.title
    # exactly one title per slide, and its line spacing is written out (not taken from the template)
    for slide in slides:
        assert sum(1 for shape in slide.placeholders) == 1
        assert slide.shapes.title.text_frame.paragraphs[0].line_spacing is not None


def test_a_slide_that_shows_no_title_gets_one_just_above_the_slide():
    quote = next(i for i, s in enumerate(SAMPLE_DECK.slides) if s.type == "quote")
    slide = list(Presentation(BytesIO(build_pptx(SAMPLE_DECK, "minimal", "Corporate Blue", {}))).slides)[quote + 1]
    title = slide.shapes.title
    assert title.text_frame.text == SAMPLE_DECK.slides[quote].title
    assert title.top + title.height <= 0                       # above the visible area


def test_boxes_are_marked_decorative_and_texts_are_not():
    slide = list(Presentation(BytesIO(build_pptx(SAMPLE_DECK, "corporate", "Corporate Blue", {}))).slides)[1]
    decorative = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"

    def is_decorative(shape):
        return decorative in shape._element.xml
    boxes = [s for s in slide.shapes if s.shape_type == 1]     # auto shapes: rectangles, ovals
    assert boxes and all(is_decorative(s) for s in boxes)
    assert not any(is_decorative(s) for s in slide.shapes if s.has_text_frame and s.text_frame.text.strip())
