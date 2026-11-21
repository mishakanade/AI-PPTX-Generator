"""Streamlit interface. All generation logic lives in the generator/ package.

Streamlit reruns this whole file from top to bottom on every click. Everything that
must survive between reruns (the generated presentation, the photos, the chosen style)
is kept in st.session_state.

Every text on the page comes from ui_text.py, in the language chosen in the sidebar.
Widgets have fixed keys, so what the user typed survives a change of language.
"""
import hashlib
import re
import uuid

import streamlit as st

import ui_text
from generator import config
from generator.content.documents import DocumentReadError, extract_text_from_file
from generator.content.editing import apply_edits, slide_to_text
from generator.content.llm import generate_deck, regenerate_slide, trim_slides
from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS
from generator.content.schema import ContentError, parse_deck, parse_slide
from generator.content.prompt import MAX_DOC_CHARS, build_prompt, build_slide_prompt
from generator.design.colors import from_hex, readable_theme, to_hex
from generator.design.sample_deck import SAMPLE_DECKS, SAMPLE_IMAGE, sample_photo_url
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import THEMES
from generator.images.unsplash import fetch_another, fetch_photos, keywords_for, own_photo
from generator.project import load_project, save_project
from generator.render.builder import build_pptx, build_preview, theme_colors
from generator.render.logo import logo_aspect

PREVIEW_COLUMNS = 3

# The AI providers the user can choose from. "chat" means copy & paste with any AI chat app.
PROVIDERS = {
    "gemini": {"name": "Gemini", "env": "GEMINI_API_KEY", "url": "https://aistudio.google.com/api-keys"},
    "openai": {"name": "OpenAI", "env": "OPENAI_API_KEY", "url": "https://platform.openai.com/api-keys"},
    "claude": {"name": "Anthropic", "env": "ANTHROPIC_API_KEY", "url": "https://platform.claude.com"},
    "chat": None,
}
DEFAULT_MODELS = {"gemini": config.MODELS[0], "openai": config.OPENAI_MODEL, "claude": config.CLAUDE_MODEL}
CUSTOM_THEME = "custom"                  # internal value of the "custom colours" choice
UNSPLASH_LINK = "https://unsplash.com/?utm_source=ai_pptx_generator&utm_medium=referral"


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


def tr(key, **values):
    """The text with this key in the current language, with {placeholders} filled in."""
    text = ui_text.TEXTS[current_language()].get(key) or ui_text.TEXTS["en"][key]
    return text.format(**values) if values else text


# ----- small helpers -----------------------------------------------------------------------

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
    """Four colour chips of the selected theme."""
    chips = "".join(
        f'<div title="{name}" style="flex:1;height:26px;background:{to_hex(tuple(theme[name]))};"></div>'
        for name in ("bg", "title", "text", "accent")
    )
    st.html(
        '<div style="display:flex;border-radius:6px;overflow:hidden;'
        f'box-shadow:0 0 0 1px rgba(128,128,128,0.35);">{chips}</div>'
    )


def select_style(style_key):
    st.session_state["style"] = style_key


def edit_section(deck):
    """A form to change the text of the slides or delete slides, then redraw without Gemini."""
    lang = current_language()
    # The widget keys include a version number: after a new generation or after applying edits
    # the form starts again from the current content instead of keeping old typed values.
    version = st.session_state.setdefault("edit_version", 0)
    with st.expander(tr("edit_header")):
        st.caption(tr("edit_caption"))
        with st.form(f"edit_form_{version}", border=False):
            title = st.text_input(tr("deck_title"), deck.title, key=f"e{version}_title")
            subtitle = st.text_input(tr("deck_subtitle"), deck.subtitle, key=f"e{version}_subtitle")
            edits = []
            for i, slide in enumerate(deck.slides):
                st.divider()
                head, remove = st.columns([4, 1], vertical_alignment="center")
                type_name = ui_text.pick(ui_text.SLIDE_TYPES, lang, slide.type)
                head.markdown("**" + tr("slide_heading", number=i + 2, type=type_name) + "**")
                delete = remove.checkbox(tr("delete"), key=f"e{version}_{i}_delete")
                slide_title = st.text_input(tr("slide_title"), slide.title, key=f"e{version}_{i}_title")
                text = slide_to_text(slide)
                hint = ui_text.EDIT_HINTS[lang].get(slide.type) or ui_text.EDIT_HINTS["en"].get(slide.type)
                body = st.text_area(
                    tr("slide_text"), text, key=f"e{version}_{i}_text", help=hint,
                    height=max(68, min(260, 26 * (text.count("\n") + 2))),
                )
                author = None
                if slide.type == "quote":
                    author = st.text_input(tr("author"), slide.author or "", key=f"e{version}_{i}_author")
                edits.append(None if delete else (slide_title, body, author))
            applied = st.form_submit_button(tr("apply"), type="primary", key=f"apply_{version}")
    if applied:
        if all(edit is None for edit in edits):
            st.warning(tr("keep_one"))
            return
        st.session_state["deck"] = apply_edits(deck, title, subtitle, edits)
        st.session_state.pop("rendered_design", None)    # forces the redraw block to run
        st.session_state["edit_version"] = version + 1
        st.rerun()


def regenerate_section(deck):
    """Rewrite one chosen slide with the AI, optionally following the user's wish."""
    version = st.session_state.get("edit_version", 0)
    with st.expander(tr("regen_header")):
        st.caption(tr("regen_caption"))
        index = st.selectbox(
            tr("regen_slide"), range(len(deck.slides)), key=f"regen_slide_{version}",
            format_func=lambda i: f"{i + 2}. {deck.slides[i].title}",
        )
        wish = st.text_input(tr("regen_wish"), placeholder=tr("regen_wish_placeholder"), key=f"regen_wish_{version}")

        # the slide is written with the settings of the original generation
        settings = st.session_state.get("settings") or {"tone": next(iter(TONE_PRESETS)),
                                                        "text_amount": "Balanced", "speaker_notes": True}
        prompt = build_slide_prompt(deck, index, wish, settings["tone"], settings["text_amount"],
                                    settings["speaker_notes"], for_chat=provider == "chat")

        if provider == "chat":
            # copy & paste: show the request, read the pasted answer
            if st.button(tr("regen_chat_show"), key="regen_chat_show"):
                st.session_state["regen_chat_prompt"] = (version, index, prompt)
            shown = st.session_state.get("regen_chat_prompt")
            if not shown or shown[0] != version or shown[1] != index:
                return
            st.code(shown[2], language=None, wrap_lines=True, height=220)
            answer = st.text_area(tr("chat_answer"), placeholder=tr("chat_answer_placeholder"),
                                  key=f"regen_chat_answer_{version}")
            if not st.button(tr("regen_chat_apply"), key="regen_chat_apply"):
                return
            if not answer.strip():
                st.warning(tr("chat_need_answer"))
                return
            try:
                slide = parse_slide(answer)
            except ContentError as e:
                st.error(tr("chat_bad_answer", error=e))
                return
        else:
            if not st.button(tr("regen_button"), key="regen_button", disabled=not ai_key):
                return
            with st.spinner(tr("regen_working", provider=provider_name)):
                try:
                    slide = regenerate_slide(prompt, api_key=ai_key, provider=provider, model=ai_model)
                except Exception as e:
                    st.error(tr("error", error=e))
                    return

    photos = st.session_state["photos"]
    if slide.type in ("bullets", "image") and slide.image_keyword and slide.image_keyword not in photos:
        found, _ = fetch_photos([slide.image_keyword], client_id=unsplash_key)
        photos.update(found)
    slides = list(deck.slides)
    slides[index] = slide
    st.session_state["deck"] = deck.model_copy(update={"slides": slides})
    st.session_state.pop("rendered_design", None)    # forces the redraw block to run
    st.session_state.pop("regen_chat_prompt", None)
    st.session_state["edit_version"] = version + 1     # the edit form shows the new text
    st.rerun()


def store_deck(deck, topic, settings):
    """Keep a freshly written deck and its photos in the session; the file is drawn later."""
    photos, photo_warnings = fetch_photos(keywords_for(deck), client_id=unsplash_key)
    st.session_state["deck"] = deck
    st.session_state["photos"] = photos
    st.session_state["photo_warnings"] = photo_warnings
    st.session_state["file_name"] = safe_file_name(topic)
    st.session_state["settings"] = settings
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1


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
                            style=project["style"], transition=project["transition"])
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


def take_logo():
    """Called when a logo file is chosen: keep it in the session if it is a picture."""
    uploaded = st.session_state.get("logo_file")
    if not uploaded:
        return
    try:
        logo_aspect(uploaded.getvalue())
    except ValueError:
        st.session_state["logo_message"] = tr("logo_not_image")
        return
    st.session_state["logo"] = uploaded.getvalue()


def remove_logo():
    st.session_state.pop("logo", None)


def changed_photos(deck=None):
    """After a photo change: store the deck if it changed, and make the file be drawn again."""
    if deck is not None:
        st.session_state["deck"] = deck
    st.session_state.pop("rendered_design", None)
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1


def set_slide_keyword(index, keyword):
    deck = st.session_state["deck"]
    slides = list(deck.slides)
    slides[index] = slides[index].model_copy(update={"image_keyword": keyword})
    return deck.model_copy(update={"slides": slides})


def another_photo(index):
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    keyword = deck.slides[index].image_keyword
    used = {photo.photo_id for photo in photos.values() if photo.photo_id}
    photo, warnings = fetch_another(keyword, used, client_id=unsplash_key)
    if photo:
        photos[keyword] = photo
        changed_photos()
    else:
        st.session_state["photo_message"] = tr(warnings[0]) if warnings else tr("photo_none_found", keyword=keyword)


def upload_photo(index, widget_key):
    uploaded = st.session_state.get(widget_key)
    if not uploaded:
        return
    try:
        photo = own_photo(uploaded.getvalue())
    except ValueError:
        st.session_state["photo_message"] = tr("photo_not_image")
        return
    key = f"upload-{uuid.uuid4().hex[:8]}"     # own pictures get their own key: never searched on Unsplash
    st.session_state["photos"][key] = photo
    changed_photos(set_slide_keyword(index, key))


def remove_photo(index):
    changed_photos(set_slide_keyword(index, None))


def photos_section(deck, photos):
    """Per slide that can show a photo: its current picture and the ways to change it."""
    version = st.session_state.get("edit_version", 0)
    with st.expander(tr("photos_header")):
        st.caption(tr("photos_caption"))
        message = st.session_state.pop("photo_message", None)
        if message:
            st.warning(message)
        for i, slide in enumerate(deck.slides):
            if slide.type not in ("bullets", "image"):
                continue
            keyword = slide.image_keyword
            photo = photos.get(keyword) if keyword else None
            picture, controls = st.columns([1, 3], vertical_alignment="center")
            with picture:
                if photo:
                    st.image(photo.preview_url, width="stretch")
                else:
                    st.caption(tr("no_photo"))
            with controls:
                st.markdown(f"**{i + 2}. {plain(slide.title)}**")
                buttons = st.columns(2)
                can_search = bool(keyword) and not keyword.startswith("upload-") and bool(unsplash_key)
                buttons[0].button(tr("another_photo"), key=f"another_{version}_{i}", disabled=not can_search,
                                  on_click=another_photo, args=(i,), width="stretch")
                buttons[1].button(tr("remove_photo"), key=f"remove_{version}_{i}", disabled=not photo,
                                  on_click=remove_photo, args=(i,), width="stretch")
                widget_key = f"own_{version}_{i}"
                st.file_uploader(tr("upload_photo"), type=["png", "jpg", "jpeg", "webp"], key=widget_key,
                                 on_change=upload_photo, args=(i, widget_key), label_visibility="collapsed")


def forget_presentation():
    for key in ("deck", "photos", "photo_warnings", "file_name", "pptx_bytes", "preview", "rendered_design",
                "chat_request", "regen_chat_prompt"):
        st.session_state.pop(key, None)


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


# ----- page header and language --------------------------------------------------------------

st.set_page_config(page_title="AI PPTX Generator", page_icon="📊", layout="wide")
st.session_state.setdefault("lang", browser_language())
st.session_state.setdefault("style", DEFAULT_STYLE)

with st.sidebar:
    st.segmented_control(
        tr("language"), options=list(ui_text.LANGUAGES), format_func=ui_text.LANGUAGES.get,
        key="lang", label_visibility="collapsed",
    )
lang = current_language()

st.title("📊 AI PPTX Generator")
st.caption(tr("page_caption"))


# ----- AI provider and API keys -------------------------------------------------------------
# A key is taken from, in this order: the field in the sidebar (kept only in this browser
# session), the .env file, or the secrets of a hosted app (Streamlit Community Cloud).

with st.sidebar:
    st.subheader(tr("ai_header"))
    provider = st.selectbox(tr("provider"), list(PROVIDERS), key="provider",
                            format_func=lambda key: tr(f"provider_{key}"))

info = PROVIDERS[provider]
server_ai_key = None
if info:
    server_ai_key = getattr(config, info["env"]) \
        or secret(info["env"])
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

ai_key = (typed_ai_key or server_ai_key) if info else None
provider_name = {"gemini": "Gemini", "openai": "ChatGPT", "claude": "Claude"}.get(provider, "")
unsplash_key = typed_unsplash_key or server_unsplash_key

if info and not ai_key:
    st.info(tr("need_ai_key", provider=info["name"], url=info["url"], env=info["env"]))
elif not unsplash_key:
    st.info(tr("no_unsplash_key"))


# ----- sidebar: what the presentation is about -----------------------------------------------

with st.sidebar:
    st.header(tr("content"))
    with st.form("generation_form"):
        topic = st.text_input(tr("topic"), placeholder=tr("topic_placeholder"), key="topic")
        uploaded_file = st.file_uploader(tr("document"), type=["txt", "pdf", "docx"], key="document")
        selected_tone = st.selectbox(
            tr("tone"), options=list(TONE_PRESETS.keys()), key="tone",
            format_func=lambda key: ui_text.pick(ui_text.TONES, lang, key),
        )
        selected_text_amount = st.selectbox(
            tr("text_amount"), options=list(TEXT_AMOUNT_PRESETS.keys()), index=2, key="text_amount",
            format_func=lambda key: ui_text.pick(ui_text.TEXT_AMOUNTS, lang, key),
        )
        additional_commentary = st.text_input(tr("wishes"), placeholder=tr("wishes_placeholder"), key="wishes")
        num_slides = st.slider(tr("num_slides"), min_value=2, max_value=15, value=6, step=1, key="num_slides")
        speaker_notes = st.checkbox(tr("speaker_notes"), value=True, help=tr("speaker_notes_help"),
                                    key="speaker_notes")
        submit_button = st.form_submit_button(tr("generate"), type="primary", width="stretch", key="generate")
    st.caption(tr("design_hint"))
    st.file_uploader(tr("open_project"), type=["json"], key="project_file", on_change=open_project,
                     help=tr("open_project_help"))

error = st.session_state.pop("project_error", None)
if error:
    st.error(tr("project_error", error=error))


# ----- design: colours and style ------------------------------------------------------------

st.subheader(tr("design"))
theme_column, transition_column, _ = st.columns([1, 1, 1])
with theme_column:
    theme_choice = st.selectbox(
        tr("colour_theme"), list(THEMES.keys()) + [CUSTOM_THEME], key="theme",
        format_func=lambda name: tr("custom_colours") if name == CUSTOM_THEME else name,
    )
    if theme_choice == CUSTOM_THEME:
        # four colour pickers, starting from the first built-in theme
        start = THEMES[next(iter(THEMES))]
        labels = {key: tr(f"colour_{key}") for key in ("bg", "title", "text", "accent")}
        picked = {
            # a colour already in the session (e.g. from an opened project) is used as it is
            key: from_hex(column.color_picker(label, key=f"custom_{key}",
                                              **({} if f"custom_{key}" in st.session_state
                                                 else {"value": to_hex(tuple(start[key]))})))
            for column, (key, label) in zip(st.columns(4), labels.items())
        }
        selected_theme, changed = readable_theme(**picked)
        if changed:
            st.caption(tr("adjusted", names=", ".join(labels[name].lower() for name in changed)))
        theme_label = tr("theme_custom")
    else:
        selected_theme, theme_label = theme_choice, tr("theme_named", name=theme_choice)
    show_swatches(theme_colors(selected_theme))

with transition_column:
    transition = st.selectbox(
        tr("transition"), [None, "fade", "push", "wipe"], key="transition", help=tr("transition_help"),
        format_func=lambda name: tr(f"transition_{name or 'none'}"),
    )
    # the logo lives in the session (not only in the uploader), so that an opened project can set it
    logo = st.session_state.get("logo")
    if logo:
        picture, button = st.columns([1, 1], vertical_alignment="center")
        picture.image(logo, width=110)
        button.button(tr("logo_remove"), key="logo_remove", on_click=remove_logo)
    else:
        st.file_uploader(tr("logo"), type=["png", "jpg", "jpeg", "webp"], key="logo_file", on_change=take_logo,
                         help=tr("logo_help"))
    message = st.session_state.pop("logo_message", None)
    if message:
        st.warning(message)
logo_id = hashlib.sha1(logo).hexdigest() if logo else None

st.markdown(f"**{tr('style')}**")
for column, (style_key, style) in zip(st.columns(len(STYLES)), STYLES.items()):
    with column, st.container(border=True):
        # each card shows the real title slide of the example deck in this style and theme
        show_slide(sample_preview(style_key, selected_theme, lang)[0])
        st.markdown(f"**{style.name}**")
        st.caption(ui_text.pick(ui_text.STYLE_DESCRIPTIONS, lang, style_key, default=style.description))
        is_selected = st.session_state["style"] == style_key
        st.button(
            tr("selected") if is_selected else tr("select"),
            key=f"style_{style_key}",
            type="primary" if is_selected else "secondary",
            on_click=select_style, args=(style_key,),
            width="stretch",
        )
selected_style = st.session_state["style"]

st.divider()


# ----- generation: runs once, when the form is submitted ------------------------------------

if submit_button:
    doc_text = ""
    try:
        doc_text = extract_text_from_file(uploaded_file)
    except DocumentReadError as e:
        st.warning(tr("doc_ignored", reason=tr(f"doc_{e.reason}", name=e.file_name)))
    if len(doc_text) > MAX_DOC_CHARS:
        st.info(tr("doc_long", used=MAX_DOC_CHARS, total=len(doc_text)))

    if info and not ai_key:
        st.warning(tr("add_key_first", provider=info["name"]))
    elif not topic.strip() and not doc_text.strip():
        st.warning(tr("need_topic"))
    else:
        prompt = build_prompt(
            topic=topic,
            doc_text=doc_text,
            tone=selected_tone,
            text_amount=selected_text_amount,
            commentary=additional_commentary,
            num_slides=num_slides,
            speaker_notes=speaker_notes,
            for_chat=provider == "chat",
        )
        settings = {"tone": selected_tone, "text_amount": selected_text_amount, "speaker_notes": speaker_notes}
        forget_presentation()          # the previous presentation is replaced by the new one

        if provider == "chat":
            # copy & paste: the request is shown below; the deck is built when the answer comes back
            st.session_state["chat_request"] = {"prompt": prompt, "topic": topic, "num_slides": num_slides,
                                                "settings": settings}
        else:
            with st.status(tr("status_writing", provider=provider_name), expanded=False) as status:
                try:
                    deck = generate_deck(prompt, max_slides=num_slides, api_key=ai_key,
                                         provider=provider, model=ai_model)
                    status.update(label=tr("status_photos"))
                    # The content and its photos are kept for the whole session;
                    # the file itself is built from them in the block below.
                    store_deck(deck, topic, settings)
                    status.update(label=tr("status_done"), state="complete")
                except Exception as e:
                    status.update(label=tr("status_failed"), state="error")
                    st.error(tr("error", error=e))


# ----- copy & paste mode: show the request, read the answer ---------------------------------

request = st.session_state.get("chat_request")
if request and "deck" not in st.session_state:
    st.subheader(tr("chat_header"))
    st.markdown(tr("chat_steps"))
    st.code(request["prompt"], language=None, wrap_lines=True, height=300)
    pasted = st.text_area(tr("chat_answer"), placeholder=tr("chat_answer_placeholder"), height=200,
                          key="chat_answer")
    answer_file = st.file_uploader(tr("chat_file"), type=["json", "txt", "md"], key="chat_file")
    if st.button(tr("chat_build"), type="primary", key="chat_build"):
        answer = answer_file.getvalue().decode("utf-8", errors="ignore") if answer_file else pasted
        if not answer.strip():
            st.warning(tr("chat_need_answer"))
        else:
            try:
                deck = parse_deck(answer)
            except ContentError as e:
                st.error(tr("chat_bad_answer", error=e))
            else:
                deck.slides = trim_slides(deck.slides, request["num_slides"])
                with st.spinner(tr("status_photos")):
                    store_deck(deck, request["topic"], request["settings"])
                st.rerun()


# ----- rendering: runs whenever the content or the design changed ---------------------------

# Whenever there is content and it was not drawn for the currently selected style and
# theme (a new generation, or the user picked another design), draw it again.
# No Gemini or Unsplash calls happen here, so switching designs is instant.
design = (selected_style, selected_theme, transition, logo_id)
if "deck" in st.session_state and st.session_state.get("rendered_design") != design:
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    try:
        st.session_state["pptx_bytes"] = build_pptx(
            deck, selected_style, selected_theme,
            images={key: photo.data for key, photo in photos.items()},
            credits={key: photo.credit for key, photo in photos.items() if photo.credit},
            transition=transition,
            logo=logo,
        )
        st.session_state["preview"] = build_preview(
            deck, selected_style, selected_theme,
            {key: photo.preview_url for key, photo in photos.items()},
            logo=logo,
        )
        st.session_state["rendered_design"] = design
    except Exception as e:
        st.session_state.pop("pptx_bytes", None)
        st.error(tr("build_error", error=e))


# ----- result -------------------------------------------------------------------------------

if "pptx_bytes" in st.session_state:
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    title_column, button_column = st.columns([2, 1], vertical_alignment="bottom")
    with title_column:
        st.subheader(plain(deck.title))
        st.caption(tr("result_caption", count=len(deck.slides) + 1, style=STYLES[selected_style].name,
                      theme=theme_label))
    with button_column:
        st.download_button(
            label=tr("download"),
            data=st.session_state["pptx_bytes"],
            file_name=st.session_state["file_name"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
            width="stretch",
            key="download",
        )
        st.download_button(
            label=tr("save_project"),
            data=save_project(deck, photos, selected_style, selected_theme, st.session_state.get("settings"),
                              transition, logo),
            file_name=st.session_state["file_name"].removesuffix(".pptx") + ".project.json",
            mime="application/json",
            width="stretch",
            key="save_project",
            help=tr("save_project_help"),
        )
    for warning in st.session_state.get("photo_warnings", []):
        st.warning(f"⚠️ {tr(warning)}")

    show_slides(st.session_state["preview"])
    st.caption(tr("preview_note"))
    edit_section(deck)
    photos_section(deck, photos)
    regenerate_section(deck)

    slides_with_notes = [(tr("title_slide"), deck.notes)] + [(slide.title, slide.notes) for slide in deck.slides]
    if any(notes for _, notes in slides_with_notes):
        with st.expander(tr("notes_header")):
            for number, (title, notes) in enumerate(slides_with_notes, 1):
                if notes:
                    st.markdown(f"**{number}. {plain(title)}**")
                    st.markdown(plain(notes))
            st.caption(tr("notes_note"))
    unsplash_photos = {keyword: photo for keyword, photo in photos.items() if photo.author}
    if unsplash_photos:
        with st.expander(tr("credits_header")):
            for keyword, photo in unsplash_photos.items():
                st.markdown(tr("credit_line", keyword=plain(keyword), author=plain(photo.author), url=photo.author_url,
                               unsplash=UNSPLASH_LINK))
            st.caption(tr("credits_note"))
    with st.expander(tr("json_header")):
        st.json(deck.model_dump(exclude_none=True))
else:
    st.subheader(tr("example"))
    st.caption(tr("example_caption"))
    show_slides(sample_preview(selected_style, selected_theme, lang))
