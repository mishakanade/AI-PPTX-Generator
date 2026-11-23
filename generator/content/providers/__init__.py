"""One module per AI provider. Each has the same four functions:

    ask(model, prompt, schema, api_key) -> str
        Send the prompt and return the raw text of the answer. schema is the pydantic class
        the answer must follow, or None to ask for plain JSON without a strict schema.

    classify(error) -> "retry" | "schema" | "fatal"
        What to do after an error: wait and try again, try again without the strict schema
        (the model rejected it), or give up and show the error to the user.

    explain(error) -> "bad_key" | "quota" | "rate_limit" | "model_not_found" | "overloaded" | ... | None
        A short code for a failure, which the interface turns into advice for the user
        (see generator/content/errors.py); None when the provider does not recognise it.

    default_models() -> list of model names, tried in order.

llm.py runs the shared retry loop and does not know which provider it is talking to.
"""
from generator.content.providers import claude_api, gemini, openai_api

PROVIDERS = {"gemini": gemini, "openai": openai_api, "claude": claude_api}
