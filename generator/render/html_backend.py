"""Painter #2: draws the same slide descriptions (SlideSpec) as HTML for the in-browser preview.

Every item becomes an absolutely positioned <div>. Positions are percentages of the
slide, and font sizes use the CSS unit "cqw" (1% of the slide's own width), so a slide
looks the same whether it is shown as a small thumbnail or stretched across the page.
"""
import html

from generator.design.colors import to_hex
from generator.render.primitives import SLIDE_H, SLIDE_W, Box, Gradient, Picture, Text
from generator.render.textfit import BULLET_INDENT_EM, line_height

# Each Office font with look-alikes for computers that do not have it installed.
FONT_STACKS = {
    "Calibri": "Calibri, Carlito, 'Segoe UI', 'Helvetica Neue', sans-serif",
    "Arial": "Arial, 'Liberation Sans', Helvetica, sans-serif",
    "Georgia": "Georgia, 'Times New Roman', 'Liberation Serif', serif",
}
GRADIENT_CSS = {"horizontal": "to right", "vertical": "to bottom", "diagonal": "135deg"}
JUSTIFY = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}


def _cqw(inches):
    """A length in inches as a share of the slide width."""
    return f"{inches / SLIDE_W * 100:.3f}cqw"


def _pt(points):
    return _cqw(points / 72)


def _rect(item):
    return (
        f"position:absolute;left:{item.x / SLIDE_W * 100:.3f}%;top:{item.y / SLIDE_H * 100:.3f}%;"
        f"width:{item.w / SLIDE_W * 100:.3f}%;height:{item.h / SLIDE_H * 100:.3f}%;"
    )


def _fill_css(fill, alpha=1.0):
    if fill is None:
        return "transparent"
    if isinstance(fill, Gradient):
        return f"linear-gradient({GRADIENT_CSS[fill.direction]},{to_hex(fill.start)},{to_hex(fill.end)})"
    if alpha < 1.0:
        return f"rgba({fill[0]},{fill[1]},{fill[2]},{alpha:.3f})"
    return to_hex(fill)


def _box_html(box):
    style = _rect(box) + f"background:{_fill_css(box.fill, box.alpha)};box-sizing:border-box;"
    if box.ellipse:
        style += "border-radius:50%;"
    elif box.radius:
        style += f"border-radius:{_cqw(box.radius)};"
    if box.line:
        style += f"border:{_pt(box.line_width)} solid {to_hex(box.line)};"
    if box.shadow:
        style += f"box-shadow:0 {_pt(5)} {_pt(18)} rgba(0,0,0,0.14);"
    return f'<div style="{style}"></div>'


def _text_html(block):
    style = (
        _rect(block)
        + f"display:flex;flex-direction:column;justify-content:{JUSTIFY[block.valign]};"
        + f"text-align:{block.align};overflow:visible;"
    )
    parts = []
    for i, para in enumerate(block.paragraphs):
        size = para.size or block.size
        font = para.font or block.font
        bold = block.bold if para.bold is None else para.bold
        italic = block.italic if para.italic is None else para.italic
        gap = block.space_after if para.space_after is None else para.space_after
        p_style = (
            f"font-family:{FONT_STACKS.get(font, FONT_STACKS['Arial'])};font-size:{_pt(size)};"
            f"line-height:{line_height(font) * block.line_spacing:.3f};"
            f"font-weight:{700 if bold else 400};font-style:{'italic' if italic else 'normal'};"
            f"color:{to_hex(para.color or block.color)};margin:0;overflow-wrap:break-word;"
        )
        if gap and i < len(block.paragraphs) - 1:
            p_style += f"margin-bottom:{_pt(gap)};"
        text = html.escape(para.text)   # the text comes from an AI model: never trust it as HTML
        if para.bullet:
            p_style += f"padding-left:{BULLET_INDENT_EM}em;text-indent:-{BULLET_INDENT_EM}em;"
            mark_color = to_hex(block.bullet_color or block.color)
            text = (
                f'<span style="display:inline-block;width:{BULLET_INDENT_EM}em;text-indent:0;'
                f'color:{mark_color};font-weight:400;font-style:normal;">{html.escape(block.bullet_char)}</span>{text}'
            )
        parts.append(f'<div style="{p_style}">{text}</div>')
    return f'<div style="{style}">{"".join(parts)}</div>'


def _picture_html(item, image_urls):
    url = image_urls.get(item.key)
    if not url:
        return ""
    style = _rect(item) + f"background:url('{url}') center/cover no-repeat;"
    if item.radius:
        style += f"border-radius:{_cqw(item.radius)};"
    return f'<div style="{style}"></div>'


def slide_to_html(spec, image_urls=None):
    """One slide as an HTML snippet. image_urls maps picture keys to URLs (usually data: URLs)."""
    image_urls = image_urls or {}
    parts = []
    for item in spec.items:
        if isinstance(item, Box):
            parts.append(_box_html(item))
        elif isinstance(item, Text):
            parts.append(_text_html(item))
        elif isinstance(item, Picture):
            parts.append(_picture_html(item, image_urls))
    return (
        '<div style="position:relative;width:100%;aspect-ratio:16/9;container-type:inline-size;'
        f'overflow:hidden;background:{_fill_css(spec.background)};">{"".join(parts)}</div>'
    )
