"""Settings shared by the whole app: API keys and model names.

Keys are read from the .env file (see .env.example) or from real environment variables.
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
UNSPLASH_CLIENT_ID = os.getenv("UNSPLASH_CLIENT_ID")

# Tried in this order: if the first model is overloaded, the next one is used.
MODELS = ["gemini-3.8-flash", "gemini-3.7-flash"]
