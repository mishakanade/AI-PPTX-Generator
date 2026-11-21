"""Google Gemini through the google-genai SDK."""
import functools

import httpx
from google import genai
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
