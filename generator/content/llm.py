"""Talking to Gemini: sending the prompt and turning the answer into Python data."""
import functools
import json
import random
import re
import time

import httpx
from google import genai
from google.genai import types

from generator import config


@functools.lru_cache(maxsize=1)
def get_client():
    """Create the Gemini client on first use and reuse the same one afterwards."""
    return genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=45_000))


def generate_structure_with_retry(prompt, retries_per_model=2):
    """Ask Gemini for the presentation structure and return its raw text answer.

    Temporary failures (rate limit, server error, timeout) are retried with a growing
    pause, first on the same model and then on the next one in config.MODELS.
    Any other error (for example a wrong API key) is raised immediately.
    """
    last_err = None
    for model in config.MODELS:
        for attempt in range(retries_per_model):
            try:
                response = get_client().models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                    ),
                )
                return response.text
            except Exception as e:
                last_err = e
                code = getattr(e, "code", None)
                if code not in (429, 500, 503, 504) and not isinstance(e, httpx.TimeoutException):
                    raise
                time.sleep(2 ** attempt + random.random())
    raise last_err


def parse_slides_json(raw_text):
    """Turn the model's text answer into a dict, ignoring any text around the JSON object."""
    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    clean_text = json_match.group(0) if json_match else raw_text.strip()
    return json.loads(clean_text)
