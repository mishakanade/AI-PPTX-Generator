"""AI PPTX Generator: the Streamlit page. Run it with:  python -m streamlit run app.py

Streamlit reruns this file from top to bottom on every click. Everything that must survive
between reruns (the presentation, its photos, the chosen style) is kept in st.session_state.

This file only puts the page together, part by part; each part lives in interface/ and the
generation itself in generator/. Every text comes from ui_text.py, in the chosen language.
"""
import streamlit as st

from generator.design.styles import DEFAULT_STYLE
from interface import design, generation, result, sidebar
from interface.common import browser_language, tr

# the sidebar holds the form, so it starts open: on a phone it would otherwise be hidden
st.set_page_config(page_title="AI PPTX Generator", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
# Streamlit leaves a lot of empty space above the page title; half of it is enough
st.html("<style>[data-testid='stMainBlockContainer'] { padding-top: 2.5rem; }</style>")
st.session_state.setdefault("lang", browser_language())
st.session_state.setdefault("style", DEFAULT_STYLE)

# sidebar: language, which AI writes the content, what the presentation is about
sidebar.language_switch()
st.title("📊 AI PPTX Generator")
st.caption(tr("page_caption"))
conn = sidebar.connection()
form = sidebar.content_form()

# the answer to "Generate" first, where it is seen: progress, the copy & paste panel, the plan
if form.submitted:
    generation.handle_submit(form, conn)
generation.chat_panel(conn)
generation.outline_panel(conn)

if "deck" in st.session_state:
    # a presentation exists: its downloads on top, slides, design, quality, editing in tabs
    result.workspace(conn)
else:
    # nothing yet: choose the design and see it on the built-in example
    look = design.design_section()
    st.divider()
    result.example_section(look)
