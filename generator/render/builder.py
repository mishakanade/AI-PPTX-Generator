"""The entry point of the renderer: content + style + colours + pictures -> slides.

    Deck  --layouts.py-->  list of SlideSpec  --pptx_backend.py-->  .pptx file
                                              --html_backend.py-->  preview in the browser

Nothing here talks to the network or to an AI model, so the same content can be
re-drawn in another style or colour theme instantly.
"""
import base64

from PIL import Image

from generator.design.colors import make_palette
from generator.design.styles import DEFAULT_STYLE, STYLES
from generator.design.themes import DEFAULT_THEME, THEMES
from generator.images.pictures import open_image
from generator.render.html_backend import slide_to_html
from generator.render.layouts import build_specs
from generator.render.logo import FOOTER_RESERVE, LOGO_KEY, logo_aspect, place_logo
from generator.render.pptx_backend import specs_to_pptx


def theme_colors(theme):
    """A theme given by name (a key of THEMES) or directly as {"bg", "title", "text", "accent"}."""
    if isinstance(theme, dict):
        return theme
    return THEMES.get(theme, THEMES[DEFAULT_THEME])


def build_slides(deck, style_key, theme_name, image_keys, credits=None, logo=None):
    """Describe every slide of the deck as a SlideSpec (what to draw and where).

    logo: the logo image bytes, or None. It is put into a free corner of every slide.
    """
    style = STYLES.get(style_key, STYLES[DEFAULT_STYLE])
    palette = make_palette(theme_colors(theme_name))
    # with a logo, content areas end a little higher, so that a bottom corner stays free for it
    specs = build_specs(deck, style, palette, image_keys, credits, footer_reserve=FOOTER_RESERVE if logo else 0.0)
    if logo:
        aspect = logo_aspect(logo)
        for spec in specs:
            place_logo(spec, aspect)
    return specs


def build_pptx(deck, style_key, theme_name, images, credits=None, transition=None, logo=None):
    """Build the .pptx file and return it as bytes.

    images is {image_keyword: image bytes}; credits is {image_keyword: author line}
    and ends up in the speaker notes of the slides with those pictures.
    transition: None, "fade", "push" or "wipe" - played between slides in PowerPoint.
    logo: the logo image bytes, or None.
    """
    specs = build_slides(deck, style_key, theme_name, images.keys(), credits, logo)
    images = {**images, LOGO_KEY: logo} if logo else images
    return specs_to_pptx(specs, images, title=deck.title, transition=transition)


def build_preview(deck, style_key, theme_name, image_urls, logo=None):
    """Build an HTML snippet per slide. image_urls is {image_keyword: URL the browser can show}."""
    specs = build_slides(deck, style_key, theme_name, image_urls.keys(), logo=logo)
    if logo:
        image_urls = {**image_urls, LOGO_KEY: logo_data_url(logo)}
    return [slide_to_html(spec, image_urls) for spec in specs]


def logo_data_url(data):
    """The logo as a data: URL in its own format, so a transparent PNG stays transparent."""
    mime = Image.MIME.get(open_image(data).format, "image/png")
    return f"data:{mime};base64," + base64.b64encode(data).decode()
