"""The entry point of the renderer: content + style + colours + pictures -> slides.

    Deck  --layouts.py-->  list of SlideSpec  --pptx_backend.py-->  .pptx file
                                              --html_backend.py-->  preview in the browser

Nothing here talks to the network or to an AI model, so the same content can be
re-drawn in another style or colour theme instantly.
"""
from generator.design.colors import make_palette
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import DEFAULT_THEME, THEMES
from generator.render.html_backend import slide_to_html
from generator.render.layouts import build_specs
from generator.render.pptx_backend import specs_to_pptx


def build_slides(deck, style_key, theme_name, image_keys):
    """Describe every slide of the deck as a SlideSpec (what to draw and where)."""
    style = STYLES.get(style_key, STYLES[DEFAULT_STYLE])
    palette = make_palette(THEMES.get(theme_name, THEMES[DEFAULT_THEME]))
    return build_specs(deck, style, palette, image_keys)


def build_pptx(deck, style_key, theme_name, images):
    """Build the .pptx file and return it as bytes. images is {image_keyword: image bytes}."""
    specs = build_slides(deck, style_key, theme_name, images.keys())
    return specs_to_pptx(specs, images, title=deck.title)


def build_preview(deck, style_key, theme_name, image_urls):
    """Build an HTML snippet per slide. image_urls is {image_keyword: URL the browser can show}."""
    specs = build_slides(deck, style_key, theme_name, image_urls.keys())
    return [slide_to_html(spec, image_urls) for spec in specs]
