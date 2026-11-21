"""The Streamlit page itself, driven by Streamlit's test runner with fake Gemini and Unsplash."""
import json
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

    def fake_generate(prompt, max_slides=None, retries_per_model=2, api_key=None, provider="gemini", model=None):
        counts["gemini"] += 1
        counts["gemini_key"] = api_key
        counts["provider"], counts["model"], counts["prompt"] = provider, model, prompt
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
    app.text_input(key="topic").set_value("Космос")          # [0] and [1] are the key fields in the sidebar
    app.button(key="generate").click().run()
    assert any("Add a Gemini API key" in w.value for w in app.warning)
    assert fakes["gemini"] == 0


def test_a_key_typed_in_the_sidebar_is_used(fakes, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="gemini_key").set_value("  typed-key  ")
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert fakes["gemini"] == 1 and fakes["gemini_key"] == "typed-key"


def test_generate_then_change_design_without_new_requests(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    first_file = app.session_state["pptx_bytes"]
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)

    app.button(key="style_bold").click().run()             # another style
    app.selectbox(key="theme").set_value("Cyberpunk").run()         # another colour theme
    assert not app.exception and not app.error
    assert app.session_state["rendered_design"] == ("bold", "Cyberpunk")
    assert app.session_state["pptx_bytes"] != first_file
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)  # nothing was generated again


def test_empty_form_asks_for_a_topic(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.button(key="generate").click().run()
    assert any("enter a topic" in w.value for w in app.warning)
    assert fakes["gemini"] == 0


def test_editing_changes_the_file_without_new_requests(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    deck = app.session_state["deck"]
    version = app.session_state["edit_version"]

    app.text_input(key=f"e{version}_0_title").set_value("Совсем новый заголовок")
    app.checkbox(key=f"e{version}_1_delete").check()
    app.button(key=f"apply_{version}").click().run()
    assert not app.exception and not app.error

    edited = app.session_state["deck"]
    assert edited.slides[0].title == "Совсем новый заголовок"
    assert len(edited.slides) == len(deck.slides) - 1
    assert app.session_state["edit_version"] == version + 1
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)


def test_custom_colours_from_the_pickers(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="theme").set_value("custom").run()
    app.color_picker(key="custom_bg").set_value("#102030").run()
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    from io import BytesIO
    from pptx import Presentation
    slide = Presentation(BytesIO(app.session_state["pptx_bytes"])).slides[0]
    assert str(slide.background.fill.fore_color.rgb) == "102030"


def test_russian_interface(fakes):
    app = AppTest.from_file(APP, default_timeout=60)
    app.session_state["lang"] = "ru"
    app.run()
    assert not app.exception
    assert app.subheader[0].value == "Оформление"
    assert app.button(key="generate").label == "🚀 Создать презентацию"
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert "Слайдов:" in app.caption[-1].value or any("Слайдов:" in c.value for c in app.caption)
    assert (fakes["gemini"], fakes["unsplash"]) == (1, 1)


def test_typed_topic_survives_a_change_of_language(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос").run()
    app.session_state["lang"] = "ru"
    app.run()
    assert app.text_input(key="topic").value == "Космос"
    assert app.text_input(key="topic").label == "Тема презентации"


def test_model_text_cannot_inject_markdown(fakes, monkeypatch):
    """Notes or a title with a Markdown picture must be shown as text, not loaded from the address."""
    def hostile(prompt, max_slides=None, retries_per_model=2, api_key=None, provider="gemini", model=None):
        deck = STRESS_DECK.model_copy(deep=True)
        deck.slides = deck.slides[:3]
        deck.title = "Deck ![t](http://evil.example/title.png)"
        deck.slides[0].notes = "Say hi ![n](http://evil.example/notes.png)"
        return deck

    monkeypatch.setattr(llm, "generate_deck", hostile)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("x")
    app.button(key="generate").click().run()
    assert not app.exception
    shown = [m.value for m in app.markdown] + [h.value for h in app.subheader]
    assert any("evil" in text for text in shown)                       # the text is shown...
    assert not any("![" in text for text in shown)                     # ...but never as a picture


def test_regenerating_one_slide_replaces_only_that_slide(fakes, monkeypatch):
    from generator.content.schema import Slide
    prompts = []

    def fake_regenerate(prompt, retries_per_model=2, api_key=None, provider="gemini", model=None):
        prompts.append(prompt)
        return Slide(type="statement", title="Новый", subtitle="Совсем другая мысль")

    monkeypatch.setattr(llm, "regenerate_slide", fake_regenerate)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    before = app.session_state["deck"]
    version = app.session_state["edit_version"]

    app.selectbox(key=f"regen_slide_{version}").set_value(1)
    app.text_input(key=f"regen_wish_{version}").set_value("Одной фразой")
    app.button(key="regen_button").click().run()
    assert not app.exception and not app.error

    after = app.session_state["deck"]
    assert after.slides[1].title == "Новый" and after.slides[1].type == "statement"
    assert [s.title for i, s in enumerate(after.slides) if i != 1] == \
        [s.title for i, s in enumerate(before.slides) if i != 1]
    assert "Одной фразой" in prompts[0] and "<-- THIS SLIDE" in prompts[0]
    assert fakes["gemini"] == 1                    # the whole deck was not generated again


def test_openai_provider_with_a_typed_key_and_model(fakes, monkeypatch):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("openai").run()
    assert any("OpenAI API key is needed" in i.value for i in app.info)
    app.text_input(key="openai_key").set_value("sk-typed")
    app.text_input(key="model_openai").set_value("my-model")
    app.text_input(key="topic").set_value("Космос")
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert (fakes["provider"], fakes["gemini_key"], fakes["model"]) == ("openai", "sk-typed", "my-model")


def test_copy_and_paste_mode_builds_the_deck_from_a_pasted_answer(fakes, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)        # no key at all is needed in this mode
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("chat").run()
    assert not any("API key is needed" in i.value for i in app.info)
    app.text_input(key="topic").set_value("Космос")
    app.slider(key="num_slides").set_value(3)
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    prompt = app.code[0].value
    assert '"Космос"' in prompt and "ANSWER FORMAT" in prompt and fakes["gemini"] == 0

    answer = {"title": "Космос", "subtitle": "Обзор", "slides": [
        {"type": "bullets", "title": f"Слайд {i}", "bullets": ["a", "b"], "image_keyword": "rocket launch"}
        for i in range(5)]}
    app.text_area(key="chat_answer").set_value("Конечно! Вот JSON:\n```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```")
    app.button(key="chat_build").click().run()
    assert not app.exception and not app.error
    deck = app.session_state["deck"]
    assert deck.title == "Космос" and len(deck.slides) == 3      # trimmed to the requested number
    assert fakes["unsplash"] == 1 and fakes["gemini"] == 0       # photos fetched, no AI API called
    assert "pptx_bytes" in app.session_state


def test_copy_and_paste_mode_explains_a_broken_answer(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("chat").run()
    app.text_input(key="topic").set_value("x")
    app.button(key="generate").click().run()
    app.text_area(key="chat_answer").set_value("Sorry, I can't help with that.")
    app.button(key="chat_build").click().run()
    assert not app.exception
    assert any("Could not read a presentation" in e.value for e in app.error)
    assert "deck" not in app.session_state


def test_copy_and_paste_mode_regenerates_one_slide(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("chat").run()
    app.text_input(key="topic").set_value("x")
    app.button(key="generate").click().run()
    answer = {"title": "T", "subtitle": "", "slides": [
        {"type": "bullets", "title": f"S{i}", "bullets": ["a"]} for i in range(3)]}
    app.text_area(key="chat_answer").set_value(json.dumps(answer))
    app.button(key="chat_build").click().run()
    version = app.session_state["edit_version"]

    app.selectbox(key=f"regen_slide_{version}").set_value(2)
    app.button(key="regen_chat_show").click().run()
    assert any("<-- THIS SLIDE" in c.value and "ANSWER FORMAT" in c.value for c in app.code)
    app.text_area(key=f"regen_chat_answer_{version}").set_value(
        '```json\n{"type": "statement", "title": "New", "subtitle": "One idea"}\n```')
    app.button(key="regen_chat_apply").click().run()
    assert not app.exception and not app.error
    slides = app.session_state["deck"].slides
    assert slides[2].type == "statement" and [s.title for s in slides[:2]] == ["S0", "S1"]
    assert fakes["gemini"] == 0
