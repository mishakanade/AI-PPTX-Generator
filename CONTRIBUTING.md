# Contributing

Thank you for wanting to help. This file explains how the project is put together, how to
check a change, and which rules keep the code easy to follow.

## Setting up

```bash
git clone https://github.com/mishakanade/AI-PPTX-Generator.git
cd AI-PPTX-Generator
pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
```

No API key is needed for any of this: every test replaces the AI and Unsplash with fakes.
To try the app itself, start it with `python -m streamlit run app.py` and choose
**Any AI chat (copy & paste)** in the sidebar if you have no key. To work on the interface,
`python -m streamlit run tools/ui_demo.py` runs it with a pretend AI: every screen in seconds.

## Before you open a pull request

1. `python -m pytest -q` passes (about 40 seconds).
2. `ruff check .` finds nothing (`ruff check . --fix` repairs most findings by itself).
3. A change in behaviour comes with a test that fails without it.
4. A new text in the interface is added to **both** languages in `ui_text.py`, with the
   same `{placeholders}`; `tests/test_ui_text.py` checks this.
5. If you changed how slides look, run `python tools/render_samples.py --pdf` and look at
   the files in `samples/`. Where LibreOffice is installed, `tests/test_rendering.py` also
   checks the layout against LibreOffice's real drawing.

GitHub runs the same checks (lint, tests, rendering) for every push.

## How the code is organised

The README has a diagram and a list of every file. The short version:

- `generator/content/` turns a topic or document into a `Deck`: the prompt, the request to
  the AI, and the checking and repairing of its answer (`schema.py`).
- `generator/render/` turns a `Deck` into slides. Layouts never draw: they describe each
  slide as a list of boxes, texts, pictures and charts (`primitives.py`), measured in inches,
  and two painters draw that list, one into PowerPoint and one into HTML for the preview.
- `generator/design/` holds the styles and colour themes.
- `interface/` is the Streamlit page, split by area of the screen.

## Common changes

**A new design style.** Subclass `Style` in `generator/design/styles.py`, override what
should look different (fonts, `frame`, `card`, `cover`, decorations) and add it to `STYLES`.
It appears in the app automatically, and every layout test runs for it too. Use only
Calibri, Arial or Georgia: the engine knows their letter widths (`render/font_metrics.json`).

**A new colour theme.** Add it to `generator/design/themes.py`. The four colours you give
are enough: card, line and chart colours are derived from them, with readable contrast.

**A new slide type.** Add it to `SLIDE_TYPE_GUIDE` and the `Slide` model in
`generator/content/schema.py`, teach `_normalize_slide` what the type needs (and what to fall
back to when the AI leaves it out), write `layout_<type>` in `generator/render/layouts.py`,
and put an example into `generator/design/sample_deck.py` and `tests/stress_deck.py`.

**A new AI provider.** Add a module to `generator/content/providers/` with the functions
described in its `__init__.py` (`ask`, `classify`, `explain`, `default_models`), register it
there and in `interface/common.py`, and test it against a fake server the way
`tests/test_providers.py` does.

## Style of the code

- Names and comments in plain English; a comment explains *why*, not what the line does.
- Functions short enough to read at once; a module does one thing.
- The model's answer is never trusted: everything it returns goes through `schema.py`.
- Keys are never logged, saved to a project file or sent anywhere except to their own API.
- Lines up to 120 characters; `ruff` keeps imports in order.

## Reporting a problem

Open an issue with what you did, what you expected and what happened. For a layout problem,
a saved project (**Save project** in the app) lets anyone redraw exactly your slides
without an API key.
