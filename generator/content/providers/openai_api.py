"""OpenAI (ChatGPT models) through the openai SDK and its Responses API."""
import functools

import openai
from openai.lib._pydantic import to_strict_json_schema

from generator import config


@functools.lru_cache(maxsize=8)
def get_client(api_key):
    # max_retries=0: retries are done by llm.py, the same way for every provider
    return openai.OpenAI(api_key=api_key, timeout=180, max_retries=0)


def default_models():
    return [config.OPENAI_MODEL]


def ask(model, prompt, schema, api_key):
    if schema is not None:
        # strict structured output: the answer is guaranteed to follow the schema
        text_format = {"type": "json_schema", "name": schema.__name__.lower(), "strict": True,
                       "schema": to_strict_json_schema(schema)}
    else:
        text_format = {"type": "json_object"}     # any valid JSON; the prompt describes the shape
    response = get_client(api_key).responses.create(model=model, input=prompt, text={"format": text_format})
    return response.output_text


def classify(error):
    if isinstance(error, openai.RateLimitError):
        # an exhausted balance is also reported as 429, but waiting will not help
        return "fatal" if getattr(error, "code", None) == "insufficient_quota" else "retry"
    if isinstance(error, (openai.InternalServerError, openai.APIConnectionError)):   # includes timeouts
        return "retry"
    if isinstance(error, openai.BadRequestError):
        return "schema"
    return "fatal"


def explain(error):
    """What went wrong, as a code the interface turns into advice (see content/errors.py)."""
    if isinstance(error, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return "bad_key"
    if isinstance(error, openai.NotFoundError):
        return "model_not_found"
    if isinstance(error, openai.RateLimitError):
        return "quota" if getattr(error, "code", None) == "insufficient_quota" else "rate_limit"
    if isinstance(error, openai.InternalServerError):
        return "overloaded"
    if isinstance(error, openai.APIConnectionError):        # includes timeouts
        return "network"
    return None
