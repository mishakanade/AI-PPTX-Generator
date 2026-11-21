"""Saving a presentation project to one JSON file and opening it again.

A project file holds everything needed to continue later without asking the AI again:
the content (the Deck), the chosen style and colour theme, the generation settings and
the photos themselves (base64 inside the JSON, so Unsplash is not needed to reopen it).

Opening also accepts a bare deck JSON, for example an answer saved from an AI chat.
"""
import base64
import json

from generator.content.schema import parse_deck
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import DEFAULT_THEME, THEMES
from generator.images.unsplash import Photo, make_preview

FORMAT = "ai-pptx-generator-project"
VERSION = 1


TRANSITIONS = (None, "fade", "push", "wipe")


def save_project(deck, photos, style, theme, settings=None, transition=None):
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
    except json.JSONDecodeError:
        data = None

    if not isinstance(data, dict) or data.get("format") != FORMAT:
        # not a project file: maybe just a presentation, e.g. an answer saved from an AI chat
        return {"deck": parse_deck(text), "photos": {}, "style": DEFAULT_STYLE, "theme": DEFAULT_THEME,
                "settings": {}, "transition": None}

    deck = parse_deck(json.dumps(data.get("deck")))      # the same checks and repairs as a model answer

    photos = {}
    for key, item in (data.get("photos") or {}).items():
        try:
            image = base64.b64decode(item["data"])
            photos[key] = Photo(data=image, preview_url=make_preview(image), author=item.get("author", ""),
                                author_url=item.get("author_url", ""), photo_id=item.get("photo_id", ""))
        except Exception:
            continue                                  # a damaged photo is dropped, the rest still opens

    style = data.get("style") if data.get("style") in STYLES else DEFAULT_STYLE
    theme = data.get("theme")
    if isinstance(theme, dict):
        try:
            theme = {k: tuple(int(c) for c in theme[k])[:3] for k in ("bg", "title", "text", "accent")}
        except (KeyError, TypeError, ValueError):
            theme = DEFAULT_THEME
    elif theme not in THEMES:
        theme = DEFAULT_THEME
    transition = data.get("transition") if data.get("transition") in TRANSITIONS else None
    return {"deck": deck, "photos": photos, "style": style, "theme": theme, "transition": transition,
            "settings": data.get("settings") if isinstance(data.get("settings"), dict) else {}}


