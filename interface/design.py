"""The design section: colour theme (or custom colours), transition, logo and style cards."""
import hashlib
from dataclasses import dataclass

import streamlit as st

import ui_text
from generator.design.colors import from_hex, readable_theme, to_hex
from generator.design.styles import STYLES
from generator.design.themes import THEMES
from generator.images.pictures import fit_for_slides
from generator.render.builder import theme_colors
from generator.render.logo import logo_aspect
from interface.common import (
    CUSTOM_THEME,
    current_language,
    sample_preview,
    show_slide,
    show_swatches,
    tr,
    tr_in,
)


@dataclass
class Design:
    """Everything that decides how the slides look, but not what they say."""
    style: str
    theme: object                 # a theme name, or a colour dict for custom colours
    theme_label: str              # how the theme is named in the result caption
    transition: str | None     # None, "fade", "push" or "wipe"
    logo: bytes | None

    @property
    def key(self):
        """Changes whenever the file must be drawn again."""
        logo_id = hashlib.sha1(self.logo).hexdigest() if self.logo else None
        return (self.style, self.theme, self.transition, logo_id)


def design_section():
    lang = current_language()
    st.subheader(tr("design"))
    theme_column, transition_column, _ = st.columns([1, 1, 1])
    with theme_column:
        theme, theme_label = _theme_choice()
    with transition_column:
        choice = st.selectbox(
            tr("transition"), ["none", "fade", "push", "wipe"], key="transition", help=tr("transition_help"),
            format_func=lambda name, t=tr_in(lang): t(f"transition_{name}"),
        )
        logo = _logo_choice()

    st.markdown(f"**{tr('style')}**")
    for column, (style_key, style) in zip(st.columns(len(STYLES)), STYLES.items()):
        with column, st.container(border=True):
            # each card shows the real title slide of the example deck in this style and theme
            show_slide(sample_preview(style_key, theme, lang)[0])
            st.markdown(f"**{style.name}**")
            st.caption(ui_text.pick(ui_text.STYLE_DESCRIPTIONS, lang, style_key, default=style.description))
            is_selected = st.session_state["style"] == style_key
            st.button(
                tr("selected") if is_selected else tr("select"),
                key=f"style_{style_key}",
                type="primary" if is_selected else "secondary",
                on_click=_select_style, args=(style_key,),
                width="stretch",
            )
    return Design(style=st.session_state["style"], theme=theme, theme_label=theme_label,
                  transition=None if choice == "none" else choice, logo=logo)


def _theme_choice():
    """A built-in theme, or four colour pickers. Returns (theme, its label for the caption)."""
    choice = st.selectbox(
        tr("colour_theme"), list(THEMES.keys()) + [CUSTOM_THEME], key="theme",
        format_func=lambda name, label=tr("custom_colours"): label if name == CUSTOM_THEME else name,
    )
    if choice == CUSTOM_THEME:
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
        theme, changed = readable_theme(**picked)
        if changed:
            st.caption(tr("adjusted", names=", ".join(labels[name].lower() for name in changed)))
        label = tr("theme_custom")
    else:
        theme, label = choice, tr("theme_named", name=choice)
    show_swatches(theme_colors(theme))
    return theme, label


def _logo_choice():
    """The logo lives in the session (not only in the uploader), so that an opened project can set it."""
    logo = st.session_state.get("logo")
    if logo:
        picture, button = st.columns([1, 1], vertical_alignment="center")
        picture.image(logo, width=110)
        button.button(tr("logo_remove"), key="logo_remove", on_click=_remove_logo)
    else:
        st.file_uploader(tr("logo"), type=["png", "jpg", "jpeg", "webp"], key="logo_file", on_change=_take_logo,
                         help=tr("logo_help"))
    message = st.session_state.pop("logo_message", None)
    if message:
        st.warning(message)
    return logo


LOGO_SIDE = 1200   # pixels; plenty for a logo in a corner, even on a large screen


def _select_style(style_key):
    st.session_state["style"] = style_key


def _take_logo():
    """Called when a logo file is chosen: keep it in the session if it is a picture."""
    uploaded = st.session_state.get("logo_file")
    if not uploaded:
        return
    try:
        logo = fit_for_slides(uploaded.getvalue(), max_side=LOGO_SIDE)   # a logo needs few pixels
        logo_aspect(logo)
    except ValueError:
        st.session_state["logo_message"] = tr("logo_not_image")
        return
    st.session_state["logo"] = logo


def _remove_logo():
    st.session_state.pop("logo", None)
