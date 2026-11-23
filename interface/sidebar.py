"""The sidebar: language, which AI writes the content and its keys, the content form, opening a project."""
from dataclasses import dataclass

import streamlit as st

import ui_text
from generator import config
from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS
from generator.content.schema import ContentError
from generator.content.storytelling import DEFAULT_GOAL, GOALS
from generator.design.colors import to_hex
from generator.project import load_project
from interface.common import (
    CUSTOM_THEME,
    DEFAULT_MODELS,
    PROVIDERS,
    Connection,
    current_language,
    forget_presentation,
    safe_file_name,
    secret,
    tr,
    tr_in,
)


@dataclass
class ContentForm:
    """What the user filled in about the presentation."""
    submitted: bool
    topic: str
    uploaded_file: object
    tone: str
    text_amount: str
    commentary: str
    num_slides: int
    speaker_notes: bool
    outline_first: bool
    data_file: object = None
    goal: str = DEFAULT_GOAL
    audience: str = ""
    minutes: int = 0
    auto_review: bool = True

    @property
    def settings(self):
        """The choices that also matter later, e.g. when one slide is regenerated."""
        return {"tone": self.tone, "text_amount": self.text_amount, "speaker_notes": self.speaker_notes,
                "goal": self.goal, "audience": self.audience, "minutes": self.minutes or None,
                "auto_review": self.auto_review}


def language_switch():
    with st.sidebar:
        st.segmented_control(
            tr("language"), options=list(ui_text.LANGUAGES), format_func=ui_text.LANGUAGES.get,
            key="lang", label_visibility="collapsed",
        )


def connection():
    """The AI provider, its model and the keys. Shows a hint in the page when a key is missing.

    A key is taken from, in this order: the field in the sidebar (kept only in this browser
    session), the .env file, or the secrets of a hosted app (Streamlit Community Cloud).
    """
    lang = current_language()
    with st.sidebar:
        st.subheader(tr("ai_header"))
        provider = st.selectbox(tr("provider"), list(PROVIDERS), key="provider",
                                format_func=lambda key, t=tr_in(lang): t(f"provider_{key}"))

    info = PROVIDERS[provider]
    server_ai_key = (getattr(config, info["env"]) or secret(info["env"])) if info else None
    server_unsplash_key = config.UNSPLASH_CLIENT_ID or secret("UNSPLASH_CLIENT_ID")

    with st.sidebar:
        typed_ai_key, ai_model = "", None
        if info:
            ai_model = st.text_input(tr("model"), key=f"model_{provider}", placeholder=DEFAULT_MODELS[provider],
                                     help=tr("model_help")).strip() or None
        else:
            st.caption(tr("chat_mode_info"))
        with st.expander(tr("keys_header"), expanded=bool(info) and not server_ai_key):
            if info:
                typed_ai_key = st.text_input(
                    tr(f"{provider}_key"), type="password", key=f"{provider}_key",
                    placeholder=tr("key_on_server") if server_ai_key else tr("key_paste"),
                    help=tr("key_get", url=info["url"]),
                ).strip()
            typed_unsplash_key = st.text_input(
                tr("unsplash_key"), type="password", key="unsplash_key",
                placeholder=tr("key_on_server") if server_unsplash_key else tr("key_no_photos"),
                help=tr("key_get", url="https://unsplash.com/developers"),
            ).strip()
            st.caption(tr("keys_note"))

    conn = Connection(provider=provider, ai_key=(typed_ai_key or server_ai_key) if info else None,
                      ai_model=ai_model, unsplash_key=typed_unsplash_key or server_unsplash_key)
    if info and not conn.ai_key:
        st.info(tr("need_ai_key", provider=info["name"], url=info["url"], env=info["env"]))
    elif not conn.unsplash_key:
        st.info(tr("no_unsplash_key"))
    return conn


def content_form():
    """The form about the presentation, and the field to open a saved project under it."""
    lang = current_language()
    with st.sidebar:
        st.header(tr("content"))
        with st.form("generation_form"):
            topic = st.text_input(tr("topic"), placeholder=tr("topic_placeholder"), key="topic")
            uploaded_file = st.file_uploader(tr("document"), type=["txt", "pdf", "docx"], key="document")
            data_file = st.file_uploader(tr("data_file"), type=["csv", "xlsx"], key="data_file",
                                         help=tr("data_file_help"))
            goal = st.selectbox(
                tr("goal"), options=list(GOALS), key="goal", help=tr("goal_help"),
                format_func=lambda key: ui_text.pick(ui_text.GOALS, lang, key),
            )
            audience = st.text_input(tr("audience"), placeholder=tr("audience_placeholder"), key="audience")
            tone = st.selectbox(
                tr("tone"), options=list(TONE_PRESETS.keys()), key="tone",
                format_func=lambda key: ui_text.pick(ui_text.TONES, lang, key),
            )
            text_amount = st.selectbox(
                tr("text_amount"), options=list(TEXT_AMOUNT_PRESETS.keys()), index=2, key="text_amount",
                format_func=lambda key: ui_text.pick(ui_text.TEXT_AMOUNTS, lang, key),
            )
            commentary = st.text_input(tr("wishes"), placeholder=tr("wishes_placeholder"), key="wishes")
            num_slides = st.slider(tr("num_slides"), min_value=2, max_value=15, value=6, step=1, key="num_slides")
            minutes = st.number_input(tr("minutes"), min_value=0, max_value=120, value=0, step=5, key="minutes",
                                      help=tr("minutes_help"))
            speaker_notes = st.checkbox(tr("speaker_notes"), value=True, help=tr("speaker_notes_help"),
                                        key="speaker_notes")
            outline_first = st.checkbox(tr("outline_first"), value=False, help=tr("outline_first_help"),
                                        key="outline_first")
            auto_review = st.checkbox(tr("auto_review"), value=True, help=tr("auto_review_help"), key="auto_review")
            submitted = st.form_submit_button(tr("generate"), type="primary", width="stretch", key="generate")
        st.caption(tr("design_hint"))
        st.file_uploader(tr("open_project"), type=["json"], key="project_file", on_change=open_project,
                         help=tr("open_project_help"))

    error = st.session_state.pop("project_error", None)
    if error:
        st.error(tr("project_error", error=error))
    return ContentForm(submitted, topic, uploaded_file, tone, text_amount, commentary, num_slides,
                       speaker_notes, outline_first, data_file, goal, audience, int(minutes or 0), auto_review)


def open_project():
    """Called when a project file is chosen: restore the presentation, its design and settings."""
    uploaded = st.session_state.get("project_file")
    if not uploaded:
        return
    try:
        project = load_project(uploaded.getvalue())
    except ContentError as e:
        st.session_state["project_error"] = str(e)
        return
    forget_presentation()
    deck = project["deck"]
    st.session_state.update(deck=deck, photos=project["photos"], photo_warnings=[],
                            file_name=safe_file_name(deck.title), settings=project["settings"],
                            style=project["style"], transition=project["transition"] or "none")
    if project["logo"]:
        st.session_state["logo"] = project["logo"]
    else:
        st.session_state.pop("logo", None)
    theme = project["theme"]
    if isinstance(theme, dict):
        # custom colours: switch the theme list to "custom" and put the colours into the pickers
        st.session_state["theme"] = CUSTOM_THEME
        for key, color in theme.items():
            st.session_state[f"custom_{key}"] = to_hex(tuple(color))
    else:
        st.session_state["theme"] = theme
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1
