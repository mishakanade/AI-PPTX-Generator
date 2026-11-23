"""Google Gemini through the google-genai SDK."""
import functools

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from generator import config

RETRYABLE_CODES = (429, 500, 503, 504)   # rate limit and temporary server problems


@functools.lru_cache(maxsize=8)
def get_client(api_key):
    """Create a Gemini client for a key on first use and reuse it afterwards."""
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))


def default_models():
    return list(config.MODELS)


def ask(model, prompt, schema, api_key):
    response = get_client(api_key).models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            # With the schema the model is technically unable to answer in another shape.
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return response.text


def classify(error):
    code = getattr(error, "code", None)
    if code == 400:
        return "schema"
    if code in RETRYABLE_CODES or isinstance(error, httpx.TimeoutException):
        return "retry"
    return "fatal"


def explain(error):
    """What went wrong, as a code the interface turns into advice (see content/errors.py)."""
    if not isinstance(error, genai_errors.APIError):
        return None
    message = (error.message or "").lower()
    if error.code in (401, 403) or (error.code == 400 and "api key" in message):
        return "bad_key"
    if error.code == 404:
        return "model_not_found"
    if error.code == 429:
        return "rate_limit"        # Gemini reports both a request limit and a used-up quota as 429
    if error.code and error.code >= 500:
        return "overloaded"
    return None
