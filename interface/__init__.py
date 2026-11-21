"""The Streamlit interface, split by part of the page. app.py calls them from top to bottom.

    common.py      translations, small helpers, values shared by the other modules
    sidebar.py     language switch, AI provider and keys, the content form, opening a project
    design.py      colour theme, custom colours, transition, logo, style cards
    generation.py  writing the content: through an API, by copy & paste with a chat, or plan first
    result.py      drawing the file and showing it: preview, download, editing, photos, notes

The generation functions are always called through their modules (llm.generate_deck,
unsplash.fetch_photos), never imported by name: the tests replace them with fakes there.
"""
