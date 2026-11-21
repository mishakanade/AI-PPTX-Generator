"""Streamlit interface. All generation logic lives in the generator/ package.

Streamlit reruns this whole file from top to bottom on every click. Everything that
must survive between reruns (the generated presentation, the photos, the chosen style)
is kept in st.session_state.
"""
import re

import streamlit as st

from generator import config
from generator.content.documents import DocumentReadError, extract_text_from_file
from generator.content.editing import HINTS, TYPE_NAMES, apply_edits, slide_to_text
from generator.content.llm import generate_deck
from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS
from generator.content.prompt import MAX_DOC_CHARS, build_prompt
from generator.design.colors import to_hex
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo_url
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import THEMES
from generator.images.unsplash import fetch_photos, keywords_for
from generator.render.builder import build_pptx, build_preview

PREVIEW_COLUMNS = 3


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
def sample_preview(style_key, theme_name):
    """The built-in example deck drawn in a style and theme. Cached: it never changes."""
    return build_preview(SAMPLE_DECK, style_key, theme_name, {SAMPLE_IMAGE: sample_photo_url()})


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
    # The widget keys include a version number: after a new generation or after applying edits
    # the form starts again from the current content instead of keeping old typed values.
    version = st.session_state.setdefault("edit_version", 0)
    with st.expander("✏️ Edit slides"):
        st.caption("Change titles and text, or delete slides. The file is redrawn without a new request "
                   "to Gemini; photos and speaker notes are kept.")
        with st.form(f"edit_form_{version}", border=False):
            title = st.text_input("Presentation title", deck.title, key=f"e{version}_title")
            subtitle = st.text_input("Subtitle", deck.subtitle, key=f"e{version}_subtitle")
            edits = []
            for i, slide in enumerate(deck.slides):
                st.divider()
                head, remove = st.columns([4, 1], vertical_alignment="center")
                head.markdown(f"**Slide {i + 2} · {TYPE_NAMES[slide.type]}**")
                delete = remove.checkbox("Delete", key=f"e{version}_{i}_delete")
                slide_title = st.text_input("Title", slide.title, key=f"e{version}_{i}_title")
                text = slide_to_text(slide)
                body = st.text_area(
                    "Text", text, key=f"e{version}_{i}_text", help=HINTS.get(slide.type),
                    height=max(68, min(260, 26 * (text.count("\n") + 2))),
                )
                author = None
                if slide.type == "quote":
                    author = st.text_input("Author", slide.author or "", key=f"e{version}_{i}_author")
                edits.append(None if delete else (slide_title, body, author))
            applied = st.form_submit_button("Apply changes", type="primary")
    if applied:
        if all(edit is None for edit in edits):
            st.warning("⚠️ At least one slide must stay.")
            return
        st.session_state["deck"] = apply_edits(deck, title, subtitle, edits)
        st.session_state.pop("rendered_design", None)    # forces the redraw block to run
        st.session_state["edit_version"] = version + 1
        st.rerun()


def safe_file_name(topic):
    """A file name made from the topic, without characters that file systems reject."""
    name = re.sub(r'[\\/:*?"<>|\r\n]+', " ", topic).strip()[:80].strip(" .")
    return f"{name or 'presentation'}.pptx"


# ----- page header and key checks -----------------------------------------------------------

st.set_page_config(page_title="AI PPTX Generator", page_icon="📊", layout="wide")
st.title("📊 AI PPTX Generator")
st.caption("Describe a topic, pick a design, and get an editable PowerPoint presentation.")

st.session_state.setdefault("style", DEFAULT_STYLE)


# ----- API keys -----------------------------------------------------------------------------
# A key is taken from, in this order: the field in the sidebar (kept only in this browser
# session), the .env file, or the secrets of a hosted app (Streamlit Community Cloud).

def secret(name):
    """A value from .streamlit/secrets.toml or the hosting's secrets, or None if there are none."""
    try:
        return st.secrets.get(name)
    except Exception:          # no secrets file at all
        return None


server_gemini_key = config.GEMINI_API_KEY or secret("GEMINI_API_KEY")
server_unsplash_key = config.UNSPLASH_CLIENT_ID or secret("UNSPLASH_CLIENT_ID")

with st.sidebar:
    with st.expander("🔑 API keys", expanded=not server_gemini_key):
        typed_gemini_key = st.text_input(
            "Gemini API key", type="password",
            placeholder="Set on the server" if server_gemini_key else "Paste your key",
            help="Get one at https://aistudio.google.com/api-keys",
        ).strip()
        typed_unsplash_key = st.text_input(
            "Unsplash access key (optional)", type="password",
            placeholder="Set on the server" if server_unsplash_key else "Without it: no photos",
            help="Get one at https://unsplash.com/developers",
        ).strip()
        st.caption("Keys typed here stay only in this browser session and are not saved.")

gemini_key = typed_gemini_key or server_gemini_key
unsplash_key = typed_unsplash_key or server_unsplash_key

if not gemini_key:
    st.info(
        "🔑 **A Gemini API key is needed to generate presentations.** Get one at "
        "https://aistudio.google.com/api-keys and paste it into **API keys** in the sidebar, "
        "or put it into `GEMINI_API_KEY` in the `.env` file and restart the app. "
        "Until then you can explore the styles and themes below."
    )
elif not unsplash_key:
    st.info(
        "🖼️ No Unsplash key, so presentations will be generated without photos. "
        "Add one (https://unsplash.com/developers) under **API keys** in the sidebar or in `.env`."
    )


# ----- sidebar: what the presentation is about -----------------------------------------------

with st.sidebar:
    st.header("Content")
    with st.form("generation_form"):
        topic = st.text_input("Presentation topic", placeholder="The History of Space Exploration")
        uploaded_file = st.file_uploader("Source document (optional)", type=["txt", "pdf", "docx"])
        selected_tone = st.selectbox("Tone", options=list(TONE_PRESETS.keys()))
        selected_text_amount = st.selectbox(
            "Text amount per slide", options=list(TEXT_AMOUNT_PRESETS.keys()), index=2
        )
        additional_commentary = st.text_input(
            "Additional wishes (optional)", placeholder="Focus on the environmental impact"
        )
        num_slides = st.slider("Number of slides", min_value=2, max_value=15, value=6, step=1)
        speaker_notes = st.checkbox(
            "Write speaker notes", value=True,
            help="What to say on each slide. Saved in the notes of the PowerPoint file.",
        )
        submit_button = st.form_submit_button("🚀 Generate presentation", type="primary", width="stretch")
    st.caption("The design on the right can be changed at any time, even after generation.")


# ----- design: colours and style ------------------------------------------------------------

st.subheader("Design")
theme_column, _ = st.columns([1, 2])
with theme_column:
    selected_theme = st.selectbox("Colour theme", list(THEMES.keys()))
    show_swatches(THEMES[selected_theme])

st.markdown("**Style**")
for column, (style_key, style) in zip(st.columns(len(STYLES)), STYLES.items()):
    with column, st.container(border=True):
        # each card shows the real title slide of the example deck in this style and theme
        show_slide(sample_preview(style_key, selected_theme)[0])
        st.markdown(f"**{style.name}**")
        st.caption(style.description)
        is_selected = st.session_state["style"] == style_key
        st.button(
            "✓ Selected" if is_selected else "Select",
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
        st.warning(f"⚠️ {e} The document was ignored.")
    if len(doc_text) > MAX_DOC_CHARS:
        st.info(
            f"ℹ️ The document is long: only the first {MAX_DOC_CHARS:,} "
            f"of its {len(doc_text):,} characters were used."
        )

    if not gemini_key:
        st.warning("⚠️ Add a Gemini API key under **API keys** in the sidebar first.")
    elif not topic.strip() and not doc_text.strip():
        st.warning("⚠️ Please enter a topic or upload a document!")
    else:
        prompt = build_prompt(
            topic=topic,
            doc_text=doc_text,
            tone=selected_tone,
            text_amount=selected_text_amount,
            commentary=additional_commentary,
            num_slides=num_slides,
            speaker_notes=speaker_notes,
        )

        # Forget the previous presentation before making a new one
        for key in ("deck", "photos", "photo_warnings", "file_name", "pptx_bytes", "preview", "rendered_design"):
            st.session_state.pop(key, None)

        with st.status("Writing the content with Gemini…", expanded=False) as status:
            try:
                deck = generate_deck(prompt, max_slides=num_slides, api_key=gemini_key)
                status.update(label="Looking for photos on Unsplash…")
                photos, photo_warnings = fetch_photos(keywords_for(deck), client_id=unsplash_key)
                # The content and its photos are kept for the whole session;
                # the file itself is built from them in the block below.
                st.session_state["deck"] = deck
                st.session_state["photos"] = photos
                st.session_state["photo_warnings"] = photo_warnings
                st.session_state["file_name"] = safe_file_name(topic)
                st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1
                status.update(label="Content is ready", state="complete")
            except Exception as e:
                status.update(label="Generation failed", state="error")
                st.error(f"❌ An error occurred: {e}")


# ----- rendering: runs whenever the content or the design changed ---------------------------

# Whenever there is content and it was not drawn for the currently selected style and
# theme (a new generation, or the user picked another design), draw it again.
# No Gemini or Unsplash calls happen here, so switching designs is instant.
design = (selected_style, selected_theme)
if "deck" in st.session_state and st.session_state.get("rendered_design") != design:
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    try:
        st.session_state["pptx_bytes"] = build_pptx(
            deck, selected_style, selected_theme,
            images={key: photo.data for key, photo in photos.items()},
            credits={key: photo.credit for key, photo in photos.items()},
        )
        st.session_state["preview"] = build_preview(
            deck, selected_style, selected_theme,
            {key: photo.preview_url for key, photo in photos.items()},
        )
        st.session_state["rendered_design"] = design
    except Exception as e:
        st.session_state.pop("pptx_bytes", None)
        st.error(f"❌ Could not build the presentation: {e}")


# ----- result -------------------------------------------------------------------------------

if "pptx_bytes" in st.session_state:
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    title_column, button_column = st.columns([2, 1], vertical_alignment="bottom")
    with title_column:
        st.subheader(deck.title)
        st.caption(
            f"{len(deck.slides) + 1} slides · {STYLES[selected_style].name} style · {selected_theme} theme. "
            "Pick another style or theme above to redraw it with the same content."
        )
    with button_column:
        st.download_button(
            label="📥 Download .pptx",
            data=st.session_state["pptx_bytes"],
            file_name=st.session_state["file_name"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
            width="stretch",
        )
    for warning in st.session_state.get("photo_warnings", []):
        st.warning(f"⚠️ {warning}")

    show_slides(st.session_state["preview"])
    st.caption(
        "The preview is drawn by the browser and may differ slightly from PowerPoint "
        "(for example if a font is not installed on this computer)."
    )
    edit_section(deck)

    slides_with_notes = [("Title slide", deck.notes)] + [(slide.title, slide.notes) for slide in deck.slides]
    if any(notes for _, notes in slides_with_notes):
        with st.expander("🎤 Speaker notes"):
            for number, (title, notes) in enumerate(slides_with_notes, 1):
                if notes:
                    st.markdown(f"**{number}. {title}**")
                    st.write(notes)
            st.caption("The notes are also saved in the .pptx file: PowerPoint shows them in presenter view.")
    if photos:
        with st.expander("📷 Photo credits"):
            for keyword, photo in photos.items():
                st.markdown(
                    f"- *{keyword}*: photo by [{photo.author}]({photo.author_url}) on "
                    "[Unsplash](https://unsplash.com/?utm_source=ai_pptx_generator&utm_medium=referral)"
                )
            st.caption("The same credits are saved in the speaker notes of the slides.")
    with st.expander("🔍 Generated content (JSON)"):
        st.json(deck.model_dump(exclude_none=True))
else:
    st.subheader("Example")
    st.caption(
        "This is a built-in sample presentation drawn in the selected style and theme. "
        "Fill in the form on the left to generate your own."
    )
    show_slides(sample_preview(selected_style, selected_theme))
