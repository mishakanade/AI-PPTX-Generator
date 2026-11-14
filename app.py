"""Streamlit interface. All generation logic lives in the generator/ package."""
import streamlit as st

from generator.content.documents import extract_text_from_file
from generator.content.llm import generate_structure_with_retry, parse_slides_json
from generator.content.presets import TEXT_AMOUNT_PRESETS, TONE_PRESETS
from generator.content.prompt import build_prompt
from generator.design.themes import THEMES
from generator.render.pptx_builder import create_pptx_in_memory


def render_theme_preview(theme_colors):
    """Show a small card painted in the theme's colours."""
    bg_color = theme_colors['bg']
    title_color = theme_colors['title']
    accent_color = theme_colors['accent']
    bg = f"rgb({bg_color[0]}, {bg_color[1]}, {bg_color[2]})"
    title = f"rgb({title_color[0]}, {title_color[1]}, {title_color[2]})"
    accent = f"rgb({accent_color[0]}, {accent_color[1]}, {accent_color[2]})"
    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin-top: 5px;
        ">
            <div style="color: {title}; font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                Slide Title
            </div>
            <div style="color: {accent}; font-size: 12px; font-weight: 600;">
                — Subtitle / Accent
            </div>
            <div style="background-color: {accent}; height: 3px; width: 30px; border-radius: 2px; margin-top: 6px;"></div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.set_page_config(page_title="AI PPTX Generator Pro", page_icon="📊", layout="wide")
st.title("📊 AI PPTX Generator Pro")
st.caption("Presentation generator with auto-design and illustration selection from Unsplash")


col_main, col_settings = st.columns([2, 1], gap="medium")


with col_settings:
    st.markdown("### 🎨 Design Settings")
    selected_theme = st.selectbox("Design theme:", list(THEMES.keys()))
    st.caption("Theme preview:")
    render_theme_preview(THEMES[selected_theme])

    st.markdown("### 🎯 Presentation Content")
    with st.form("generation_form"):
        topic = st.text_input("Presentation topic:", placeholder="For example: The History of Space Exploration")
        uploaded_file = st.file_uploader(
            "Attach a document (TXT, PDF, DOCX):",
            type=["txt", "pdf", "docx"]
        )
        selected_tone = st.selectbox(
            "Presentation style and tone:",
            options=list(TONE_PRESETS.keys())
        )
        selected_text_amount = st.selectbox(
            "Text amount per slide:",
            options=list(TEXT_AMOUNT_PRESETS.keys())
        )
        additional_commentary = st.text_input("Additional commentary (optional):", placeholder="For example: Focus on the environmental impact of Space exploration")
        num_slides = st.slider("Number of slides:", min_value=2, max_value=10, value=4, step=1)

        st.write("")
        submit_button = st.form_submit_button("🚀 Generate Presentation", use_container_width=True)


if submit_button:
    doc_text = extract_text_from_file(uploaded_file)
    if not topic.strip() and not doc_text.strip():
        st.warning("⚠️ Please enter a topic or upload a document!")
    else:
        prompt = build_prompt(
            topic=topic,
            doc_text=doc_text,
            tone=selected_tone,
            text_amount=selected_text_amount,
            commentary=additional_commentary,
            num_slides=num_slides,
        )

        for key in ("pptx_bytes", "slides_data", "file_name"):
            st.session_state.pop(key, None)

        with st.spinner("⏳ Gemini is creating the content and downloading images from Unsplash..."):
            try:
                raw_text = generate_structure_with_retry(prompt)
                slides_data = parse_slides_json(raw_text)
                pptx_file = create_pptx_in_memory(slides_data, selected_theme)
                st.session_state["pptx_bytes"] = pptx_file.getvalue()
                st.session_state["slides_data"] = slides_data
                st.session_state["file_name"] = f"{topic if topic else 'presentation'}.pptx"
            except Exception as e:
                st.error(f"❌ An error occurred: {e}")


with col_main:
    if "pptx_bytes" in st.session_state:
        slides_data = st.session_state["slides_data"]
        st.success(f"✅ Presentation with {len(slides_data.get('slides', []))} slides is ready!")
        st.download_button(
            label="📥 Download the finished .pptx file",
            data=st.session_state["pptx_bytes"],
            file_name=st.session_state["file_name"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True
        )
        with st.expander("🔍 View generated JSON"):
            st.json(slides_data)
