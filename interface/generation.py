"""Writing the content: through an AI API, by copy & paste with any AI chat, and the plan-first step.

The generation functions are called through their modules (llm.generate_deck,
unsplash.fetch_photos) so that the tests can replace them with fakes.
"""
import streamlit as st

import ui_text
from generator.content import llm
from generator.content.data import DataError, bind_data_charts, chart_options, describe_for_prompt, read_tables
from generator.content.documents import DocumentReadError, extract_text_from_file
from generator.content.prompt import MAX_DOC_CHARS, build_outline_prompt, build_prompt, build_review_prompt
from generator.content.quality import check_deck, describe_for_model
from generator.content.schema import SLIDE_TYPE_GUIDE, ContentError, Outline, OutlineSlide, parse_deck, parse_outline
from generator.content.storytelling import DEFAULT_GOAL
from generator.images import unsplash
from interface.common import current_language, forget_presentation, safe_file_name, show_error, tr


def bind(deck):
    """Put the user's real numbers into every chart slide that names a prepared chart.

    Done last, right before a deck is kept, so that whatever the model did to the numbers
    on the way (writing, the editor's pass, a fix), the charts show the user's data.
    """
    data = st.session_state.get("data")
    return bind_data_charts(deck, data["options"]) if data else bind_data_charts(deck, [])


def data_text():
    data = st.session_state.get("data")
    return data["text"] if data else None


def load_data(form):
    """Read the uploaded table, prepare the chart menu and keep both in the session."""
    st.session_state.pop("data", None)
    if not form.data_file:
        return
    try:
        tables = read_tables(form.data_file.name, form.data_file.getvalue())
    except DataError as e:
        st.warning(tr("data_error", reason=e))
        return
    options = chart_options(tables)
    st.session_state["data"] = {"text": describe_for_prompt(tables, options), "options": options}
    st.info(tr("data_loaded", tables=len(tables), charts=len(options)))


def store_deck(deck, topic, settings, conn):
    """Keep a freshly written deck and its photos in the session; the file is drawn later."""
    deck = bind(deck)
    photos, photo_warnings = unsplash.fetch_photos(unsplash.keywords_for(deck), client_id=conn.unsplash_key)
    st.session_state["deck"] = deck
    st.session_state["photos"] = photos
    st.session_state["photo_warnings"] = photo_warnings
    st.session_state["file_name"] = safe_file_name(topic)
    st.session_state["settings"] = settings
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1


def brief(settings):
    """Purpose, audience and talk length from the settings (older projects may not have them)."""
    return {"goal": settings.get("goal") or DEFAULT_GOAL, "audience": settings.get("audience") or ""}


def review(deck, settings, conn):
    """The editor's pass: fix what the automatic check found. Returns the better version."""
    deck = bind(deck)          # the check and the editor see the real chart numbers
    issues = check_deck(deck, settings["text_amount"], settings["speaker_notes"])
    if not issues:
        return deck
    prompt = build_review_prompt(deck, describe_for_model(issues), settings["tone"], settings["text_amount"],
                                 settings["speaker_notes"], **brief(settings))
    return llm.review_deck(deck, prompt, settings["text_amount"], settings["speaker_notes"],
                           api_key=conn.ai_key, provider=conn.provider, model=conn.ai_model)


def write_deck(prompt, num_slides, topic, settings, conn):
    """Ask the AI API for the slides and store them, with a status box. Returns True on success."""
    with st.status(tr("status_writing", provider=conn.name), expanded=False) as status:
        try:
            deck = llm.generate_deck(prompt, max_slides=num_slides, api_key=conn.ai_key,
                                     provider=conn.provider, model=conn.ai_model)
            if settings.get("auto_review"):
                status.update(label=tr("status_reviewing", provider=conn.name))
                deck = review(deck, settings, conn)
            status.update(label=tr("status_photos"))
            store_deck(deck, topic, settings, conn)
            status.update(label=tr("status_done"), state="complete")
            return True
        except Exception as e:
            status.update(label=tr("status_failed"), state="error")
            show_error(e, conn)
            return False


def read_long_document(doc_text, topic, conn):
    """A document too long for one request is read part by part; the presentation is then
    written from the digest of all parts instead of from the first pages only."""
    with st.status(tr("status_digest", number=1, total="…"), expanded=False) as status:
        try:
            digest, used, total = llm.digest_document(
                doc_text, topic, api_key=conn.ai_key, provider=conn.provider, model=conn.ai_model,
                progress=lambda number, count: status.update(label=tr("status_digest", number=number, total=count)),
            )
        except Exception as e:
            status.update(label=tr("status_failed"), state="error")
            show_error(e, conn)
            return None
        status.update(label=tr("status_done"), state="complete")
    st.info(tr("doc_digested", parts=used) if used == total else tr("doc_digested_partly", parts=used, total=total))
    return digest


# After "Generate" the answer (a warning, the progress, the result) appears below the design
# section, often out of sight. This scrolls to it; and on a phone, where the sidebar lies over
# the page, it first closes the sidebar. On a computer, where the sidebar sits beside the page,
# the sidebar stays as it is.
SHOW_THE_ANSWER = """<script>
const root = window.parent.document.querySelector('[data-testid="stSidebar"]') ? window.parent.document : document;
const sidebar = root.querySelector('[data-testid="stSidebar"]');
if (sidebar && sidebar.getBoundingClientRect().width > window.innerWidth * 0.6) {
  root.querySelector('[data-testid="stSidebarCollapseButton"] button')?.click();
}
setTimeout(() => {
  const answer = root.querySelector('.st-key-answer');
  if (answer) {
    answer.style.scrollMarginTop = '80px';         // room for Streamlit's bar at the top
    answer.scrollIntoView({behavior: 'smooth', block: 'start'});
  }
}, 400);
</script>"""


def handle_submit(form, conn):
    """Runs once when the content form is submitted."""
    with st.container(key="answer"):              # the place SHOW_THE_ANSWER scrolls to
        st.html(SHOW_THE_ANSWER, unsafe_allow_javascript=True)
    doc_text = ""
    try:
        doc_text = extract_text_from_file(form.uploaded_file)
    except DocumentReadError as e:
        st.warning(tr("doc_ignored", reason=tr(f"doc_{e.reason}", name=e.file_name)))
    if conn.info and not conn.ai_key:
        st.warning(tr("add_key_first", provider=conn.info["name"]))
        return
    if not form.topic.strip() and not doc_text.strip():
        st.warning(tr("need_topic"))
        return
    if len(doc_text) > MAX_DOC_CHARS:
        if conn.is_chat:
            st.info(tr("doc_long", used=MAX_DOC_CHARS, total=len(doc_text)))
        else:
            doc_text = read_long_document(doc_text, form.topic, conn)
            if doc_text is None:
                return

    forget_presentation()          # the previous presentation is replaced by the new one
    load_data(form)
    plan_request = {"topic": form.topic, "doc_text": doc_text, "commentary": form.commentary,
                    "settings": form.settings}

    if form.outline_first:
        outline_prompt = build_outline_prompt(form.topic, doc_text, form.tone, form.commentary, form.num_slides,
                                              for_chat=conn.is_chat, data_text=data_text(), **brief(form.settings))
        if conn.is_chat:
            st.session_state["chat_request"] = {"kind": "outline", "prompt": outline_prompt, **plan_request}
            return
        with st.status(tr("status_planning", provider=conn.name), expanded=False) as status:
            try:
                show_outline(llm.generate_outline(outline_prompt, api_key=conn.ai_key, provider=conn.provider,
                                                  model=conn.ai_model), plan_request)
                status.update(label=tr("status_plan_done"), state="complete")
            except Exception as e:
                status.update(label=tr("status_failed"), state="error")
                show_error(e, conn)
        return

    prompt = build_prompt(topic=form.topic, doc_text=doc_text, tone=form.tone, text_amount=form.text_amount,
                          commentary=form.commentary, num_slides=form.num_slides,
                          speaker_notes=form.speaker_notes, for_chat=conn.is_chat,
                          minutes=form.minutes or None, data_text=data_text(), **brief(form.settings))
    if conn.is_chat:
        # copy & paste: the request is shown by chat_panel(); the deck is built when the answer comes back
        st.session_state["chat_request"] = {"kind": "deck", "prompt": prompt, "topic": form.topic,
                                            "num_slides": form.num_slides, "settings": form.settings}
    else:
        write_deck(prompt, form.num_slides, form.topic, form.settings, conn)


def chat_panel(conn):
    """Copy & paste mode: show the request for the chat and read the answer pasted back."""
    request = st.session_state.get("chat_request")
    if not request or "deck" in st.session_state:
        return
    st.subheader(tr("chat_header"))
    st.markdown(tr("chat_steps"))
    st.code(request["prompt"], language=None, wrap_lines=True, height=300)
    kind = request.get("kind", "deck")        # the plan, or the slides themselves
    pasted = st.text_area(tr("chat_answer"), placeholder=tr("chat_answer_placeholder"), height=200,
                          key=f"chat_answer_{kind}")
    answer_file = st.file_uploader(tr("chat_file"), type=["json", "txt", "md"], key=f"chat_file_{kind}")
    if not st.button(tr("chat_build") if kind == "deck" else tr("outline_header"), type="primary",
                     key=f"chat_build_{kind}"):
        return
    answer = answer_file.getvalue().decode("utf-8", errors="ignore") if answer_file else pasted
    if not answer.strip():
        st.warning(tr("chat_need_answer"))
        return
    try:
        parsed = parse_deck(answer) if kind == "deck" else parse_outline(answer)
    except ContentError as e:
        st.error(tr("chat_bad_answer", error=e))
        return
    st.session_state.pop("chat_request", None)
    if kind == "outline":
        show_outline(parsed, {k: request[k] for k in ("topic", "doc_text", "commentary", "settings")})
    else:
        parsed.slides = llm.trim_slides(parsed.slides, request["num_slides"])
        with st.spinner(tr("status_photos")):
            store_deck(parsed, request["topic"], request["settings"], conn)
    st.rerun()


# ----- plan first -------------------------------------------------------------------------------

def show_outline(outline, request):
    """Keep a proposed plan in the session; outline_panel() shows it."""
    st.session_state["outline"] = outline
    st.session_state["outline_request"] = request
    st.session_state["outline_version"] = st.session_state.get("outline_version", 0) + 1


def outline_panel(conn):
    """The proposed plan as an editable form; on submit, the slides are written by it."""
    if "outline" not in st.session_state or "deck" in st.session_state or st.session_state.get("chat_request"):
        return
    outline, request = st.session_state["outline"], st.session_state["outline_request"]
    lang = current_language()
    version = st.session_state.get("outline_version", 0)
    types = list(SLIDE_TYPE_GUIDE)
    st.subheader(tr("outline_header"))
    st.caption(tr("outline_caption"))
    with st.form(f"outline_form_{version}", border=False):
        title = st.text_input(tr("deck_title"), outline.title, key=f"o{version}_title")
        subtitle = st.text_input(tr("deck_subtitle"), outline.subtitle, key=f"o{version}_subtitle")
        rows = list(outline.slides) + [None, None]          # two empty rows to add slides
        edited = []
        for i, slide in enumerate(rows):
            label = "visible" if i == 0 else "collapsed"     # column labels only on the first row
            number, kind, name, focus, delete = st.columns([0.4, 2, 4, 5, 1.4], vertical_alignment="bottom")
            number.markdown(f"**{i + 2}**")
            slide_type = kind.selectbox(
                tr("outline_type"), types, index=types.index(slide.type) if slide else 0,
                key=f"o{version}_{i}_type", label_visibility=label,
                format_func=lambda key: ui_text.pick(ui_text.SLIDE_TYPES, lang, key),
            )
            slide_title = name.text_input(
                tr("outline_title"), slide.title if slide else "", key=f"o{version}_{i}_title",
                placeholder=tr("outline_new") if slide is None else "", label_visibility=label,
            )
            slide_focus = focus.text_input(
                tr("outline_focus"), (slide.focus or "") if slide else "", key=f"o{version}_{i}_focus",
                label_visibility=label,
            )
            removed = delete.checkbox(tr("outline_delete"), key=f"o{version}_{i}_delete", label_visibility=label)
            if slide_title.strip() and not removed:
                edited.append(OutlineSlide(type=slide_type, title=slide_title.strip(),
                                           focus=slide_focus.strip() or None))
        write = st.form_submit_button(tr("outline_write"), type="primary", key=f"outline_write_{version}")
    if not write:
        return
    if not edited:
        st.warning(tr("outline_empty"))
        return

    approved = Outline(title=title.strip() or outline.title, subtitle=subtitle.strip(), slides=edited)
    settings = request["settings"]
    prompt = build_prompt(
        topic=request["topic"], doc_text=request["doc_text"], tone=settings["tone"],
        text_amount=settings["text_amount"], commentary=request["commentary"], num_slides=len(edited),
        speaker_notes=settings["speaker_notes"], for_chat=conn.is_chat, outline=approved,
        minutes=settings.get("minutes"), data_text=data_text(), **brief(settings),
    )
    if conn.is_chat:
        st.session_state["chat_request"] = {"kind": "deck", "prompt": prompt, "topic": request["topic"],
                                            "num_slides": len(edited), "settings": settings}
    elif not write_deck(prompt, len(edited), request["topic"], settings, conn):
        return
    st.session_state.pop("outline", None)
    st.rerun()
