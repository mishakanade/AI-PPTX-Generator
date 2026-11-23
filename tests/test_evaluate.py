"""tools/evaluate.py with a fake model: the whole comparison runs and the report adds up."""
import json

import pytest

from generator.content import llm
from generator.content.schema import parse_deck
from tools import evaluate

PLAIN = {"title": "Bikes", "subtitle": "", "slides": [
    {"title": "Introduction", "bullets": ["In today's world bikes play a key role", "Bikes are important"]},
    {"title": "Problems", "bullets": ["Traffic is bad", "Air is bad"]},
    {"title": "Conclusion", "bullets": ["Bikes are important"]}]}
APP = {"title": "Bikes", "subtitle": "", "slides": [
    {"type": "stats", "title": "Short car trips are moving to bikes", "notes": "Say it.",
     "stats": [{"value": "31%", "label": "of trips are under 3 km"}, {"value": "2x", "label": "more bike lanes"}]},
    {"type": "bullets", "title": "Bike lanes pay back in four years", "notes": "Say it.",
     "bullets": ["Lanes cost 1 M€ per km", "Saved time is worth 0.3 M€ a year"]},
    {"type": "closing", "title": "Build the lanes where trips are short", "notes": "Say it.",
     "bullets": ["Start with the centre"]}]}


def verdict(app_first, better):
    good, poor = {k: 5 for k in evaluate.CRITERIA}, {k: 2 for k in evaluate.CRITERIA}
    a, b = (good, poor) if app_first else (poor, good)
    return json.dumps({"a": a, "b": b, "better": better, "why": "Concrete numbers."})


@pytest.fixture
def fake(monkeypatch):
    prompts = []

    def ask(provider, model, prompt, schema, api_key):
        prompts.append(prompt)
        if prompt.startswith("Make a presentation about"):
            return json.dumps(PLAIN)
        if "presentation coach" in prompt:
            app_first = prompt.index("<presentation_a>") < prompt.index("stats") < prompt.index("<presentation_b>")
            return verdict(app_first, "A" if app_first else "B")
        return json.dumps(APP)

    monkeypatch.setattr(llm, "_ask", ask)
    return prompts


def test_the_comparison_runs_and_reports_both_sides(fake, tmp_path):
    topics = [("Bikes in cities", "persuade", "city council")]
    conn = {"provider": "gemini", "model": "m"}
    text = evaluate.evaluate(topics, 3, conn, judge_conn=conn, out=tmp_path, pptx=True, log=lambda *a: None)
    assert "The judge preferred the app on 1 of 1 topics" in text
    assert "| judge: specifics (1-5) | 2.00 | 5.00 |" in text
    assert "| Bikes in cities | persuade |" in text and "| app |" in text
    assert "filler" in text                                   # what the check found in the plain deck
    judged = [p for p in fake if "presentation coach" in p]
    assert len(judged) == 2                                   # both orders
    assert "purpose: persuade, audience: city council" in judged[0]
    assert sorted(f.name for f in tmp_path.iterdir()) == ["01_app.json", "01_app.pptx", "01_plain.json",
                                                          "01_plain.pptx"]


def test_a_judge_that_changes_its_mind_with_the_order_is_a_tie(monkeypatch):
    answers = iter([verdict(True, "A"), verdict(False, "A")])    # always prefers whatever is shown first
    monkeypatch.setattr(llm, "_ask", lambda *args: next(answers))
    deck = parse_deck(json.dumps(APP))
    _, _, result = evaluate.judge("t", "inform", "", deck, deck, {"provider": "gemini", "model": "m"})
    assert result == 0


def test_topics_file_and_failed_topics(tmp_path, monkeypatch):
    path = tmp_path / "topics.txt"
    path.write_text("Solar roofs | pitch | investors\nTea\n\n", encoding="utf-8")
    assert evaluate.read_topics(path) == [("Solar roofs", "pitch", "investors"), ("Tea", "inform", "")]

    def broken(*args):
        raise RuntimeError("no key")
    monkeypatch.setattr(llm, "_ask", broken)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    text = evaluate.evaluate([("Tea", "inform", "")], 3, {"provider": "gemini", "model": "m"}, log=lambda *a: None)
    assert "every topic failed" in text
