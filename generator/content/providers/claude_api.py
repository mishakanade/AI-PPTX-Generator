"""Anthropic Claude through the anthropic SDK (Messages API with structured outputs)."""
import functools

import anthropic

from generator import config
from generator.content.schema import ContentError

# Models that accept server-side refusal fallbacks ("default" routing). On the rare occasion
# a safety classifier declines a request, the API re-runs it on a suitable fallback model.
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class RefusalError(Exception):
    """Claude declined the request (stop_reason "refusal"); retrying the same request will not help."""


@functools.lru_cache(maxsize=8)
def get_client(api_key):
    # max_retries=0: retries are done by llm.py, the same way for every provider
    return anthropic.Anthropic(api_key=api_key, max_retries=0)


def default_models():
    return [config.CLAUDE_MODEL]


def ask(model, prompt, schema, api_key):
    request = {
        "model": model,
        "max_tokens": 16000,
        "messages": [{"role": "user", "content": prompt}],
        # Claude Opus 5.5 always thinks; effort sets how much ("medium" is its default, set explicitly)
        "output_config": {"effort": "medium"},
    }
    if model in FALLBACK_MODELS:
        request["betas"] = [FALLBACK_BETA]
        request["fallbacks"] = "default"
    client = get_client(api_key)
    if schema is not None:
        response = client.beta.messages.parse(output_format=schema, **request)
    else:
        response = client.beta.messages.create(**request)

    if response.stop_reason == "refusal":
        raise RefusalError("Claude declined to write this presentation. Try rephrasing the topic.")
    if response.stop_reason == "max_tokens":
        raise ContentError("The answer was cut off because it was too long. Please try again.")
    parsed = getattr(response, "parsed_output", None)
    if parsed is not None:
        return parsed.model_dump_json()
    return "".join(block.text for block in response.content if block.type == "text")


def classify(error):
    if isinstance(error, (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError)):
        return "retry"           # APIConnectionError includes timeouts; InternalServerError covers 5xx
    if isinstance(error, anthropic.APIStatusError) and error.status_code >= 500:
        return "retry"           # overloaded (529) and other server-side errors
    if isinstance(error, anthropic.BadRequestError):
        return "schema"
    return "fatal"
