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

st.set_page_config(page_title="AI PPTX Generator", page_icon="📊", layout="wide")
st.session_state.setdefault("lang", browser_language())
st.session_state.setdefault("style", DEFAULT_STYLE)

# sidebar: language, which AI writes the content, what the presentation is about
sidebar.language_switch()
st.title("📊 AI PPTX Generator")
st.caption(tr("page_caption"))
conn = sidebar.connection()
form = sidebar.content_form()

# how the slides look
look = design.design_section()
st.divider()

# writing the content: on submit, then the copy & paste panel and the plan when they are waiting
if form.submitted:
    generation.handle_submit(form, conn)
generation.chat_panel(conn)
generation.outline_panel(conn)

# the file is drawn whenever the content or the design changed, then shown
result.render(look)
if "pptx_bytes" in st.session_state:
    result.result_section(look, conn)
else:
    result.example_section(look)
