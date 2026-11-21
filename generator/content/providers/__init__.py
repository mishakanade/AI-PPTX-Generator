"""One module per AI provider. Each has the same three functions:

    ask(model, prompt, schema, api_key) -> str
        Send the prompt and return the raw text of the answer. schema is the pydantic class
        the answer must follow, or None to ask for plain JSON without a strict schema.

    classify(error) -> "retry" | "schema" | "fatal"
        What to do after an error: wait and try again, try again without the strict schema
        (the model rejected it), or give up and show the error to the user.

    default_models() -> list of model names, tried in order.

llm.py runs the shared retry loop and does not know which provider it is talking to.
"""
from generator.content.providers import claude_api, gemini, openai_api

PROVIDERS = {"gemini": gemini, "openai": openai_api, "claude": claude_api}
