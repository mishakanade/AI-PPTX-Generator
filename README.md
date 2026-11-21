# AI-PPTX-Generator

An open-source app that turns a topic or a document into an editable PowerPoint presentation.
An AI of your choice writes the content (Gemini, ChatGPT or Claude through their APIs, or any
AI chat by copy & paste), Unsplash supplies the photos, and a layout engine designs every
slide in the style and colours you choose.

It is a BYOK (Bring Your Own Key) application: you use your own API keys.
The project is in alpha and is built solo, so expect changes.

## What it does

- **Your choice of AI.** Gemini, OpenAI (ChatGPT models) or Anthropic (Claude) through their
  APIs, with the model name editable. Or **no API key at all**: in copy & paste mode the app
  gives you a request to paste into ChatGPT, Claude, Gemini or any other AI chat, and builds
  the presentation (photos included) from the answer you paste back.
- **Content from a topic or a document.** Type a topic, or attach a TXT, PDF or DOCX file
  (up to about 60,000 characters are used). Choose the tone, the amount of text per slide
  and the number of slides, and add your own wishes.
- **13 slide types.** The model picks the type that suits each slide: bullets, full-screen photo,
  two columns, cards, key numbers, chart, quote, key statement, timeline, table, agenda,
  section divider and closing takeaways.
- **Native, editable charts.** Column, bar, line and doughnut charts are real PowerPoint charts,
  so the data can be edited after download.
- **5 design styles × 32 colour themes, or your own colours.** Minimal, Editorial, Corporate,
  Soft and Bold, each working with every palette. Custom colours (for example your brand's)
  are checked for contrast and adjusted where text would be hard to read. Slides of the same type alternate between layout variants
  (photo on the left or right, card grid or numbered list, and so on).
- **Text that fits.** The engine measures text before placing it, so titles and paragraphs
  shrink or grow to fit their space instead of overlapping.
- **Speaker notes.** Optionally, the model writes what to say on each slide; the notes go into
  PowerPoint's presenter view. Photo credits are added to the notes as well.
- **Instant redesign.** After generation, pick another style or theme: the file is redrawn
  with the same content, without a new request to the AI.
- **Edit before you download.** Change titles and text or delete slides in a simple form;
  the file is redrawn without asking the model again. Or let the AI rewrite a single slide,
  optionally with a wish such as "shorter" or "turn it into a chart".
- **Your photos, your choice.** Swap any slide's photo for another one from Unsplash, upload
  your own picture, or remove it. Photos carry alternative text for screen readers.
- **Save and reopen projects.** One `.project.json` file keeps the text, photos, style and
  colours, so you can come back later, restyle and download again without asking the AI.
- **Preview in the browser** before you download.
- **Interface in English or Russian**, chosen from the browser's language and switchable in
  the sidebar. The presentation itself is written in the language of your topic.

## Getting started

1. Get the API keys you need:
   - one AI key: Gemini (https://aistudio.google.com/api-keys), OpenAI
     (https://platform.openai.com/api-keys) or Anthropic (https://platform.claude.com),
     or none if you will use the copy & paste mode with an AI chat
   - Unsplash (optional, for photos): https://unsplash.com/developers
2. Clone the project and open its folder:
   ```bash
   git clone https://github.com/mishakanade/AI-PPTX-Generator.git
   cd AI-PPTX-Generator
   ```
3. Install the libraries (Python 3.11 or newer):
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to a new file named `.env` and put your keys into it
   (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `UNSPLASH_CLIENT_ID`). Without the
   Unsplash key the app still works, just without photos.
5. Start the app:
   ```bash
   python -m streamlit run app.py
   ```

Instead of step 4 you can paste the keys into **API keys** in the app's sidebar. Keys typed
there are kept only for that browser session and are never saved.

## Publishing the app

On a hosting such as Streamlit Community Cloud there is no `.env` file. Either let every
visitor paste their own key in the sidebar (true BYOK), or give the app your keys as
secrets, in TOML format:

```toml
GEMINI_API_KEY = "..."
UNSPLASH_CLIENT_ID = "..."
```

Keep in mind that keys set as secrets are used by everyone who opens the app.

## How it works

```
topic / document
      │
      ▼
content/prompt.py   builds the request: slide types, text limits, tone, language
      │
      ▼
content/llm.py      asks the chosen AI for JSON in a strict schema, retries and falls back on failures
                    (or: the user pastes the answer of an AI chat)
      │
      ▼
content/schema.py   checks the answer and repairs it, so every slide can be drawn
      │
      ▼
images/unsplash.py  finds one distinct photo per slide, in parallel
      │
      ▼
render/layouts.py   one layout per slide type; asks the style how cards, titles and covers look
      │
      ├──▶ render/pptx_backend.py   draws the slides into the .pptx file
      └──▶ render/html_backend.py   draws the same slides as HTML for the preview
```

Layouts do not draw directly. They describe each slide as a list of simple shapes
(boxes, text blocks, pictures, charts) measured in inches, and two painters draw that same
description: one into PowerPoint, one into the browser. That is why the preview matches the file.

## Project structure

```
app.py                       Streamlit interface: form, design picker, preview, download
ui_text.py                   every text of the interface, in English and Russian
generator/
  config.py                  API keys and model names
  content/
    presets.py               tone and text-amount presets
    prompt.py                builds the request for the AI (API or chat)
    llm.py                   sends it, retries, falls back to plain JSON if the schema is rejected
    providers/               one module per AI provider: Gemini, OpenAI, Claude
    schema.py                slide types and fields; validation and repair of the answer
    documents.py             reads TXT / PDF / DOCX
    editing.py               slides as editable text and back
  design/
    themes.py                the 32 colour palettes
    colors.py                derives card, line, text-on-accent and chart colours from a palette
    styles.py                the 5 design styles
    sample_deck.py           built-in example presentation (style previews, tests)
  images/
    unsplash.py              photo search, download and credits; the user's own pictures
  project.py                 saving a project to one JSON file and opening it again
  render/
    primitives.py            the shapes a slide is described with
    textfit.py               text measurement: line wrapping, shrink-to-fit
    font_metrics.json        character widths of Calibri, Arial and Georgia
    layout_tools.py          shared helpers for layouts and styles
    layouts.py               one layout function per slide type, with variants
    builder.py               entry point: content + style + theme + photos → slides
    pptx_backend.py          draws slides into a .pptx file
    html_backend.py          draws slides as HTML for the preview
tests/                       automated tests (see below)
tools/
  render_samples.py          saves the example deck in every style to samples/
  build_font_metrics.py      regenerates font_metrics.json
.streamlit/config.toml       look of the interface
```

## Development

Install the extra tools and run the tests (about 5 seconds, no API keys needed):

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests check, among other things, that on every slide type, in every style, text and
photos stay on the slide, every text fits its box and no texts overlap. They also run on
GitHub for every push.

To look at the designs without API keys, save the example deck in every style:

```bash
python tools/render_samples.py --theme "Dark Modern"
```

Add `--stress` for a deck of deliberately long texts, and `--pdf` to also get PDF files
(needs LibreOffice).

### Adding a design style

Subclass `Style` in `generator/design/styles.py`, override what should look different
(fonts, `frame`, `card`, `cover`, decorations) and add it to `STYLES`. It appears in the
app automatically, and the tests check it like the others.
