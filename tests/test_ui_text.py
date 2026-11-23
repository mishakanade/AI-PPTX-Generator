"""Every interface text exists in every language, with the same {placeholders}."""
import string

import ui_text
from generator.content.schema import SLIDE_TYPE_GUIDE
from generator.design.styles import STYLES


def placeholders(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_all_languages_have_the_same_texts_and_placeholders():
    english = ui_text.TEXTS["en"]
    for lang, texts in ui_text.TEXTS.items():
        missing, extra = set(english) - set(texts), set(texts) - set(english)
        assert not missing and not extra, f"{lang}: missing {missing}, extra {extra}"
        for key, text in texts.items():
            assert placeholders(text) == placeholders(english[key]), (lang, key)


def test_every_slide_type_and_style_has_a_name_in_every_language():
    for lang in ui_text.LANGUAGES:
        assert set(ui_text.SLIDE_TYPES[lang]) == set(SLIDE_TYPE_GUIDE), lang
        if lang != "en":
            assert set(ui_text.STYLE_DESCRIPTIONS[lang]) == set(STYLES), lang
