"""Developer tool: the app with a pretend AI and pretend Unsplash, to look at the interface.

Every screen can be reached without any API key: "Generate" returns the built-in example
presentation (in Russian when the topic is in Russian) after a short pause, photos are the
drawn example picture, and "fix", "rewrite this slide" and "plan first" answer with example
content too. Nothing is sent anywhere. Run from the project folder:

    python -m streamlit run tools/ui_demo.py
"""
import re
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generator import config  # noqa: E402
from generator.content import llm  # noqa: E402
from generator.content.schema import Outline, OutlineSlide  # noqa: E402
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU, sample_photo, sample_photo_url  # noqa: E402
from generator.images import unsplash  # noqa: E402

PAUSE = 1.5   # seconds: long enough to see the progress messages


def _example(prompt):
    return SAMPLE_DECK_RU if re.search("[а-яё]", prompt or "", re.IGNORECASE) else SAMPLE_DECK


def generate_deck(prompt, max_slides=None, **kwargs):
    time.sleep(PAUSE)
    deck = _example(prompt).model_copy(deep=True)
    deck.slides = llm.trim_slides(deck.slides, max_slides) if max_slides else deck.slides
    return deck


def review_deck(deck, prompt, *args, **kwargs):
    time.sleep(PAUSE)
    return deck


def regenerate_slide(prompt, **kwargs):
    time.sleep(PAUSE)
    return _example(prompt).slides[2].model_copy(deep=True)


def generate_outline(prompt, **kwargs):
    time.sleep(PAUSE)
    deck = _example(prompt)
    return Outline(title=deck.title, subtitle=deck.subtitle,
                   slides=[OutlineSlide(type=s.type, title=s.title, focus=s.subtitle) for s in deck.slides])


def fetch_photos(keywords, client_id=None):
    photo = unsplash.Photo(sample_photo(), sample_photo_url(), "Demo Author", "https://unsplash.com")
    return {keyword: photo for keyword in keywords}, []


def fetch_another(keyword, exclude_ids, client_id=None):
    return unsplash.Photo(sample_photo(), sample_photo_url(), "Another Author", "https://unsplash.com",
                          photo_id=f"demo-{len(exclude_ids)}"), []


llm.generate_deck, llm.review_deck, llm.regenerate_slide = generate_deck, review_deck, regenerate_slide
llm.generate_outline = generate_outline
unsplash.fetch_photos, unsplash.fetch_another = fetch_photos, fetch_another
config.GEMINI_API_KEY = config.GEMINI_API_KEY or "demo"
config.UNSPLASH_CLIENT_ID = config.UNSPLASH_CLIENT_ID or "demo"

runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
