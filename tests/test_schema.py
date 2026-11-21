"""Reading and repairing the model's answer (generator/content/schema.py)."""
import json

import pytest

from generator.content.schema import ContentError, parse_deck


def deck_json(*slides, title="T", subtitle="S"):
    return json.dumps({"title": title, "subtitle": subtitle, "slides": list(slides)})


def test_valid_answer_is_parsed():
    deck = parse_deck(deck_json(
        {"type": "stats", "title": "Numbers", "stats": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}]}
    ))
    assert deck.slides[0].type == "stats"
    assert [s.value for s in deck.slides[0].stats] == ["1", "2"]


def test_text_around_json_is_ignored():
    raw = "Here is your presentation:\n```json\n" + deck_json({"type": "bullets", "title": "A", "bullets": ["x"]}) + "\n```"
    assert parse_deck(raw).slides[0].bullets == ["x"]


def test_old_format_with_content_field_is_accepted():
    deck = parse_deck(deck_json({"title": "A", "content": ["one", "two"], "image_keyword": "cat"}))
    slide = deck.slides[0]
    assert slide.type == "bullets" and slide.bullets == ["one", "two"] and slide.image_keyword == "cat"


def test_unknown_type_becomes_bullets():
    assert parse_deck(deck_json({"type": "mindmap", "title": "A", "bullets": ["x"]})).slides[0].type == "bullets"


def test_slide_without_what_its_type_needs_falls_back_to_bullets():
    # "cards" needs at least two cards; with one, its text is kept as a bullet slide
    deck = parse_deck(deck_json({"type": "cards", "title": "A", "cards": [{"heading": "H", "text": "T"}]}))
    assert deck.slides[0].type == "bullets"
    assert deck.slides[0].bullets == ["H: T"]


def test_slide_with_no_text_at_all_becomes_a_section():
    assert parse_deck(deck_json({"type": "stats", "title": "Only a title"})).slides[0].type == "section"


def test_table_rows_get_exactly_one_cell_per_header():
    deck = parse_deck(deck_json({"type": "table", "title": "A", "table": {
        "headers": ["a", "b", "c"],
        "rows": [{"cells": ["1"]}, {"cells": ["1", "2", "3", "4", "5"]}]}}))
    assert [row.cells for row in deck.slides[0].table.rows] == [["1", "", ""], ["1", "2", "3"]]


def test_limits_are_applied():
    deck = parse_deck(deck_json(
        {"type": "cards", "title": "A", "cards": [{"heading": str(i), "text": "t"} for i in range(9)]},
        {"type": "bullets", "title": "B", "bullets": [str(i) for i in range(20)]},
    ))
    assert len(deck.slides[0].cards) == 4
    assert len(deck.slides[1].bullets) == 7


def test_whitespace_and_quotes_are_cleaned():
    deck = parse_deck(deck_json({"type": "quote", "title": "  A \n B ", "quote": '"To be"', "author": " X "}))
    slide = deck.slides[0]
    assert (slide.title, slide.quote, slide.author) == ("A B", "To be", "X")


@pytest.mark.parametrize("raw", ["", "not json at all", "{broken", json.dumps({"slides": "nope"})])
def test_unusable_answers_raise_content_error(raw):
    with pytest.raises(ContentError):
        parse_deck(raw)


def test_answer_without_slides_raises_content_error():
    with pytest.raises(ContentError):
        parse_deck(deck_json())
