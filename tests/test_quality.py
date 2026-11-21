"""The content checks (generator/content/quality.py)."""
from generator.content.quality import check_deck, describe_for_model, score
from generator.content.schema import Card, Deck, Slide, Stat
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU


def codes(deck, **kwargs):
    return [(issue.code, issue.slide) for issue in check_deck(deck, **kwargs)]


def deck_of(*slides, title="Urban mobility in 2030", subtitle="How cities change"):
    return Deck(title=title, subtitle=subtitle, slides=list(slides))


GOOD_NOTES = "Say this out loud."


def test_topic_label_titles_are_flagged_but_takeaways_are_not():
    deck = deck_of(
        Slide(type="bullets", title="Problems", bullets=["a b c"], notes=GOOD_NOTES),
        Slide(type="bullets", title="Cars take most street space but carry few trips", bullets=["x y z"],
              notes=GOOD_NOTES),
        Slide(type="agenda", title="Agenda", bullets=["one", "two"], notes=GOOD_NOTES),
    )
    assert ("title_label", 0) in codes(deck)
    assert not [c for c in codes(deck) if c[1] in (1, 2) and c[0] == "title_label"]


def test_filler_phrases_in_both_languages():
    en = deck_of(Slide(type="bullets", title="Shared bikes cut short car trips",
                       bullets=["In today's world bikes matter"], notes=GOOD_NOTES))
    ru = deck_of(Slide(type="bullets", title="Велосипеды заменяют короткие поездки на машине",
                       bullets=["Важно отметить, что велосипеды полезны"], notes=GOOD_NOTES),
                 title="Городская мобильность", subtitle="Обзор")
    assert ("filler", 0) in codes(en) and ("filler", 0) in codes(ru)


def test_too_much_text_and_long_items():
    long_bullets = ["word " * 30] * 3
    deck = deck_of(
        Slide(type="bullets", title="Too many words on one slide here", bullets=long_bullets, notes=GOOD_NOTES),
        Slide(type="cards", title="Three cards with very long texts inside", notes=GOOD_NOTES,
              cards=[Card(heading="A", text="word " * 50), Card(heading="B", text="short")]),
    )
    found = codes(deck, text_amount="Balanced")
    assert ("too_much_text", 0) in found and ("long_items", 1) in found


def test_repeated_points_across_slides():
    point = "Electric buses reduce noise and exhaust on busy city streets"
    deck = deck_of(
        Slide(type="bullets", title="Electric buses make streets quieter", bullets=[point], notes=GOOD_NOTES),
        Slide(type="bullets", title="Fleet renewal is the main lever", notes=GOOD_NOTES,
              bullets=["Electric buses reduce exhaust and noise on busy city streets"]),
    )
    assert ("repeat", 1) in codes(deck)


def test_stats_language_runs_closing_and_notes():
    deck = deck_of(
        Slide(type="stats", title="The numbers behind the shift to bikes",
              stats=[Stat(value="many", label="riders"), Stat(value="12%", label="share")]),
        Slide(type="bullets", title="Велосипедов становится больше каждый год", bullets=["Да"], notes=GOOD_NOTES),
        Slide(type="bullets", title="Second bullets slide with a takeaway", bullets=["b"], notes=GOOD_NOTES),
        Slide(type="bullets", title="Third bullets slide with a takeaway", bullets=["c"], notes=GOOD_NOTES),
    )
    found = codes(deck)
    assert ("stat_without_number", 0) in found
    assert ("language_mix", 1) in found
    assert ("same_type_run", 3) in found
    assert ("no_closing", None) in found
    assert ("missing_notes", None) in found
    assert ("missing_notes", None) not in codes(deck, speaker_notes=False)


def test_the_built_in_examples_are_mostly_clean_and_the_report_is_readable():
    for deck in (SAMPLE_DECK, SAMPLE_DECK_RU):
        issues = check_deck(deck, speaker_notes=False)
        assert score(issues) >= 60
        assert not [i for i in issues if i.code in ("language_mix", "repeat", "filler")]
    text = describe_for_model(check_deck(deck_of(Slide(type="bullets", title="Problems", bullets=["a"]))))
    assert text.startswith("1. slide 2:") and "names a topic" in text
