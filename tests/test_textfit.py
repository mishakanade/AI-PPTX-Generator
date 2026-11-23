"""Predicting text size (generator/render/textfit.py)."""
from generator.render.primitives import Para, Text
from generator.render.textfit import (
    best_scale,
    count_lines,
    fit,
    fit_single_line,
    text_height,
    text_width,
)


def test_wider_text_is_wider_and_bold_is_wider_than_regular():
    assert text_width("WWW", "Calibri", 20) > text_width("iii", "Calibri", 20)
    assert text_width("Hello", "Arial", 20, bold=True) > text_width("Hello", "Arial", 20)
    assert text_width("Привет", "Calibri", 20) > 0    # Cyrillic has real widths, not a fallback


def test_line_count_grows_when_the_box_gets_narrower():
    text = "one two three four five six seven eight nine ten"
    assert count_lines(text, "Calibri", 18, 20.0) == 1
    assert count_lines(text, "Calibri", 18, 2.0) > count_lines(text, "Calibri", 18, 4.0)


def test_a_word_longer_than_the_line_is_broken():
    assert count_lines("Supercalifragilisticexpialidocious", "Arial", 40, 2.0) >= 3


def test_fit_shrinks_text_until_it_fits():
    block = Text(0, 0, 3.0, 1.0, [Para("word " * 20)], size=24)
    assert text_height(block) > 1.0
    fit(block)
    assert text_height(block) <= 1.0
    assert block.size < 24


def test_fit_never_shrinks_below_the_readable_limit():
    # far too much text: it is shrunk to 55% at most and allowed to overflow,
    # because unreadably small text is worse than text that runs long
    block = Text(0, 0, 3.0, 1.0, [Para("word " * 60)], size=24)
    fit(block)
    assert block.size >= 24 * 0.55 - 0.1


def test_fit_can_grow_sparse_text_when_allowed():
    block = Text(0, 0, 8.0, 4.0, [Para("Short")], size=18)
    assert best_scale(block, max_scale=1.3) > 1.0
    assert best_scale(block) == 1.0          # by default text is never enlarged


def test_fit_single_line():
    size = fit_single_line("1 234 567 km", "Arial", 66, 2.0, bold=True)
    assert size < 66
    assert text_width("1 234 567 km", "Arial", size, bold=True) <= 2.0
