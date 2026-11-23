"""The OpenAI and Claude providers, talking to a local fake server instead of the real API.

The real SDKs build and send real HTTP requests; the fake server records them and answers
with a canned response in the provider's format. This checks what is actually sent
(model, structured-output schema, beta headers) and how answers and errors are handled.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic
import openai
import pytest

from generator.content import llm
from generator.content.providers import claude_api, openai_api
from generator.content.schema import Deck

DECK = {"title": "T", "subtitle": "S", "slides": [{"type": "bullets", "title": "A", "bullets": ["x", "y"]}]}


class FakeServer:
    """Answers every POST with the next scripted (status, body) and records the requests."""

    def __init__(self):
        self.requests, self.script = [], []
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                headers = {name.lower(): value for name, value in self.headers.items()}
                recorder.requests.append({"path": self.path, "headers": headers, "body": body})
                status, answer = recorder.script.pop(0)
                data = json.dumps(answer).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")      # never send local requests to a proxy
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    fake = FakeServer()
    monkeypatch.setattr(openai_api, "get_client",
                        lambda key: openai.OpenAI(api_key=key, base_url=fake.url + "/v1", max_retries=0))
    monkeypatch.setattr(claude_api, "get_client",
                        lambda key: anthropic.Anthropic(api_key=key, base_url=fake.url, max_retries=0))
    yield fake
    fake.close()


def openai_answer(text):
    return {"id": "resp_1", "object": "response", "created_at": 0, "model": "m", "status": "completed",
            "output": [{"type": "message", "id": "msg_1", "status": "completed", "role": "assistant",
                        "content": [{"type": "output_text", "text": text, "annotations": []}]}]}


def claude_answer(text, stop_reason="end_turn"):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": text}] if text else [], "stop_reason": stop_reason,
            "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 10}}


def error(kind, message="nope"):
    return {"error": {"type": kind, "message": message, "code": kind}}


# ----- OpenAI -----------------------------------------------------------------------------

def test_openai_sends_a_strict_schema_and_reads_the_answer(server):
    server.script.append((200, openai_answer(json.dumps(DECK))))
    deck = llm.generate_deck("Make a deck about JSON", provider="openai", api_key="sk-test")
    assert deck.slides[0].bullets == ["x", "y"]
    sent = server.requests[0]
    assert sent["path"] == "/v1/responses"
    assert sent["headers"]["authorization"] == "Bearer sk-test"
    assert sent["body"]["model"] == "gpt-6.2-astra"
    fmt = sent["body"]["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["name"] == "deck"
    assert fmt["schema"]["additionalProperties"] is False


def test_openai_falls_back_to_json_mode_when_the_schema_is_rejected(server):
    server.script += [(400, error("invalid_request_error")), (200, openai_answer(json.dumps(DECK)))]
    llm.generate_deck("JSON please", provider="openai", api_key="k", model="my-model")
    assert [r["body"]["text"]["format"]["type"] for r in server.requests] == ["json_schema", "json_object"]
    assert server.requests[1]["body"]["model"] == "my-model"


def test_openai_rate_limit_is_retried_but_an_empty_balance_is_not(server):
    server.script += [(429, error("rate_limit_exceeded")), (200, openai_answer(json.dumps(DECK)))]
    llm.generate_deck("JSON", provider="openai", api_key="k")
    assert len(server.requests) == 2

    server.requests.clear()
    server.script.append((429, error("insufficient_quota")))
    with pytest.raises(openai.RateLimitError):
        llm.generate_deck("JSON", provider="openai", api_key="k")
    assert len(server.requests) == 1


# ----- Claude -----------------------------------------------------------------------------

def test_claude_sends_structured_output_effort_and_fallbacks(server):
    server.script.append((200, claude_answer(json.dumps(DECK))))
    deck = llm.generate_deck("Make a deck", provider="claude", api_key="sk-ant-test")
    assert deck.title == "T"
    sent = server.requests[0]
    assert sent["path"].startswith("/v1/messages")
    assert sent["headers"]["authorization"] == "Bearer sk-ant-test"   # how the 2.x SDK sends the key
    assert "server-side-fallback-2026-07-01" in sent["headers"]["anthropic-beta"]
    body = sent["body"]
    assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default"
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "thinking" not in body                     # Opus 5.5 always thinks; the parameter is left out


def test_claude_model_without_fallbacks_gets_no_fallback_parameter(server):
    server.script.append((200, claude_answer(json.dumps(DECK))))
    llm.generate_deck("x", provider="claude", api_key="k", model="claude-haiku-5-5")
    body, headers = server.requests[0]["body"], server.requests[0]["headers"]
    assert "fallbacks" not in body and "server-side-fallback" not in headers.get("anthropic-beta", "")


def test_claude_refusal_is_reported_and_not_retried(server):
    server.script.append((200, claude_answer("", stop_reason="refusal")))
    with pytest.raises(claude_api.RefusalError):
        llm.generate_deck("x", provider="claude", api_key="k")
    assert len(server.requests) == 1


def test_claude_overload_is_retried_and_a_bad_key_is_not(server):
    server.script += [(529, error("overloaded_error")), (200, claude_answer(json.dumps(DECK)))]
    llm.generate_deck("x", provider="claude", api_key="k")
    assert len(server.requests) == 2

    server.requests.clear()
    server.script.append((401, error("authentication_error")))
    with pytest.raises(anthropic.AuthenticationError):
        llm.generate_deck("x", provider="claude", api_key="bad")
    assert len(server.requests) == 1


def test_claude_schema_rejection_retries_without_schema(server):
    server.script += [(400, error("invalid_request_error")), (200, claude_answer("Here:\n" + json.dumps(DECK)))]
    deck = llm.generate_deck("x", provider="claude", api_key="k")
    assert deck.slides[0].title == "A"
    assert "format" in server.requests[0]["body"]["output_config"]
    assert "format" not in server.requests[1]["body"]["output_config"]


def test_regenerating_one_slide_through_claude(server):
    server.script.append((200, claude_answer(json.dumps({"type": "statement", "title": "Key", "subtitle": "One idea"}))))
    slide = llm.regenerate_slide("x", provider="claude", api_key="k")
    assert slide.type == "statement" and slide.subtitle == "One idea"
    assert server.requests[0]["body"]["output_config"]["format"]["type"] == "json_schema"


def test_deck_schema_is_accepted_by_both_sdks():
    from anthropic.lib._parse._transform import transform_schema
    from openai.lib._pydantic import to_strict_json_schema
    assert to_strict_json_schema(Deck)["additionalProperties"] is False
    assert transform_schema(Deck)["additionalProperties"] is False


# ----- turning failures into advice -----------------------------------------------------------

def failure(callable_):
    try:
        callable_()
    except Exception as e:      # noqa: BLE001 - the point is to look at whatever was raised
        return e
    raise AssertionError("no error was raised")


@pytest.mark.parametrize("status, kind, code", [
    (401, "invalid_api_key", "bad_key"),
    (404, "model_not_found", "model_not_found"),
    (429, "insufficient_quota", "quota"),
    (429, "rate_limit_exceeded", "rate_limit"),
    (500, "server_error", "overloaded"),
])
def test_openai_errors_become_advice(server, status, kind, code):
    from generator.content.errors import explain
    server.script += [(status, error(kind))] * 4
    e = failure(lambda: llm.generate_deck("JSON", provider="openai", api_key="k", retries_per_model=1))
    assert explain(e, "openai") == code


@pytest.mark.parametrize("status, kind, message, code", [
    (401, "authentication_error", "invalid x-api-key", "bad_key"),
    (404, "not_found_error", "model: nope", "model_not_found"),
    (429, "rate_limit_error", "slow down", "rate_limit"),
    (529, "overloaded_error", "Overloaded", "overloaded"),
    (400, "invalid_request_error", "Your credit balance is too low to access the API", "quota"),
])
def test_claude_errors_become_advice(server, status, kind, message, code):
    from generator.content.errors import explain
    server.script += [(status, {"type": "error", "error": {"type": kind, "message": message}})] * 4
    e = failure(lambda: llm.generate_deck("x", provider="claude", api_key="k", retries_per_model=1))
    assert explain(e, "claude") == code


def test_claude_refusal_and_unusable_answers_become_advice(server):
    from generator.content.errors import explain
    server.script.append((200, claude_answer("", stop_reason="refusal")))
    assert explain(failure(lambda: llm.generate_deck("x", provider="claude", api_key="k")), "claude") == "refused"
    server.script += [(200, claude_answer("no json at all"))] * 2
    e = failure(lambda: llm.generate_deck("x", provider="claude", api_key="k"))
    assert explain(e, "claude") == "unusable_answer"


@pytest.mark.parametrize("status, message, code", [
    (400, "API key not valid. Please pass a valid API key.", "bad_key"),
    (403, "Permission denied", "bad_key"),
    (404, "models/nope is not found", "model_not_found"),
    (429, "Resource has been exhausted", "rate_limit"),
    (503, "The model is overloaded", "overloaded"),
    (400, "Something else", "unknown"),
])
def test_gemini_errors_become_advice(status, message, code):
    from google.genai import errors
    from generator.content.errors import explain
    error_class = errors.ServerError if status >= 500 else errors.ClientError
    e = error_class(status, {"error": {"code": status, "message": message, "status": "X"}})
    assert explain(e, "gemini") == code


def test_network_failures_become_advice():
    import httpx
    from generator.content.errors import explain
    assert explain(httpx.ConnectTimeout("timed out"), "gemini") == "network"
    assert explain(ValueError("strange"), "gemini") == "unknown"
