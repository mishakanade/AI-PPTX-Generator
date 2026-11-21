"""The finished outputs: the .pptx file and the HTML preview."""
from io import BytesIO

from pptx import Presentation

from generator.content.schema import Deck, Slide
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo, sample_photo_url
from generator.design.styles import STYLES
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
