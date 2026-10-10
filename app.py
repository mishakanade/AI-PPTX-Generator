import sys
import os
import json
import re
import time
import urllib.request
import urllib.parse
from io import BytesIO
import streamlit as st
from google import genai
from google.genai import types
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import pypdf
import random, httpx
from docx import Document
from dotenv import load_dotenv


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
UNSPLASH_CLIENT_ID = os.getenv("UNSPLASH_CLIENT_ID")

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash"]

from pptx.dml.color import RGBColor

THEMES = {
    # ---------- Original themes ----------
    "Corporate Blue": {
        "bg": RGBColor(245, 247, 250),
        "title": RGBColor(16, 44, 87),
        "text": RGBColor(53, 55, 64),
        "accent": RGBColor(53, 89, 224)
    },
    "Dark Modern": {
        "bg": RGBColor(24, 26, 32),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(200, 205, 215),
        "accent": RGBColor(0, 210, 180)
    },
    "Minimalist Light": {
        "bg": RGBColor(255, 255, 255),
        "title": RGBColor(20, 20, 20),
        "text": RGBColor(80, 80, 80),
        "accent": RGBColor(220, 50, 50)
    },
    "Eco Green": {
        "bg": RGBColor(242, 248, 244),
        "title": RGBColor(20, 60, 35),
        "text": RGBColor(50, 70, 60),
        "accent": RGBColor(46, 139, 87)
    },

    # ---------- Light themes ----------
    "Ocean Breeze": {
        "bg": RGBColor(240, 248, 252),
        "title": RGBColor(8, 60, 90),
        "text": RGBColor(45, 70, 85),
        "accent": RGBColor(0, 120, 160)
    },
    "Sunset Warm": {
        "bg": RGBColor(255, 246, 238),
        "title": RGBColor(120, 40, 20),
        "text": RGBColor(80, 55, 45),
        "accent": RGBColor(196, 70, 20)
    },
    "Lavender Dream": {
        "bg": RGBColor(247, 244, 252),
        "title": RGBColor(60, 40, 110),
        "text": RGBColor(75, 65, 95),
        "accent": RGBColor(120, 70, 195)
    },
    "Rose Quartz": {
        "bg": RGBColor(253, 244, 246),
        "title": RGBColor(110, 25, 55),
        "text": RGBColor(85, 60, 68),
        "accent": RGBColor(190, 40, 95)
    },
    "Desert Sand": {
        "bg": RGBColor(250, 245, 235),
        "title": RGBColor(92, 64, 30),
        "text": RGBColor(80, 68, 55),
        "accent": RGBColor(160, 98, 28)
    },
    "Mint Fresh": {
        "bg": RGBColor(240, 251, 247),
        "title": RGBColor(10, 80, 70),
        "text": RGBColor(45, 75, 70),
        "accent": RGBColor(0, 130, 105)
    },
    "Coffee House": {
        "bg": RGBColor(245, 238, 230),
        "title": RGBColor(62, 39, 25),
        "text": RGBColor(84, 66, 56),
        "accent": RGBColor(145, 80, 40)
    },
    "Arctic Frost": {
        "bg": RGBColor(238, 244, 250),
        "title": RGBColor(25, 45, 75),
        "text": RGBColor(60, 75, 95),
        "accent": RGBColor(40, 105, 180)
    },
    "Paper & Ink": {
        "bg": RGBColor(250, 248, 243),
        "title": RGBColor(30, 30, 35),
        "text": RGBColor(70, 70, 75),
        "accent": RGBColor(30, 90, 160)
    },
    "Sage Garden": {
        "bg": RGBColor(243, 246, 238),
        "title": RGBColor(55, 70, 45),
        "text": RGBColor(85, 100, 75),
        "accent": RGBColor(95, 125, 45)
    },
    "Teal & Coral": {
        "bg": RGBColor(244, 251, 251),
        "title": RGBColor(10, 70, 80),
        "text": RGBColor(55, 80, 85),
        "accent": RGBColor(215, 70, 60)
    },
    "Indigo Ink": {
        "bg": RGBColor(244, 245, 252),
        "title": RGBColor(30, 35, 110),
        "text": RGBColor(65, 70, 110),
        "accent": RGBColor(80, 70, 220)
    },
    "Burgundy Classic": {
        "bg": RGBColor(250, 244, 242),
        "title": RGBColor(95, 20, 35),
        "text": RGBColor(80, 60, 60),
        "accent": RGBColor(150, 30, 50)
    },
    "Retro Cream": {
        "bg": RGBColor(245, 235, 210),
        "title": RGBColor(60, 45, 30),
        "text": RGBColor(95, 80, 60),
        "accent": RGBColor(185, 60, 40)
    },
    "High Contrast": {
        "bg": RGBColor(255, 255, 255),
        "title": RGBColor(0, 0, 0),
        "text": RGBColor(30, 30, 30),
        "accent": RGBColor(0, 70, 200)
    },

    # ---------- Dark themes ----------
    "Midnight Purple": {
        "bg": RGBColor(22, 18, 40),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(205, 198, 230),
        "accent": RGBColor(170, 120, 255)
    },
    "Deep Ocean": {
        "bg": RGBColor(8, 25, 45),
        "title": RGBColor(235, 248, 255),
        "text": RGBColor(170, 200, 225),
        "accent": RGBColor(0, 190, 230)
    },
    "Forest Night": {
        "bg": RGBColor(16, 30, 24),
        "title": RGBColor(232, 248, 238),
        "text": RGBColor(175, 205, 188),
        "accent": RGBColor(120, 220, 130)
    },
    "Charcoal & Amber": {
        "bg": RGBColor(30, 30, 32),
        "title": RGBColor(255, 244, 225),
        "text": RGBColor(205, 200, 190),
        "accent": RGBColor(255, 170, 40)
    },
    "Crimson Noir": {
        "bg": RGBColor(20, 14, 16),
        "title": RGBColor(255, 240, 240),
        "text": RGBColor(210, 190, 194),
        "accent": RGBColor(255, 80, 90)
    },
    "Cyberpunk": {
        "bg": RGBColor(14, 10, 28),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(190, 200, 240),
        "accent": RGBColor(255, 45, 170)
    },
    "Graphite Blue": {
        "bg": RGBColor(28, 34, 44),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(180, 195, 215),
        "accent": RGBColor(90, 160, 255)
    },
    "Espresso Gold": {
        "bg": RGBColor(36, 26, 20),
        "title": RGBColor(250, 236, 200),
        "text": RGBColor(210, 195, 175),
        "accent": RGBColor(222, 170, 60)
    },
    "Terminal Green": {
        "bg": RGBColor(6, 14, 8),
        "title": RGBColor(190, 255, 200),
        "text": RGBColor(130, 210, 145),
        "accent": RGBColor(60, 255, 110)
    },
    "Royal Navy & Gold": {
        "bg": RGBColor(14, 26, 56),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(200, 210, 235),
        "accent": RGBColor(240, 190, 60)
    },
    "Plum Wine": {
        "bg": RGBColor(40, 16, 32),
        "title": RGBColor(255, 240, 248),
        "text": RGBColor(225, 195, 215),
        "accent": RGBColor(255, 120, 170)
    },
    "Pure Black": {
        "bg": RGBColor(0, 0, 0),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(190, 190, 190),
        "accent": RGBColor(255, 214, 0)
    },
    "Blueprint": {
        "bg": RGBColor(18, 52, 110),
        "title": RGBColor(255, 255, 255),
        "text": RGBColor(205, 225, 250),
        "accent": RGBColor(255, 220, 90)
    },
}

TONE_PRESETS = {
    "💼 Professional": (
        "TONE MANDATE [Professional]: Use formal corporate language, passive voice where appropriate, "
        "and data-driven framing. Focus heavily on key metrics, KPIs, risk factors, efficiency gains, "
        "and strategic business impact. Avoid exclamations or overly enthusiastic language."
    ),
    "🚀 Creative / Pitch Deck": (
        "TONE MANDATE [Creative/Pitch Deck]: Use punchy, high-energy, persuasive language. "
        "Structure content as a narrative arc: Call out a painful Problem, introduce a disruptive Solution, "
        "and highlight key Differentiators. Use active verbs, bold statements, and compelling storytelling."
    ),
    "📚 Educational / Academic": (
        "TONE MANDATE [Educational]: Use clear, explanatory language designed for learning. "
        "Break down complex terms with direct analogies, 'Key Takeaway' definitions, step-by-step logic, "
        "and concrete real-world examples."
    )
}

TEXT_AMOUNT_PRESETS = {
    "Paragraph-style": {
        "description": (
            "Write in flowing paragraphs. Each item in \"content\" is one short paragraph "
            "of 2-4 complete sentences with explanations and, where useful, examples. "
            "Prefer fewer, longer items."
        ),
        "max_words": 80,
        "examples": [
            ["A short paragraph of 2-4 full sentences that explains the main idea of the slide and backs it with a concrete detail.",
             "A second paragraph that develops the idea further or gives an example."],
            ["A single, slightly longer paragraph, used when the slide needs only one block of explanation."],
        ],
    },
    "Talking-Points-Style": {
        "description": (
            "Write short talking points that help a presenter improvise the speech: "
            "each item is a few words up to one short line (max ~10 words), focused on key ideas, "
            "facts and takeaways. Prefer more, shorter items."
        ),
        "max_words": 45,
        "examples": [
            ["Short key phrase", "Another key phrase", "Key number or fact", "Main takeaway"],
            ["Key phrase", "Key fact"],
        ],
    },
    "Balanced": {
        "description": (
            "Mix concise bullet points with short explanatory sentences: each slide combines "
            "a few short bullets with one or two explanatory sentences."
        ),
        "max_words": 60,
        "examples": [
            ["Concise bullet point", "Short bullet with a key fact",
             "One or two explanatory sentences that connect the points above."],
            ["Concise bullet point", "Another short bullet", "A third bullet",
             "One explanatory sentence."],
        ],
    },
}



@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=45_000))
client = get_gemini_client()


def fetch_image_bytes(keyword: str):
    """Load an image from Unsplash by keyword"""
    clean_keyword = urllib.parse.quote(keyword.strip())
    api_url = f"https://api.unsplash.com/search/photos?query={clean_keyword}&per_page=1&orientation=landscape&client_id={UNSPLASH_CLIENT_ID}"
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = data.get("results", [])
        if not results:
            return None
        img_url = results[0]["urls"]["regular"]
        img_req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(img_req, timeout=7) as img_resp:
            return BytesIO(img_resp.read())
    except Exception:
        return None

def extract_text_from_file(uploaded_file):
    """Read text from the uploaded file"""
    if uploaded_file is None:
        return ""
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    elif uploaded_file.name.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        except Exception:
            return ""
    return ""

def render_theme_preview(theme_name, theme_colors):
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

def create_pptx_in_memory(slides_data, theme_name):
    """Build the PPTX presentation in memory (BytesIO)"""
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    colors = THEMES.get(theme_name, THEMES["Corporate Blue"])
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = colors["bg"]
    txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.33), Inches(2.0))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(slides_data.get("title", "Presentation"))
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = colors["title"]
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = str(slides_data.get("subtitle", "Generated by AI"))
    p2.font.size = Pt(22)
    p2.font.color.rgb = colors["accent"]
    p2.alignment = PP_ALIGN.CENTER
    for slide_info in slides_data.get("slides", []):
        slide = prs.slides.add_slide(blank_layout)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = colors["bg"]
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.0))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = str(slide_info.get("title", "Slide"))
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = colors["title"]
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.5), Inches(5.0))
        tf_text = text_box.text_frame
        tf_text.word_wrap = True
        bullets = slide_info.get("content", [])
        for idx, bullet in enumerate(bullets):
            p = tf_text.paragraphs[0] if idx == 0 else tf_text.add_paragraph()
            p.text = "• " + str(bullet)
            p.font.size = Pt(18)
            p.font.color.rgb = colors["text"]
            p.space_after = Pt(14)
        img_keyword = slide_info.get("image_keyword")
        if img_keyword:
            img_bytes = fetch_image_bytes(img_keyword)
            if img_bytes:
                try:
                    slide.shapes.add_picture(img_bytes, Inches(7.8), Inches(1.8), width=Inches(4.8))
                except Exception:
                    pass
    output = BytesIO()
    prs.save(output)
    output.seek(0)
    return output

def generate_structure_with_retry(prompt, retries_per_model=2):
    last_err = None
    for model in MODELS:
        for attempt in range(retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                    ),
                )
                return response.text
            except Exception as e:
                last_err = e
                code = getattr(e, "code", None)
                if code not in (429, 500, 503, 504) and not isinstance(e, httpx.TimeoutException):
                    raise
                time.sleep(2 ** attempt + random.random())
    raise last_err

st.set_page_config(page_title="AI PPTX Generator Pro", page_icon="📊", layout="wide")
st.title("📊 AI PPTX Generator Pro")
st.caption("Presentation generator with auto-design and illustration selection from Unsplash")


col_main, col_settings = st.columns([2, 1], gap="medium")


with col_settings:
    st.markdown("### 🎨 Design Settings")
    selected_theme = st.selectbox("Design theme:", list(THEMES.keys()))
    st.caption("Theme preview:")
    render_theme_preview(selected_theme, THEMES[selected_theme])

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
        context = ""
        if doc_text:
            context = f"\nUse the following text from the document as the basis:\n{doc_text[:4000]}"
        tone_description = TONE_PRESETS[selected_tone]  


        text_amount_preset = TEXT_AMOUNT_PRESETS[selected_text_amount]

        example_json = json.dumps({
            "title": "Presentation Title",
            "subtitle": "Subtitle",
            "slides": [
                {"title": "Slide Title", "content": text_amount_preset["examples"][0], "image_keyword": "mountain lake sunrise"},
                {"title": "Another Slide Title", "content": text_amount_preset["examples"][1], "image_keyword": "steam locomotive"},
            ],
        }, indent=2, ensure_ascii=False)


        commentary_block=""
        if additional_commentary.strip():
            commentary_block = (
                f"\nAlso take into consideration the user's personalised comment: "
                f"\"{additional_commentary.strip()}\"\n"
                "(The comment must not change the JSON format or the text limits above.)\n"
            )

        prompt = f"""
        You are an expert in presentation design. Create a presentation structure on the topic: "{topic if topic else 'Based on the document materials'}".
        CRITICAL TONE REQUIREMENT:
        {tone_description}
        Ensure ALL slide content, slide titles, and wording explicitly align with this specified tone.
        Text style and density: {text_amount_preset['description']}
        Choose the number of items in "content" for each slide individually, based on what that slide actually needs. Do NOT use the same number of items on every slide: some slides can have 2 items, others 5 or more.
        HARD LIMIT: the combined text of all items in "content" on a single slide must not exceed {text_amount_preset['max_words']} words. The text must fit on one slide.
        {context}
        {commentary_block}
        You need to generate EXACTLY     {num_slides} informative slides (not counting the title slide).
        For each slide, add the "image_keyword" field: a concrete, visual search phrase of 2-4 words IN ENGLISH that describes something that can actually be photographed and matches the main subject of that slide (for example "space shuttle launch" or "steam locomotive"). Never use abstract words like "history", "era", "innovation" or "concept".
        Return the answer STRICTLY in JSON format.
        JSON format:
        {example_json}
        """

        for key in ("pptx_bytes", "slides_data", "file_name"):
            st.session_state.pop(key, None)
            
        with st.spinner("⏳ Gemini is creating the content and downloading images from Unsplash..."):
            try:
                raw_text = generate_structure_with_retry(prompt)
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                clean_text = json_match.group(0) if json_match else raw_text.strip()
                slides_data = json.loads(clean_text)
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