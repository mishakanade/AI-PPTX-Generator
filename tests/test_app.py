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

    def fake_review(deck, prompt, *args, **kwargs):
        counts["review"] = counts.get("review", 0) + 1
        counts["review_prompt"] = prompt
        return deck                                   # the editor's pass changes nothing here

    monkeypatch.setattr(llm, "generate_deck", fake_generate)
    monkeypatch.setattr(llm, "review_deck", fake_review)
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
    assert app.session_state["rendered_design"] == ("bold", "Cyberpunk", None, None)
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
    app.text_area(key="chat_answer_deck").set_value("Конечно! Вот JSON:\n```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```")
    app.button(key="chat_build_deck").click().run()
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
    app.text_area(key="chat_answer_deck").set_value("Sorry, I can't help with that.")
    app.button(key="chat_build_deck").click().run()
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
    app.text_area(key="chat_answer_deck").set_value(json.dumps(answer))
    app.button(key="chat_build_deck").click().run()
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


def generated_app(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос")
    app.slider(key="num_slides").set_value(15)          # the test deck's photo slides come later
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    return app


def photo_slide_index(app):
    return next(i for i, s in enumerate(app.session_state["deck"].slides)
                if s.type == "bullets" and s.image_keyword)


def test_a_saved_project_opens_with_its_design(fakes):
    from generator.project import save_project
    app = generated_app(fakes)
    custom = {"bg": (16, 32, 48), "title": (250, 250, 250), "text": (220, 220, 220), "accent": (255, 120, 0)}
    raw = save_project(app.session_state["deck"], app.session_state["photos"], "soft", custom,
                       {"tone": "💼 Professional", "text_amount": "Balanced", "speaker_notes": False}, "fade")

    fresh = AppTest.from_file(APP, default_timeout=60).run()
    fresh.file_uploader(key="project_file").set_value(("deck.project.json", raw, "application/json")).run()
    assert not fresh.exception and not fresh.error
    assert fresh.session_state["deck"] == app.session_state["deck"]
    assert fresh.session_state["style"] == "soft" and fresh.session_state["theme"] == "custom"
    assert fresh.session_state["custom_bg"] == "#102030"
    assert fresh.session_state["rendered_design"][:3] == ("soft", custom, "fade")
    assert fakes["gemini"] == 1                         # opening did not ask the AI again


def test_a_file_that_is_not_a_project_shows_an_error(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.file_uploader(key="project_file").set_value(("x.json", b"hello", "application/json")).run()
    assert not app.exception
    assert any("Could not open this file" in e.value for e in app.error)


def test_uploading_own_picture_replaces_the_photo(fakes):
    from generator.design.sample_deck import sample_photo
    app = generated_app(fakes)
    index, version = photo_slide_index(app), app.session_state["edit_version"]
    app.file_uploader(key=f"own_{version}_{index}").set_value(("me.jpg", sample_photo(), "image/jpeg")).run()
    assert not app.exception and not app.error
    keyword = app.session_state["deck"].slides[index].image_keyword
    assert keyword.startswith("upload-") and app.session_state["photos"][keyword].credit == ""

    version = app.session_state["edit_version"]
    app.file_uploader(key=f"own_{version}_{index}").set_value(("x.jpg", b"not a picture", "image/jpeg")).run()
    assert any("not a picture" in w.value for w in app.warning)


def test_another_photo_and_remove_photo(fakes, monkeypatch):
    from generator.design.sample_deck import sample_photo
    replacement = unsplash.Photo(sample_photo(), "data:image/jpeg;base64,", "New Author", "https://u/new", "id-2")
    seen = {}

    def fake_another(keyword, exclude_ids, client_id=None):
        seen["keyword"], seen["exclude"] = keyword, set(exclude_ids)
        return replacement, []

    monkeypatch.setattr(unsplash, "fetch_another", fake_another)
    app = generated_app(fakes)
    index, version = photo_slide_index(app), app.session_state["edit_version"]
    keyword = app.session_state["deck"].slides[index].image_keyword
    app.button(key=f"another_{version}_{index}").click().run()
    assert not app.exception and not app.error
    assert seen["keyword"] == keyword and app.session_state["photos"][keyword].author == "New Author"

    version = app.session_state["edit_version"]
    app.button(key=f"remove_{version}_{index}").click().run()
    assert app.session_state["deck"].slides[index].image_keyword is None


def test_choosing_a_transition_redraws_the_file(fakes):
    from io import BytesIO
    from pptx import Presentation
    app = generated_app(fakes)
    app.selectbox(key="transition").set_value("wipe").run()
    assert not app.exception and app.session_state["rendered_design"][2] == "wipe"
    slide = Presentation(BytesIO(app.session_state["pptx_bytes"])).slides[0]
    assert "<p:wipe" in slide._element.xml
    assert fakes["gemini"] == 1


def test_a_logo_is_added_to_every_slide_and_saved_with_the_project(fakes):
    from io import BytesIO
    from PIL import Image
    from pptx import Presentation
    from generator.project import load_project, save_project
    buffer = BytesIO()
    Image.new("RGBA", (300, 100), (200, 0, 0, 255)).save(buffer, "PNG")
    app = generated_app(fakes)
    app.file_uploader(key="logo_file").set_value(("logo.png", buffer.getvalue(), "image/png")).run()
    assert not app.exception and not app.error and app.session_state["logo"] == buffer.getvalue()
    slides = Presentation(BytesIO(app.session_state["pptx_bytes"])).slides
    logos = [sh for slide in slides for sh in slide.shapes
             if sh.shape_type == 13 and sh._element.nvPicPr.cNvPr.get("descr") == "Logo"]
    assert len(logos) == len(slides)
    assert fakes["gemini"] == 1

    saved = save_project(app.session_state["deck"], app.session_state["photos"], "minimal", "Corporate Blue",
                         logo=app.session_state["logo"])
    assert load_project(saved)["logo"] == buffer.getvalue()

    app.button(key="logo_remove").click().run()
    assert "logo" not in app.session_state and app.session_state["rendered_design"][3] is None


PLAN = {"title": "Космос", "subtitle": "Обзор", "slides": [
    {"type": "agenda", "title": "План", "focus": "Части"},
    {"type": "bullets", "title": "Гонка", "focus": "Кто был первым"},
    {"type": "stats", "title": "Цифры", "focus": "Ключевые числа"},
]}


def test_plan_first_through_the_api(fakes, monkeypatch):
    from generator.content.schema import parse_outline
    prompts = []

    def fake_outline(prompt, retries_per_model=2, api_key=None, provider="gemini", model=None):
        prompts.append(prompt)
        return parse_outline(json.dumps(PLAN))

    monkeypatch.setattr(llm, "generate_outline", fake_outline)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос")
    app.checkbox(key="outline_first").check()
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert "Write only the plan" in prompts[0] and fakes["gemini"] == 0
    version = app.session_state["outline_version"]

    app.text_input(key=f"o{version}_0_title").set_value("Содержание")      # rename
    app.checkbox(key=f"o{version}_1_delete").check()                       # delete
    app.text_input(key=f"o{version}_3_title").set_value("Итоги")           # fill an empty row
    app.selectbox(key=f"o{version}_3_type").set_value("closing")
    app.button(key=f"outline_write_{version}").click().run()
    assert not app.exception and not app.error

    assert fakes["gemini"] == 1
    prompt = fakes["prompt"]
    assert 'approved this outline' in prompt and '1. agenda: "Содержание"' in prompt
    assert '"Гонка"' not in prompt and '3. closing: "Итоги"' in prompt
    assert "deck" in app.session_state and "outline" not in app.session_state


def test_plan_first_by_copy_and_paste(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("chat").run()
    app.text_input(key="topic").set_value("Космос")
    app.checkbox(key="outline_first").check()
    app.button(key="generate").click().run()
    assert "Write only the plan" in app.code[0].value

    app.text_area(key="chat_answer_outline").set_value("```json\n" + json.dumps(PLAN, ensure_ascii=False) + "\n```")
    app.button(key="chat_build_outline").click().run()
    version = app.session_state["outline_version"]
    app.button(key=f"outline_write_{version}").click().run()
    assert not app.exception and not app.error
    deck_prompt = app.code[0].value
    assert "approved this outline" in deck_prompt and "ANSWER FORMAT" in deck_prompt

    deck = {"title": "Космос", "subtitle": "Обзор", "slides": [
        {"type": "agenda", "title": "План", "bullets": ["a", "b"]},
        {"type": "bullets", "title": "Гонка", "bullets": ["x"]},
        {"type": "stats", "title": "Цифры", "stats": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}]}]}
    app.text_area(key="chat_answer_deck").set_value(json.dumps(deck, ensure_ascii=False))
    app.button(key="chat_build_deck").click().run()
    assert not app.exception and not app.error
    assert [s.title for s in app.session_state["deck"].slides] == ["План", "Гонка", "Цифры"]
    assert fakes["gemini"] == 0


def test_pdf_button_only_where_libreoffice_exists(fakes, monkeypatch):
    from generator import export
    monkeypatch.setattr(export, "find_soffice", lambda: None)
    app = generated_app(fakes)
    assert not [b for b in app.button if b.key == "make_pdf"]

    monkeypatch.setattr(export, "find_soffice", lambda: "/usr/bin/soffice")
    monkeypatch.setattr(export, "to_pdf", lambda pptx: b"%PDF-fake")
    app.run()
    app.button(key="make_pdf").click().run()
    assert not app.exception and not app.error
    assert app.session_state["pdf"][1] == b"%PDF-fake"

    app.selectbox(key="theme").set_value("Cyberpunk").run()        # a new design: the old PDF is not offered
    assert [b for b in app.button if b.key == "make_pdf"]


def test_the_editors_pass_runs_after_writing_unless_switched_off(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Космос")
    app.selectbox(key="goal").set_value("persuade")
    app.text_input(key="audience").set_value("депутаты")
    app.number_input(key="minutes").set_value(15)
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert "convince the audience" in fakes["prompt"] and "AUDIENCE: депутаты" in fakes["prompt"]
    assert "so that the talk lasts about 15 minutes" in fakes["prompt"]
    assert fakes["review"] == 1 and "PROBLEMS FOUND:" in fakes["review_prompt"]

    app.checkbox(key="auto_review").uncheck()
    app.button(key="generate").click().run()
    assert fakes["gemini"] == 2 and fakes["review"] == 1


def test_quality_section_lists_problems_and_fixes_them_with_ai(fakes, monkeypatch):
    app = generated_app(fakes)
    quality = [e for e in app.expander if "Quality check" in e.label]
    assert quality and "/100" in quality[0].label

    better = app.session_state["deck"].model_copy(deep=True)
    better.slides[0].title = "Новый заголовок-тезис для первого слайда"
    monkeypatch.setattr(llm, "review_deck", lambda deck, prompt, *a, **k: better)
    app.button(key="fix_ai").click().run()
    assert not app.exception and not app.error
    assert app.session_state["deck"].slides[0].title == "Новый заголовок-тезис для первого слайда"


def test_quality_fix_by_copy_and_paste(fakes):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.selectbox(key="provider").set_value("chat").run()
    app.text_input(key="topic").set_value("x")
    app.button(key="generate").click().run()
    draft = {"title": "T", "subtitle": "", "slides": [
        {"type": "bullets", "title": "Problems", "bullets": ["In today's world things change"]}]}
    app.text_area(key="chat_answer_deck").set_value(json.dumps(draft))
    app.button(key="chat_build_deck").click().run()
    app.button(key="fix_chat_show").click().run()
    request = [c.value for c in app.code if "PROBLEMS FOUND" in c.value]
    assert request and "names a topic" in request[0] and "in today's world" in request[0]

    version = app.session_state["edit_version"]
    fixed = {"title": "T", "subtitle": "", "slides": [
        {"type": "bullets", "title": "Change is now measured in months", "bullets": ["Things change fast"]}]}
    app.text_area(key=f"fix_chat_answer_{version}").set_value(json.dumps(fixed))
    app.button(key="fix_chat_apply").click().run()
    assert not app.exception and not app.error
    assert app.session_state["deck"].slides[0].title == "Change is now measured in months"


def test_uploaded_data_becomes_charts_with_the_real_numbers(fakes, monkeypatch):
    from generator.content.schema import parse_deck
    answer = {"title": "Финансы", "subtitle": "", "slides": [
        {"type": "chart", "title": "Выручка растёт третий год подряд", "subtitle": "+78% к 2019", "data_ref": "D1",
         "chart": {"kind": "pie", "categories": ["x", "y"], "series": [{"name": "fake", "values": [1, 2]}]}}]}
    seen = {}

    def fake_generate(prompt, max_slides=None, **kwargs):
        seen["prompt"] = prompt
        return parse_deck(json.dumps(answer, ensure_ascii=False))

    monkeypatch.setattr(llm, "generate_deck", fake_generate)
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="topic").set_value("Финансы")
    csv = "Год;Выручка, млн ₽\n2019;120,5\n2020;98\n2021;140\n2022;214,6\n".encode()
    app.file_uploader(key="data_file").set_value(("finance.csv", csv, "text/csv"))
    app.button(key="generate").click().run()
    assert not app.exception and not app.error
    assert "PREPARED CHARTS" in seen["prompt"] and "2022,214.6" in seen["prompt"]
    assert any("Data: 1 table(s)" in i.value for i in app.info)
    chart = app.session_state["deck"].slides[0].chart
    assert chart.kind == "line" and chart.series[0].values == [120.5, 98.0, 140.0, 214.6]
