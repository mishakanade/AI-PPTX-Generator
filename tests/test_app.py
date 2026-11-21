"""The Streamlit page itself, driven by Streamlit's test runner with fake Gemini and Unsplash."""
import os

import pytest
from streamlit.testing.v1 import AppTest

from generator import config
from generator.content import llm
from generator.images import unsplash
from generator.design.sample_deck import sample_photo, sample_photo_url
from tests.stress_deck import STRESS_DECK

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


@pytest.fixture
def fakes(monkeypatch):
    """Count calls to Gemini and Unsplash and answer them with ready-made data."""
    counts = {"gemini": 0, "unsplash": 0}

    def fake_generate(prompt, max_slides=None, retries_per_model=2, api_key=None):
        counts["gemini"] += 1
        counts["gemini_key"] = api_key
        deck = STRESS_DECK.model_copy(deep=True)
        deck.slides = deck.slides[:max_slides]
        return deck

    def fake_photos(keywords, client_id=None):
        counts["unsplash"] += 1
        photo = unsplash.Photo(sample_photo(), sample_photo_url(), "Jane Doe", "https://unsplash.com/@jane")
        return {k: photo for k in keywords if k != "missing"}, []

    monkeypatch.setattr(llm, "generate_deck", fake_generate)
    monkeypatch.setattr(unsplash, "fetch_photos", fake_photos)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(config, "UNSPLASH_CLIENT_ID", "fake")
    return counts


def test_without_gemini_key_the_page_explains_and_nothing_is_sent(fakes, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert any("Gemini API key is needed" in i.value for i in app.info)
    app.text_input[2].set_value("Космос")          # [0] and [1] are the key fields in the sidebar
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert any("Add a Gemini API key" in w.value for w in app.warning)
    assert fakes["gemini"] == 0


def test_a_key_typed_in_the_sidebar_is_used(fakes, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input[0].set_value("  typed-key  ")
    app.text_input[2].set_value("Космос")
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert not app.exception and not app.error
    assert fakes["gemini"] == 1 and fakes["gemini_key"] == "typed-key"


def test_generate_then_change_design_without_new_requests(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    app.text_input[2].set_value("Космос")
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert not app.exception and not app.error
    first_file = app.session_state["pptx_bytes"]
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)

    app.button(key="style_bold").click().run()             # another style
    app.selectbox[0].set_value("Cyberpunk").run()         # another colour theme
    assert not app.exception and not app.error
    assert app.session_state["rendered_design"] == ("bold", "Cyberpunk")
    assert app.session_state["pptx_bytes"] != first_file
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)  # nothing was generated again


def test_empty_form_asks_for_a_topic(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert any("enter a topic" in w.value for w in app.warning)
    assert fakes["gemini"] == 0


def test_editing_changes_the_file_without_new_requests(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input[2].set_value("Космос")
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    deck = app.session_state["deck"]
    version = app.session_state["edit_version"]

    app.text_input(key=f"e{version}_0_title").set_value("Совсем новый заголовок")
    app.checkbox(key=f"e{version}_1_delete").check()
    app.button(key=f"FormSubmitter:edit_form_{version}-Apply changes").click().run()
    assert not app.exception and not app.error

    edited = app.session_state["deck"]
    assert edited.slides[0].title == "Совсем новый заголовок"
    assert len(edited.slides) == len(deck.slides) - 1
    assert app.session_state["edit_version"] == version + 1
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)


def test_custom_colours_from_the_pickers(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox[0].set_value("✏️ Custom colours").run()
    app.color_picker(key="custom_bg").set_value("#102030").run()
    app.text_input[2].set_value("Космос")
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert not app.exception and not app.error
    from io import BytesIO
    from pptx import Presentation
    slide = Presentation(BytesIO(app.session_state["pptx_bytes"])).slides[0]
    assert str(slide.background.fill.fore_color.rgb) == "102030"
