"""Editing slides as text (generator/content/editing.py)."""
import pytest

from generator.content.editing import apply_edits, apply_text, slide_to_text
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU


@pytest.mark.parametrize("deck", [SAMPLE_DECK, SAMPLE_DECK_RU], ids=["en", "ru"])
def test_every_slide_survives_a_round_trip_unchanged(deck):
    """Turning every slide into text and back, without edits, must give the same deck."""
    edits = [(s.title, slide_to_text(s), s.author if s.type == "quote" else None) for s in deck.slides]
    again = apply_edits(deck, deck.title, deck.subtitle, edits)
    for before, after in zip(deck.slides, again.slides):
        assert after == before, before.type
    assert len(again.slides) == len(deck.slides)


def test_edited_bullets_and_cards_are_read_back():
    bullets = next(s for s in SAMPLE_DECK.slides if s.type == "bullets")
    edited = apply_text(bullets, "New title", "First\n\n  Second  \n")
    assert edited.title == "New title" and edited.bullets == ["First", "Second"]
    assert edited.image_keyword == bullets.image_keyword        # the photo is kept

    cards = next(s for s in SAMPLE_DECK.slides if s.type == "cards")
    edited = apply_text(cards, "T", "Fast — Gets you there quickly\nCheap - Costs little\nGreen – Clean air")
    assert [(c.heading, c.text) for c in edited.cards] == [
        ("Fast", "Gets you there quickly"), ("Cheap", "Costs little"), ("Green", "Clean air")]


def test_dashes_inside_values_are_not_separators():
    timeline = next(s for s in SAMPLE_DECK.slides if s.type == "timeline")
    edited = apply_text(timeline, "T", "1961–1963 — Vostok flights\n2020-2024 — Private crews\n5–7 — Steps")
    assert [(s.label, s.text) for s in edited.steps] == [
        ("1961–1963", "Vostok flights"), ("2020-2024", "Private crews"), ("5–7", "Steps")]


def test_two_columns_and_table_formats():
    columns = next(s for s in SAMPLE_DECK.slides if s.type == "two_columns")
    edited = apply_text(columns, "T", "# Before\na\nb\n\n# After\nc")
    assert [(c.heading, c.bullets) for c in edited.columns] == [("Before", ["a", "b"]), ("After", ["c"])]

    table = next(s for s in SAMPLE_DECK.slides if s.type == "table")
    edited = apply_text(table, "T", "Mode | Cost\nBus | Low\nTaxi | High")
    assert edited.table.headers == ["Mode", "Cost"]
    assert [r.cells for r in edited.table.rows] == [["Bus", "Low"], ["Taxi", "High"]]


def test_slides_can_be_deleted_and_broken_edits_are_repaired():
    edits = [None] * len(SAMPLE_DECK.slides)
    cards_index = next(i for i, s in enumerate(SAMPLE_DECK.slides) if s.type == "cards")
    edits[cards_index] = ("Only one card left", "Lonely — just one", None)
    deck = apply_edits(SAMPLE_DECK, "New deck title", "", edits)
    assert deck.title == "New deck title"
    assert len(deck.slides) == 1
    # a cards slide needs two cards: like a broken model answer, it becomes a bullet slide
    assert deck.slides[0].type == "bullets" and deck.slides[0].bullets == ["Lonely: just one"]
