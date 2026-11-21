"""Talking to an AI model: sending the prompt and getting a checked presentation back.

The provider (Gemini, OpenAI or Claude) is chosen by the caller; the provider modules in
content/providers/ hide the differences between their SDKs. Whatever the provider, the
answer goes through the same checks and repairs in schema.py.
"""
import random
import time

from generator import config
from generator.content.providers import PROVIDERS
from generator.content.quality import check_deck, score
from generator.content.schema import ContentError, Deck, Outline, Slide, parse_deck, parse_outline, parse_slide


def _ask(provider, model, prompt, schema, api_key):
    """One request to one model of one provider. Returns the raw text of the answer."""
    return PROVIDERS[provider].ask(model, prompt, schema, api_key)


def _request(prompt, schema, parse, provider, api_key, model, retries_per_model):
    """Send a prompt and return parse(answer), retrying the way generate_deck describes."""
    module = PROVIDERS[provider]
    models = [model] if model else module.default_models()
    last_err = None
    for current in models:
        use_schema = True
        attempt = 0
        while attempt < retries_per_model:
            try:
                return parse(_ask(provider, current, prompt, schema if use_schema else None, api_key))
            except ContentError as e:
                last_err = e              # the answer was unusable: simply ask again
            except Exception as e:
                last_err = e
                verdict = module.classify(e)
                if verdict == "schema" and use_schema:
                    use_schema = False    # schema not accepted: same attempt again without it
                    continue
                if verdict != "retry":
                    raise
                time.sleep(2 ** attempt + random.random())
            attempt += 1
    raise last_err


def _key(provider, api_key):
    """The key to use: the one given, or the provider's key from .env."""
    env_keys = {"gemini": config.GEMINI_API_KEY, "openai": config.OPENAI_API_KEY, "claude": config.ANTHROPIC_API_KEY}
    return api_key or env_keys[provider]


def trim_slides(slides, limit):
    """Cut a deck that came back longer than asked, keeping a closing slide at the end."""
    if len(slides) <= limit:
        return slides
    if slides[-1].type == "closing" and limit > 1:
        return slides[:limit - 1] + [slides[-1]]
    return slides[:limit]


def generate_deck(prompt, max_slides=None, retries_per_model=2, api_key=None, provider="gemini", model=None):
    """Ask a model for a presentation and return it as a checked Deck.

    provider: "gemini", "openai" or "claude"; model: a model name, or None for the
    provider's defaults; api_key: the user's key, or None for the provider's key from .env.

    - Temporary failures (rate limit, server error, timeout) and unusable answers are
      retried with a growing pause, first on the same model, then on the next default one.
    - If a model rejects the strict answer schema, the request is repeated in plain
      JSON mode: the prompt describes the format too, and parse_deck repairs the rest.
    - Any other error (for example a wrong API key) is raised immediately.
    """
    deck = _request(prompt, Deck, parse_deck, provider, _key(provider, api_key), model, retries_per_model)
    if max_slides:
        deck.slides = trim_slides(deck.slides, max_slides)
    return deck


def regenerate_slide(prompt, retries_per_model=2, api_key=None, provider="gemini", model=None):
    """Ask a model for one new slide (see prompt.build_slide_prompt) and return it checked."""
    return _request(prompt, Slide, parse_slide, provider, _key(provider, api_key), model, retries_per_model)


def generate_outline(prompt, retries_per_model=2, api_key=None, provider="gemini", model=None):
    """Ask a model for the plan of a presentation (see prompt.build_outline_prompt)."""
    return _request(prompt, Outline, parse_outline, provider, _key(provider, api_key), model, retries_per_model)


def review_deck(deck, prompt, text_amount="Balanced", speaker_notes=True, retries_per_model=2, api_key=None,
                provider="gemini", model=None):
    """The editor's pass (see prompt.build_review_prompt). Returns the better of draft and revision.

    The revision is kept only if the automatic check finds it at least as good as the draft,
    so this step can never make the presentation worse by the check's measure.
    """
    revised = _request(prompt, Deck, parse_deck, provider, _key(provider, api_key), model, retries_per_model)
    before = score(check_deck(deck, text_amount, speaker_notes))
    after = score(check_deck(revised, text_amount, speaker_notes))
    return revised if after >= before and revised.slides else deck
