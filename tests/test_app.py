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

    def fake_generate(prompt, max_slides=None, retries_per_model=2):
        counts["gemini"] += 1
        deck = STRESS_DECK.model_copy(deep=True)
        deck.slides = deck.slides[:max_slides]
        return deck

    def fake_photos(keywords):
        counts["unsplash"] += 1
        photo = unsplash.Photo(sample_photo(), sample_photo_url(), "Jane Doe", "https://unsplash.com/@jane")
        return {k: photo for k in keywords if k != "missing"}, []

    monkeypatch.setattr(llm, "generate_deck", fake_generate)
    monkeypatch.setattr(unsplash, "fetch_photos", fake_photos)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(config, "UNSPLASH_CLIENT_ID", "fake")
    return counts


def test_without_gemini_key_the_page_explains_what_to_do(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert "Gemini API key not found" in app.error[0].value
    assert len(app.text_input) == 0          # the form is not shown


def test_generate_then_change_design_without_new_requests(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    app.text_input[0].set_value("Космос")
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert not app.exception and not app.error
    first_file = app.session_state["pptx_bytes"]
    assert fakes == {"gemini": 1, "unsplash": 1}

    app.button(key="style_bold").click().run()             # another style
    app.selectbox[0].set_value("Cyberpunk").run()         # another colour theme
    assert not app.exception and not app.error
    assert app.session_state["rendered_design"] == ("bold", "Cyberpunk")
    assert app.session_state["pptx_bytes"] != first_file
    assert fakes == {"gemini": 1, "unsplash": 1}           # nothing was generated again


def test_empty_form_asks_for_a_topic(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.button(key="FormSubmitter:generation_form-🚀 Generate presentation").click().run()
    assert any("enter a topic" in w.value for w in app.warning)
    assert fakes["gemini"] == 0
