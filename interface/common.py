"""Translations, small helpers and values shared by the interface modules."""
import re
from dataclasses import dataclass
from typing import Optional

import streamlit as st

import ui_text
from generator import config
from generator.content.errors import explain
from generator.design.colors import to_hex
from generator.design.sample_deck import SAMPLE_DECKS, SAMPLE_IMAGE, sample_photo_url
from generator.render.builder import build_preview

PREVIEW_COLUMNS = 3
CUSTOM_THEME = "custom"                  # internal value of the "custom colours" choice
UNSPLASH_LINK = "https://unsplash.com/?utm_source=ai_pptx_generator&utm_medium=referral"

# The AI providers the user can choose from. "chat" means copy & paste with any AI chat app.
PROVIDERS = {
    "gemini": {"name": "Gemini", "env": "GEMINI_API_KEY", "url": "https://aistudio.google.com/api-keys"},
    "openai": {"name": "OpenAI", "env": "OPENAI_API_KEY", "url": "https://platform.openai.com/api-keys"},
    "claude": {"name": "Anthropic", "env": "ANTHROPIC_API_KEY", "url": "https://platform.claude.com"},
    "chat": None,
}
DEFAULT_MODELS = {"gemini": config.MODELS[0], "openai": config.OPENAI_MODEL, "claude": config.CLAUDE_MODEL}
PROVIDER_NAMES = {"gemini": "Gemini", "openai": "ChatGPT", "claude": "Claude"}


def current_settings():
    """The generation settings of the current presentation, with defaults for whatever is missing
    (a project saved by an older version, or a deck opened from a bare JSON file)."""
    from generator.content.presets import TONE_PRESETS
    defaults = {"tone": next(iter(TONE_PRESETS)), "text_amount": "Balanced", "speaker_notes": True}
    return {**defaults, **(st.session_state.get("settings") or {})}


@dataclass
class Connection:
    """Who writes the content and with which keys, as chosen in the sidebar."""
    provider: str                 # "gemini", "openai", "claude" or "chat"
    ai_key: Optional[str]         # None in chat mode or when no key is known
    ai_model: Optional[str]       # None for the provider's default model
    unsplash_key: Optional[str]

    @property
    def info(self):
        return PROVIDERS[self.provider]

    @property
    def is_chat(self):
        return self.provider == "chat"

    @property
    def name(self):
        """The provider's name for status messages, e.g. "Claude"."""
        return PROVIDER_NAMES.get(self.provider, "")


# ----- language -----------------------------------------------------------------------------

def browser_language():
    """'ru' if the browser asks for Russian, otherwise 'en'."""
    try:
        locale = st.context.locale or ""
    except Exception:
        locale = ""
    return "ru" if locale.lower().startswith("ru") else "en"


def current_language():
    # the language switch can be clicked off (no choice): English then
    return st.session_state.get("lang") or "en"


def tr_in(lang):
    """A translation function fixed to one language (for list labels, which Streamlit may
    format again later, outside the run that created them)."""
    return lambda key: ui_text.TEXTS[lang].get(key) or ui_text.TEXTS["en"][key]


def tr(key, **values):
    """The text with this key in the current language, with {placeholders} filled in."""
    text = ui_text.TEXTS[current_language()].get(key) or ui_text.TEXTS["en"][key]
    return text.format(**values) if values else text


# ----- small helpers -----------------------------------------------------------------------

def plain(text):
    """Text from the model or from Unsplash, made safe to show through Markdown.

    Markdown would turn ![](address) into a picture loaded from that address, so a document
    with hidden instructions could make the model plant one. Every Markdown character is
    escaped with a backslash, which makes Streamlit show it as an ordinary character.
    """
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$:])", r"\\\1", str(text or ""))


def safe_file_name(topic):
    """A file name made from the topic, without characters that file systems reject."""
    name = re.sub(r'[\\/:*?"<>|\r\n]+', " ", topic).strip()[:80].strip(" .")
    return f"{name or 'presentation'}.pptx"


def secret(name):
    """A value from .streamlit/secrets.toml or the hosting's secrets, or None if there are none."""
    try:
        return st.secrets.get(name)
    except Exception:          # no secrets file at all
        return None


def show_error(error, conn):
    """Advice the user can act on, with the raw message kept under "technical details"."""
    code = explain(error, conn.provider)
    provider = conn.info["name"] if conn.info else conn.name
    st.error(tr(f"err_{code}", provider=provider, model=conn.ai_model or DEFAULT_MODELS.get(conn.provider, ""),
                error=error))
    if code != "unknown":
        with st.expander(tr("error_details")):
            st.code(str(error)[:3000], language=None, wrap_lines=True)


def forget_presentation():
    """Remove the current presentation and everything that belongs to it from the session."""
    for key in ("deck", "photos", "photo_warnings", "file_name", "pptx_bytes", "preview", "rendered_design",
                "chat_request", "regen_chat_prompt", "outline", "outline_request", "data"):
        st.session_state.pop(key, None)


# ----- slide previews -----------------------------------------------------------------------

def show_slide(slide_html):
    """Show one slide preview with a thin frame around it."""
    st.html(
        '<div style="border-radius:8px;overflow:hidden;box-shadow:0 0 0 1px rgba(128,128,128,0.35);">'
        f"{slide_html}</div>"
    )


def show_slides(slide_htmls):
    """Show slide previews as a grid."""
    columns = st.columns(PREVIEW_COLUMNS)
    for i, slide_html in enumerate(slide_htmls):
        with columns[i % PREVIEW_COLUMNS]:
            show_slide(slide_html)


@st.cache_data(show_spinner=False)
def sample_preview(style_key, theme_name, lang):
    """The built-in example deck in the interface language, drawn in a style and theme. Cached."""
    deck = SAMPLE_DECKS.get(lang, SAMPLE_DECKS["en"])
    return build_preview(deck, style_key, theme_name, {SAMPLE_IMAGE: sample_photo_url()})


def show_swatches(theme):
    """Four colour chips of a theme."""
    chips = "".join(
        f'<div title="{name}" style="flex:1;height:26px;background:{to_hex(tuple(theme[name]))};"></div>'
        for name in ("bg", "title", "text", "accent")
    )
    st.html(
        '<div style="display:flex;border-radius:6px;overflow:hidden;'
        f'box-shadow:0 0 0 1px rgba(128,128,128,0.35);">{chips}</div>'
    )
