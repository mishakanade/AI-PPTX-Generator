"""Turning failures into something a user can act on.

The SDKs report problems as exceptions with server messages such as
"400 INVALID_ARGUMENT ... API key not valid". explain() reduces any of them to one of a few
codes; the interface shows advice for the code (in the user's language) and keeps the raw
message under "technical details".

    bad_key          the key was not accepted
    quota            no credit or quota left on the account
    rate_limit       too many requests right now (or the period's quota is used up)
    model_not_found  the model name is unknown to the provider
    overloaded       the provider is overloaded or temporarily down
    network          no connection to the provider
    refused          the model declined the request
    unusable_answer  the answers could not be turned into slides, even after retries
    unknown          anything else
"""
import httpx

from generator.content.providers import PROVIDERS
from generator.content.schema import ContentError


def explain(error, provider=None):
    if isinstance(error, ContentError):
        return "unusable_answer"
    module = PROVIDERS.get(provider)
    code = module.explain(error) if module else None
    if code:
        return code
    if isinstance(error, (httpx.TimeoutException, httpx.ConnectError, ConnectionError, TimeoutError)):
        return "network"
    return "unknown"
