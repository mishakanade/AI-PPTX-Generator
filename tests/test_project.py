"""Saving and opening projects (generator/project.py) and photos the user uploads."""
import json

import pytest

from generator.content.schema import ContentError
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo
from generator.images.unsplash import Photo, own_photo
from generator.project import load_project, save_project


def unsplash_photo():
    return Photo(data=sample_photo(), preview_url="x", author="Jane Doe", author_url="https://u/jane", photo_id="abc")


def test_a_project_opens_exactly_as_it_was_saved():
    custom = {"bg": (16, 32, 48), "title": (250, 250, 250), "text": (220, 220, 220), "accent": (255, 120, 0)}
    raw = save_project(SAMPLE_DECK, {SAMPLE_IMAGE: unsplash_photo()}, "bold", custom,
                       {"tone": "💼 Professional", "text_amount": "Balanced", "speaker_notes": True})
    project = load_project(raw)
    assert project["deck"] == SAMPLE_DECK
    assert project["style"] == "bold" and project["theme"] == custom
    assert project["settings"]["text_amount"] == "Balanced"
    photo = project["photos"][SAMPLE_IMAGE]
    assert photo.data == sample_photo() and photo.author == "Jane Doe" and photo.photo_id == "abc"
    assert photo.preview_url.startswith("data:image/jpeg;base64,")


def test_a_built_in_theme_is_saved_by_name():
    project = load_project(save_project(SAMPLE_DECK, {}, "soft", "Cyberpunk"))
    assert project["theme"] == "Cyberpunk" and project["photos"] == {}


def test_a_bare_deck_from_an_ai_chat_also_opens():
    answer = "Here you go:\n```json\n" + json.dumps({"title": "T", "subtitle": "", "slides": [
        {"type": "bullets", "title": "A", "bullets": ["x"]}]}) + "\n```"
    project = load_project(answer.encode())
    assert project["deck"].title == "T" and project["style"] and project["theme"]


def test_unknown_values_and_broken_photos_fall_back_safely():
    data = json.loads(save_project(SAMPLE_DECK, {SAMPLE_IMAGE: unsplash_photo()}, "minimal", "Corporate Blue"))
    data["style"], data["theme"] = "no-such-style", "no-such-theme"
    data["photos"]["broken"] = {"data": "!!!not base64!!!"}
    project = load_project(json.dumps(data).encode())
    assert project["style"] == "minimal" and project["theme"] == "Corporate Blue"
    assert set(project["photos"]) == {SAMPLE_IMAGE}


def test_a_file_without_a_presentation_is_rejected():
    with pytest.raises(ContentError):
        load_project(b"just some text")


def test_uploaded_pictures_have_no_unsplash_credit():
    photo = own_photo(sample_photo())
    assert photo.credit == "" and photo.preview_url.startswith("data:image/jpeg")
    assert unsplash_photo().credit == "Photo by Jane Doe on Unsplash"
    with pytest.raises(ValueError):
        own_photo(b"not an image")
