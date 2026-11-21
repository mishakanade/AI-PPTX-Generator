"""Talking to Gemini: sending the prompt and getting a checked presentation back."""
import functools
import random
import time

import httpx
from google import genai
from google.genai import types

from generator import config
from generator.content.schema import ContentError, Deck, parse_deck

RETRYABLE_CODES = (429, 500, 503, 504)   # rate limit and temporary server problems


@functools.lru_cache(maxsize=8)
def get_client(api_key):
    """Create a Gemini client for a key on first use and reuse it afterwards."""
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))


def _ask(model, prompt, use_schema, api_key):
    """One request to one model. Returns the raw text of the answer."""
    response = get_client(api_key).models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            # With the schema the model is technically unable to answer in another shape.
            response_schema=Deck if use_schema else None,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return response.text


def trim_slides(slides, limit):
    """Cut a deck that came back longer than asked, keeping a closing slide at the end."""
    if len(slides) <= limit:
        return slides
    if slides[-1].type == "closing" and limit > 1:
        return slides[:limit - 1] + [slides[-1]]
    return slides[:limit]


def generate_deck(prompt, max_slides=None, retries_per_model=2, api_key=None):
    """Ask Gemini for a presentation and return it as a checked Deck.

    api_key: the user's key; by default the one from .env (config.GEMINI_API_KEY).

    - Temporary failures (rate limit, server error, timeout) and unusable answers are
      retried with a growing pause, first on the same model, then on the next one in
      config.MODELS.
    - If a model rejects the strict answer schema, the request is repeated in plain
      JSON mode: the prompt describes the format too, and parse_deck repairs the rest.
    - Any other error (for example a wrong API key) is raised immediately.
    """
    api_key = api_key or config.GEMINI_API_KEY
    last_err = None
    for model in config.MODELS:
        use_schema = True
        attempt = 0
        while attempt < retries_per_model:
            try:
                deck = parse_deck(_ask(model, prompt, use_schema, api_key))
                if max_slides:
                    deck.slides = trim_slides(deck.slides, max_slides)
                return deck
            except ContentError as e:
                last_err = e              # the answer was unusable: simply ask again
            except Exception as e:
                last_err = e
                code = getattr(e, "code", None)
                if code == 400 and use_schema:
                    use_schema = False    # schema not accepted: same attempt again without it
                    continue
                if code not in RETRYABLE_CODES and not isinstance(e, httpx.TimeoutException):
                    raise
                time.sleep(2 ** attempt + random.random())
            attempt += 1
    raise last_err
