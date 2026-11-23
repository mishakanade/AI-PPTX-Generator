"""Saving a presentation project to one JSON file and opening it again.

A project file holds everything needed to continue later without asking the AI again:
the content (the Deck), the chosen style and colour theme, the generation settings and
the photos themselves (base64 inside the JSON, so Unsplash is not needed to reopen it).

Opening also accepts a bare deck JSON, for example an answer saved from an AI chat.
"""
import base64
import json

from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS
from generator.content.schema import parse_deck
from generator.content.storytelling import DEFAULT_GOAL, GOALS
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import DEFAULT_THEME, THEMES
from generator.images.unsplash import Photo, make_preview
from generator.render.logo import logo_aspect

FORMAT = "ai-pptx-generator-project"
VERSION = 1


TRANSITIONS = (None, "fade", "push", "wipe")
DEFAULT_SETTINGS = {"tone": next(iter(TONE_PRESETS)), "text_amount": "Balanced", "speaker_notes": True,
                    "goal": DEFAULT_GOAL, "audience": "", "minutes": None, "auto_review": True}


def _one_of(value, options):
    """True if value is one of the names in options. A file may hold anything there, even a list."""
    return isinstance(value, str) and value in options


def clean_settings(raw):
    """The generation settings from a file, each checked; anything missing or odd gets its default.

    The interface reads these settings later (when a slide is rewritten, for example), so a
    file from an older version, a bare deck or an edited file must not leave a gap.
    """
    raw = raw if isinstance(raw, dict) else {}
    settings = dict(DEFAULT_SETTINGS)
    if _one_of(raw.get("tone"), TONE_PRESETS):
        settings["tone"] = raw["tone"]
    if _one_of(raw.get("text_amount"), TEXT_AMOUNT_PRESETS):
        settings["text_amount"] = raw["text_amount"]
    if _one_of(raw.get("goal"), GOALS):
        settings["goal"] = raw["goal"]
    for key in ("speaker_notes", "auto_review"):
        if isinstance(raw.get(key), bool):
            settings[key] = raw[key]
    if isinstance(raw.get("audience"), str):
        settings["audience"] = " ".join(raw["audience"].split())[:200]
    if isinstance(raw.get("minutes"), int) and not isinstance(raw["minutes"], bool) and 0 < raw["minutes"] <= 180:
        settings["minutes"] = raw["minutes"]
    return settings


def save_project(deck, photos, style, theme, settings=None, transition=None, logo=None):
    """The project as JSON bytes. theme is a theme name or a colour dict (custom colours)."""
    data = {
        "format": FORMAT,
        "version": VERSION,
        "deck": deck.model_dump(exclude_none=True),
        "style": style,
        # custom colours are stored as lists of three numbers; a built-in theme by its name
        "theme": {k: list(v) for k, v in theme.items()} if isinstance(theme, dict) else theme,
        "settings": settings or {},
        "transition": transition,
        "logo": base64.b64encode(logo).decode() if logo else None,
        "photos": {
            key: {"data": base64.b64encode(photo.data).decode(), "author": photo.author,
                  "author_url": photo.author_url, "photo_id": photo.photo_id}
            for key, photo in photos.items()
        },
    }
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def load_project(raw):
    """Read a project file (bytes or text).

    Returns a dict with deck, photos, style, theme and settings. Missing or unknown parts
    fall back to defaults; broken photos are skipped. Raises ContentError if there is no
    presentation in the file at all.
    """
    text = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        data = None

    if not isinstance(data, dict) or data.get("format") != FORMAT:
        # not a project file: maybe just a presentation, e.g. an answer saved from an AI chat
        return {"deck": parse_deck(text), "photos": {}, "style": DEFAULT_STYLE, "theme": DEFAULT_THEME,
                "settings": clean_settings(None), "transition": None, "logo": None}

    deck = parse_deck(json.dumps(data.get("deck")))      # the same checks and repairs as a model answer

    photos = {}
    photos_data = data.get("photos") if isinstance(data.get("photos"), dict) else {}
    for key, item in photos_data.items():
        try:
            image = base64.b64decode(item["data"])
            photos[key] = Photo(data=image, preview_url=make_preview(image), author=item.get("author", ""),
                                author_url=item.get("author_url", ""), photo_id=item.get("photo_id", ""))
        except Exception:
            continue                                  # a damaged photo is dropped, the rest still opens

    style = data.get("style") if _one_of(data.get("style"), STYLES) else DEFAULT_STYLE
    theme = data.get("theme")
    if isinstance(theme, dict):
        try:
            theme = {key: tuple(min(255, max(0, int(c))) for c in theme[key])[:3]     # colour parts are 0-255
                     for key in ("bg", "title", "text", "accent")}
            if any(len(color) != 3 for color in theme.values()):
                theme = DEFAULT_THEME
        except (KeyError, TypeError, ValueError):
            theme = DEFAULT_THEME
    elif not _one_of(theme, THEMES):
        theme = DEFAULT_THEME
    transition = data.get("transition") if _one_of(data.get("transition"), TRANSITIONS) else None
    logo = None
    if data.get("logo"):
        try:
            logo = base64.b64decode(data["logo"])
            logo_aspect(logo)                         # check that it really is a picture
        except Exception:
            logo = None
    return {"deck": deck, "photos": photos, "style": style, "theme": theme, "transition": transition, "logo": logo,
            "settings": clean_settings(data.get("settings"))}


