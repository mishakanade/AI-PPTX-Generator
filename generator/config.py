"""Settings shared by the whole app: API keys and model names.

Keys are read from the .env file (see .env.example) or from real environment variables.
"""
import os

from dotenv import load_dotenv

load_dotenv()

def _read_key(name):
    """Return the key, or None when it is missing or still the placeholder from .env.example."""
    value = (os.getenv(name) or "").strip()
    if not value or value.lower().startswith("your "):
        return None
    return value


GEMINI_API_KEY = _read_key("GEMINI_API_KEY")
UNSPLASH_CLIENT_ID = _read_key("UNSPLASH_CLIENT_ID")

# Tried in this order: if the first model is overloaded, the next one is used.
MODELS = ["gemini-3.8-flash", "gemini-3.7-flash"]
