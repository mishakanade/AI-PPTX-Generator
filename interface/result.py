"""Drawing the file and showing the result: download, preview, editing, photos, notes, credits."""
import hashlib
import uuid

import streamlit as st

import ui_text
from generator import export
from generator.content import llm
from generator.content.editing import apply_edits, slide_to_text
from generator.content.prompt import build_review_prompt, build_slide_prompt
from generator.content.quality import check_deck, describe_for_model, score
from generator.content.schema import ContentError, parse_deck, parse_slide
from generator.design.styles import STYLES
from generator.images import unsplash
from generator.project import save_project
from generator.render.builder import build_pptx, build_preview
from interface import generation
from interface.common import (
    UNSPLASH_LINK, current_language, current_settings, plain, sample_preview, show_error, show_slides, tr,
)


def render(design):
    """Draw the file and the preview whenever the content or the design changed.

    No AI or Unsplash calls happen here, so switching designs is instant.
    """
    if "deck" not in st.session_state or st.session_state.get("rendered_design") == design.key:
        return
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    try:
        st.session_state["pptx_bytes"] = build_pptx(
            deck, design.style, design.theme,
            images={key: photo.data for key, photo in photos.items()},
            credits={key: photo.credit for key, photo in photos.items() if photo.credit},
            transition=design.transition,
            logo=design.logo,
        )
        st.session_state["preview"] = build_preview(
            deck, design.style, design.theme,
            {key: photo.preview_url for key, photo in photos.items()},
            logo=design.logo,
        )
        st.session_state["rendered_design"] = design.key
    except Exception as e:
        st.session_state.pop("pptx_bytes", None)
        st.error(tr("build_error", error=e))


def example_section(design):
    """Before the first generation: the built-in example deck in the chosen design."""
    st.subheader(tr("example"))
    st.caption(tr("example_caption"))
    show_slides(sample_preview(design.style, design.theme, current_language()))


def result_section(design, conn):
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    title_column, button_column = st.columns([2, 1], vertical_alignment="bottom")
    with title_column:
        st.subheader(plain(deck.title))
        st.caption(tr("result_caption", count=len(deck.slides) + 1, style=STYLES[design.style].name,
                      theme=design.theme_label))
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
            data=save_project(deck, photos, design.style, design.theme, st.session_state.get("settings"),
                              design.transition, design.logo),
            file_name=st.session_state["file_name"].removesuffix(".pptx") + ".project.json",
            mime="application/json",
            width="stretch",
            key="save_project",
            help=tr("save_project_help"),
        )
        _pdf_buttons()
    for warning in st.session_state.get("photo_warnings", []):
        st.warning(f"⚠️ {tr(warning)}")

    show_slides(st.session_state["preview"])
    st.caption(tr("preview_note"))
    _quality_section(deck, conn)
    _edit_section(deck)
    _photos_section(deck, photos, conn)
    _regenerate_section(deck, conn)
    _notes_and_credits(deck, photos)


def _pdf_buttons():
    """PDF on request, only where LibreOffice is installed. A PDF made for an older version of
    the file (before a design change or an edit) is not offered any more."""
    if not export.find_soffice():
        return
    current = hashlib.sha1(st.session_state["pptx_bytes"]).hexdigest()
    made = st.session_state.get("pdf")
    if made and made[0] == current:
        st.download_button(tr("download_pdf"), data=made[1], mime="application/pdf", width="stretch",
                           file_name=st.session_state["file_name"].removesuffix(".pptx") + ".pdf", key="download_pdf")
        return
    if st.button(tr("make_pdf"), key="make_pdf", help=tr("make_pdf_help"), width="stretch"):
        with st.spinner(tr("pdf_working")):
            try:
                st.session_state["pdf"] = (current, export.to_pdf(st.session_state["pptx_bytes"]))
            except export.ExportError as e:
                st.error(tr("pdf_error", error=e))
                return
        st.rerun()


# ----- the quality check ----------------------------------------------------------------------

def _issue_text(issue):
    number = {"n": issue.slide + 2} if issue.slide is not None else {}
    values = dict(issue.values)
    if "type" in values:                     # the slide type by its name in the interface language
        values["type"] = ui_text.pick(ui_text.SLIDE_TYPES, current_language(), values["type"])
    return tr(f"q_{issue.code}", **number, **values)


def _replace_deck(deck):
    st.session_state["deck"] = generation.bind(deck)
    st.session_state.pop("rendered_design", None)    # forces render() to draw again
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1


def _quality_section(deck, conn):
    """What the app's own checks find in the slides, and a way to let the AI fix it."""
    settings = current_settings()
    issues = check_deck(deck, settings["text_amount"], settings["speaker_notes"])
    with st.expander(tr("quality_header", score=score(issues))):
        message = st.session_state.pop("fix_message", None)
        if message:
            st.info(message)
        if not issues:
            st.success(tr("quality_clean"))
            return
        st.caption(tr("quality_caption"))
        st.markdown("\n".join("- " + plain(_issue_text(issue)) for issue in issues))
        if conn.is_chat:
            _fix_by_chat(deck, issues, settings)
        elif st.button(tr("fix_ai"), key="fix_ai", disabled=not conn.ai_key):
            with st.spinner(tr("fix_working", provider=conn.name)):
                try:
                    fixed = generation.review(deck, settings, conn)
                except Exception as e:
                    show_error(e, conn)
                    return
            if fixed is deck:
                st.session_state["fix_message"] = tr("fix_not_better")
            else:
                _replace_deck(fixed)
            st.rerun()


def _fix_by_chat(deck, issues, settings):
    """Copy & paste: the editing request for the chat, and the edited version pasted back."""
    version = st.session_state.get("edit_version", 0)
    if st.button(tr("fix_chat_show"), key="fix_chat_show"):
        st.session_state["fix_chat_version"] = version
    if st.session_state.get("fix_chat_version") != version:
        return
    prompt = build_review_prompt(deck, describe_for_model(issues), settings["tone"], settings["text_amount"],
                                 settings["speaker_notes"], for_chat=True, **generation.brief(settings))
    st.code(prompt, language=None, wrap_lines=True, height=220)
    answer = st.text_area(tr("chat_answer"), placeholder=tr("chat_answer_placeholder"), key=f"fix_chat_answer_{version}")
    if not st.button(tr("fix_chat_apply"), key="fix_chat_apply"):
        return
    if not answer.strip():
        st.warning(tr("chat_need_answer"))
        return
    try:
        fixed = parse_deck(answer)
    except ContentError as e:
        st.error(tr("chat_bad_answer", error=e))
        return
    st.session_state.pop("fix_chat_version", None)
    _replace_deck(fixed)
    st.rerun()


# ----- editing the text -------------------------------------------------------------------------

def _edit_section(deck):
    """A form to change the text of the slides or delete slides, then redraw without the AI."""
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
        st.session_state.pop("rendered_design", None)    # forces render() to draw again
        st.session_state["edit_version"] = version + 1
        st.rerun()


# ----- one slide rewritten by the AI ------------------------------------------------------------

def _regenerate_section(deck, conn):
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
        settings = current_settings()
        prompt = build_slide_prompt(deck, index, wish, settings["tone"], settings["text_amount"],
                                    settings["speaker_notes"], for_chat=conn.is_chat,
                                    data_text=generation.data_text(), **generation.brief(settings))
        slide = _slide_by_chat(prompt, version, index) if conn.is_chat else _slide_by_api(prompt, conn)
    if slide is None:
        return

    photos = st.session_state["photos"]
    if slide.type in ("bullets", "image") and slide.image_keyword and slide.image_keyword not in photos:
        found, _ = unsplash.fetch_photos([slide.image_keyword], client_id=conn.unsplash_key)
        photos.update(found)
    slides = list(deck.slides)
    slides[index] = slide
    st.session_state["deck"] = generation.bind(deck.model_copy(update={"slides": slides}))
    st.session_state.pop("rendered_design", None)    # forces render() to draw again
    st.session_state.pop("regen_chat_prompt", None)
    st.session_state["edit_version"] = version + 1     # the edit form shows the new text
    st.rerun()


def _slide_by_api(prompt, conn):
    if not st.button(tr("regen_button"), key="regen_button", disabled=not conn.ai_key):
        return None
    with st.spinner(tr("regen_working", provider=conn.name)):
        try:
            return llm.regenerate_slide(prompt, api_key=conn.ai_key, provider=conn.provider, model=conn.ai_model)
        except Exception as e:
            show_error(e, conn)
            return None


def _slide_by_chat(prompt, version, index):
    """Copy & paste: show the request, read the pasted answer."""
    if st.button(tr("regen_chat_show"), key="regen_chat_show"):
        st.session_state["regen_chat_prompt"] = (version, index, prompt)
    shown = st.session_state.get("regen_chat_prompt")
    if not shown or shown[0] != version or shown[1] != index:
        return None
    st.code(shown[2], language=None, wrap_lines=True, height=220)
    answer = st.text_area(tr("chat_answer"), placeholder=tr("chat_answer_placeholder"),
                          key=f"regen_chat_answer_{version}")
    if not st.button(tr("regen_chat_apply"), key="regen_chat_apply"):
        return None
    if not answer.strip():
        st.warning(tr("chat_need_answer"))
        return None
    try:
        return parse_slide(answer)
    except ContentError as e:
        st.error(tr("chat_bad_answer", error=e))
        return None


# ----- photos -----------------------------------------------------------------------------------

def _photos_section(deck, photos, conn):
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
                can_search = bool(keyword) and not keyword.startswith("upload-") and bool(conn.unsplash_key)
                buttons[0].button(tr("another_photo"), key=f"another_{version}_{i}", disabled=not can_search,
                                  on_click=_another_photo, args=(i, conn.unsplash_key), width="stretch")
                buttons[1].button(tr("remove_photo"), key=f"remove_{version}_{i}", disabled=not photo,
                                  on_click=_remove_photo, args=(i,), width="stretch")
                widget_key = f"own_{version}_{i}"
                st.file_uploader(tr("upload_photo"), type=["png", "jpg", "jpeg", "webp"], key=widget_key,
                                 on_change=_upload_photo, args=(i, widget_key), label_visibility="collapsed")


def _changed_photos(deck=None):
    """After a photo change: store the deck if it changed, and make the file be drawn again."""
    if deck is not None:
        st.session_state["deck"] = deck
    st.session_state.pop("rendered_design", None)
    st.session_state["edit_version"] = st.session_state.get("edit_version", 0) + 1


def _with_keyword(index, keyword):
    deck = st.session_state["deck"]
    slides = list(deck.slides)
    slides[index] = slides[index].model_copy(update={"image_keyword": keyword})
    return deck.model_copy(update={"slides": slides})


def _another_photo(index, unsplash_key):
    deck, photos = st.session_state["deck"], st.session_state["photos"]
    keyword = deck.slides[index].image_keyword
    used = {photo.photo_id for photo in photos.values() if photo.photo_id}
    photo, warnings = unsplash.fetch_another(keyword, used, client_id=unsplash_key)
    if photo:
        photos[keyword] = photo
        _changed_photos()
    else:
        st.session_state["photo_message"] = tr(warnings[0]) if warnings else tr("photo_none_found", keyword=keyword)


def _upload_photo(index, widget_key):
    uploaded = st.session_state.get(widget_key)
    if not uploaded:
        return
    try:
        photo = unsplash.own_photo(uploaded.getvalue())
    except ValueError:
        st.session_state["photo_message"] = tr("photo_not_image")
        return
    key = f"upload-{uuid.uuid4().hex[:8]}"     # own pictures get their own key: never searched on Unsplash
    st.session_state["photos"][key] = photo
    _changed_photos(_with_keyword(index, key))


def _remove_photo(index):
    _changed_photos(_with_keyword(index, None))


# ----- notes, credits, raw content --------------------------------------------------------------

def _notes_and_credits(deck, photos):
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
                st.markdown(tr("credit_line", keyword=plain(keyword), author=plain(photo.author),
                               url=photo.author_url, unsplash=UNSPLASH_LINK))
            st.caption(tr("credits_note"))
    with st.expander(tr("json_header")):
        st.json(deck.model_dump(exclude_none=True))
