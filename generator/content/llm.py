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


@functools.lru_cache(maxsize=1)
def get_client():
    """Create the Gemini client on first use and reuse the same one afterwards."""
    return genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=60_000))


def _ask(model, prompt, use_schema):
    """One request to one model. Returns the raw text of the answer."""
    response = get_client().models.generate_content(
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


def generate_deck(prompt, max_slides=None, retries_per_model=2):
    """Ask Gemini for a presentation and return it as a checked Deck.

    - Temporary failures (rate limit, server error, timeout) and unusable answers are
      retried with a growing pause, first on the same model, then on the next one in
      config.MODELS.
    - If a model rejects the strict answer schema, the request is repeated in plain
      JSON mode: the prompt describes the format too, and parse_deck repairs the rest.
    - Any other error (for example a wrong API key) is raised immediately.
    """
    last_err = None
    for model in config.MODELS:
        use_schema = True
        attempt = 0
        while attempt < retries_per_model:
            try:
                deck = parse_deck(_ask(model, prompt, use_schema))
                if max_slides:
                    deck.slides = deck.slides[:max_slides]
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
