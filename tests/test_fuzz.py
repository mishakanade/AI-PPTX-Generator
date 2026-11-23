"""Broken answers from a model: the app either repairs them or says clearly that it cannot.

A model answering without the strict schema (copy & paste mode, the JSON fallback, a
weaker model) can send almost anything: a number where text belongs, a missing field,
an unknown slide type, a list instead of an object, an answer cut off in the middle,
prose around the JSON. This test takes valid presentations, damages them at random in
such ways, many hundreds of times, and checks the promise the app makes:

- reading the answer ends either with a presentation or with ContentError (which the
  interface explains to the user) - never with any other error;
- a presentation that was read can be drawn in every style, as slides, a file and a preview.

The random damage is the same on every run (fixed seeds), so a failure can be repeated.
"""
import json
import random

import pytest

from generator.content.schema import ContentError, parse_deck, parse_digest, parse_outline, parse_slide
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU, SAMPLE_IMAGE, sample_photo
from generator.design.styles import STYLES
from generator.render.builder import build_pptx, build_preview, build_slides
from generator.render.primitives import SLIDE_W, Picture, Text
from tests.stress_deck import STRESS_DECK

SEEDS = range(400)
ORIGINALS = [d.model_dump() for d in (SAMPLE_DECK, SAMPLE_DECK_RU, STRESS_DECK)]
STRANGE_VALUES = [
    None, "", " ", 0, -1, 3.5, 1e308, -1e308, True, False, [], {}, [None], ["", None, 7],
    {"a": 1}, "NaN", "12,5 %", "x" * 3000, "😀" * 50, "<b>bold</b>", "line\nbreak\ttab", "​",
    [1, 2, 3], ["text", ["nested"]], {"heading": None}, "-", "∞",
]
SLIDE_TYPES = ["bullets", "image", "two_columns", "cards", "stats", "chart", "statement", "agenda",
               "quote", "timeline", "table", "section", "closing", "unknown", "", None, 5]


def nodes(value, path=()):
    """Every place inside a JSON value, as a path of keys and indexes."""
    yield path
    if isinstance(value, dict):
        for key, child in value.items():
            yield from nodes(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from nodes(child, path + (index,))


def strange(rng):
    return json.loads(json.dumps(rng.choice(STRANGE_VALUES)))     # a fresh copy: it may be changed later


def damage(data, rng):
    """The same JSON with one to six random injuries."""
    data = json.loads(json.dumps(data))
    for _ in range(rng.randint(1, 6)):
        places = [p for p in nodes(data) if p]
        if not places:
            break
        path = rng.choice(places)
        parent = data
        for step in path[:-1]:
            parent = parent[step]
        last = path[-1]
        action = rng.random()
        if action < 0.45:
            parent[last] = strange(rng)
        elif action < 0.6 and isinstance(parent, dict):
            del parent[last]
        elif action < 0.7 and isinstance(parent, list):
            parent.append(json.loads(json.dumps(rng.choice(parent))))       # one item too many
        elif action < 0.8 and isinstance(parent, dict) and last == "type":
            parent[last] = rng.choice(SLIDE_TYPES)
        elif action < 0.9 and isinstance(parent, dict):
            parent["extra_" + str(rng.randint(0, 9))] = strange(rng)
        else:
            parent[last] = [parent[last]] if rng.random() < 0.5 else {"value": parent[last]}
    return data


def as_answer(data, rng):
    """The JSON as a model might send it: plain, fenced, with prose around it, or cut off."""
    text = json.dumps(data, ensure_ascii=rng.random() < 0.5, indent=rng.choice([None, 2]))
    form = rng.random()
    if form < 0.15:
        return f"```json\n{text}\n```"
    if form < 0.25:
        return f"Here is your presentation:\n{text}\nI hope it helps!"
    if form < 0.32:
        return text[: rng.randint(0, len(text))]              # the answer was cut off
    if form < 0.36:
        return text.replace('"', "'")                          # not JSON at all
    return text


def check_drawable(deck, rng):
    style = rng.choice(list(STYLES))
    images = {SAMPLE_IMAGE: sample_photo()}
    for spec in build_slides(deck, style, "Corporate Blue", images.keys()):
        for item in spec.items:
            if isinstance(item, (Text, Picture)):
                assert item.x >= -0.02 and item.x + item.w <= SLIDE_W + 0.02, item
    if rng.random() < 0.08:                                    # the slow parts, now and then
        assert build_pptx(deck, style, "Dark Modern", images)[:2] == b"PK"
        assert build_preview(deck, style, "Dark Modern", {SAMPLE_IMAGE: "x.jpg"})


@pytest.mark.parametrize("seed", SEEDS)
def test_a_damaged_deck_is_repaired_or_refused_clearly(seed):
    rng = random.Random(seed)
    answer = as_answer(damage(rng.choice(ORIGINALS), rng), rng)
    try:
        deck = parse_deck(answer)
    except ContentError:
        return
    assert deck.slides
    check_drawable(deck, rng)


@pytest.mark.parametrize("seed", range(150))
def test_damaged_slides_plans_and_digests_are_repaired_or_refused_clearly(seed):
    rng = random.Random(10_000 + seed)
    deck = rng.choice(ORIGINALS)
    cases = [
        (parse_slide, rng.choice(deck["slides"])),
        (parse_outline, {"title": deck["title"], "subtitle": deck["subtitle"],
                         "slides": [{"type": s["type"], "title": s["title"], "focus": s.get("subtitle")}
                                    for s in deck["slides"]]}),
        (parse_digest, {"points": [s["title"] for s in deck["slides"]]}),
    ]
    for parse, original in cases:
        try:
            parse(as_answer(damage(original, rng), rng))
        except ContentError:
            pass


@pytest.mark.parametrize("answer", [
    None, "", "   ", "null", "[]", "{}", "42", '"text"', "[1, 2]", '{"slides": 5}', '{"slides": "abc"}',
    '{"slides": {"a": 1}}', '{"slides": [1, "x", null]}', '{"slides": [{}]}', "{" * 5000 + "}" * 5000,
])
def test_answers_that_are_not_presentations_at_all(answer):
    for parse in (parse_deck, parse_slide, parse_outline, parse_digest):
        try:
            parse(answer)
        except ContentError:
            pass


# ----- what the random damage found once, kept as fixed cases ------------------------------

def chart_answer(values):
    return json.dumps({"title": "T", "slides": [{"type": "chart", "title": "C", "subtitle": "Insight", "chart": {
        "kind": "column", "categories": ["a", "b"], "series": [{"name": "s", "values": values}]}}]}).replace(
        '"INF"', "Infinity").replace('"NAN"', "NaN")


@pytest.mark.parametrize("answer", [
    '{"title": "T", "slides": [{"type": ["chart"], "title": "A", "bullets": ["x"]}]}',      # a list as the type
    '{"title": "T", "slides": [{"type": {"a": 1}, "title": "A", "bullets": ["x"]}]}',
    '{"title": "T", "slides": 5}',
    '{"title": "T", "slides": [{"type": "chart", "title": "A", "chart": {"series": 7}}]}',
    chart_answer(["INF", 1]), chart_answer(["NAN", 1]), chart_answer([1e308, 1e308]),
])
def test_cases_the_fuzzer_found(answer):
    try:
        deck = parse_deck(answer)
    except ContentError:
        return
    check_drawable(deck, random.Random(0))


def test_a_title_of_thousands_of_characters_is_shortened():
    deck = parse_deck(json.dumps({"title": "x" * 3000, "slides": [
        {"type": "agenda", "title": "word " * 600, "bullets": ["one", "two", "three"]}]}))
    assert len(deck.title) <= 160 and deck.title.endswith("…")
    assert len(deck.slides[0].title) <= 160 and deck.slides[0].title.endswith("word…")
    check_drawable(deck, random.Random(0))


def test_a_digest_with_one_text_instead_of_a_list_is_read():
    assert parse_digest('{"points": "The only point"}').points == ["The only point"]
