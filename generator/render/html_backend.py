"""Painter #2: draws the same slide descriptions (SlideSpec) as HTML for the in-browser preview.

Every item becomes an absolutely positioned <div>. Positions are percentages of the
slide, and font sizes use the CSS unit "cqw" (1% of the slide's own width), so a slide
looks the same whether it is shown as a small thumbnail or stretched across the page.
"""
import html
import math

from generator.design.colors import to_hex
from generator.render.primitives import SLIDE_H, SLIDE_W, Box, ChartShape, Gradient, Picture, Text
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


def _nice_ceiling(value):
    """Round up to a value whose quarters are round numbers (for gridlines): 28.4 -> 30, 163 -> 200."""
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 1.2, 1.6, 2, 2.4, 3, 4, 5, 6, 8, 10):
        if step * magnitude >= value:
            return step * magnitude
    return 10 * magnitude


def _chart_html(item):
    """A simplified SVG drawing of a ChartShape. Coordinates are in hundredths of an inch."""
    width, height = item.w * 100, item.h * 100
    font_px = item.font_size / 72 * 100
    family = html.escape(FONT_STACKS.get(item.font, FONT_STACKS["Arial"]), quote=True)
    ink, grid = to_hex(item.text_color), to_hex(item.grid_color)
    out = []

    def text(x, y, value, anchor="middle", size=font_px, color=ink, bold=False):
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size:.1f}" fill="{color}" '
                   f'text-anchor="{anchor}" font-weight="{700 if bold else 400}">{html.escape(str(value))}</text>')

    def legend(entries, x, y, vertical):
        for name, color in entries:
            out.append(f'<rect x="{x:.1f}" y="{y - font_px * 0.75:.1f}" width="{font_px * 0.8:.1f}" '
                       f'height="{font_px * 0.8:.1f}" rx="2" fill="{to_hex(color)}"/>')
            text(x + font_px * 1.2, y, name, anchor="start", size=font_px)
            if vertical:
                y += font_px * 1.7
            else:
                x += font_px * 1.2 + len(name) * font_px * 0.55 + font_px * 1.5

    if item.kind == "pie":
        values = item.series[0][1]
        total = sum(values) or 1
        radius = min(height * 0.46, width * 0.28)
        cx, cy, inner = radius + 10, height / 2, radius * 0.58
        angle = -math.pi / 2
        for value, color in zip(values, item.colors):
            sweep = value / total * 2 * math.pi
            end = angle + sweep
            large = 1 if sweep > math.pi else 0
            if sweep >= 2 * math.pi - 1e-6:         # a single slice: two half arcs
                end = angle + 2 * math.pi - 1e-4
            p1 = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            p2 = (cx + radius * math.cos(end), cy + radius * math.sin(end))
            q1 = (cx + inner * math.cos(end), cy + inner * math.sin(end))
            q2 = (cx + inner * math.cos(angle), cy + inner * math.sin(angle))
            out.append(
                f'<path d="M{p1[0]:.1f},{p1[1]:.1f} A{radius:.1f},{radius:.1f} 0 {large} 1 {p2[0]:.1f},{p2[1]:.1f} '
                f'L{q1[0]:.1f},{q1[1]:.1f} A{inner:.1f},{inner:.1f} 0 {large} 0 {q2[0]:.1f},{q2[1]:.1f} Z" '
                f'fill="{to_hex(color)}" stroke="{to_hex(item.background)}" stroke-width="3"/>')
            angle += sweep
        names = [f"{name} — {item.label(v)}" for name, v in zip(item.categories, values)]
        font_px *= 1.2
        legend(list(zip(names, item.colors)), cx + radius + 40, cy - (len(names) - 1) * font_px * 0.85, True)
    else:
        top = font_px * 2.2 if item.legend else font_px * 1.6
        if item.legend:
            legend([(name, color) for (name, _), color in zip(item.series, item.colors)], 0, font_px, False)
        values = [v for _, vs in item.series for v in vs]
        low, high = min(0.0, min(values)), max(0.0, max(values))
        high = _nice_ceiling(high + (high - low) * 0.08) if high > 0 else 0
        if high == low:
            high = low + 1
        count, n_series = len(item.categories), len(item.series)

        if item.kind == "bar":
            left = min(width * 0.32, max(len(c) for c in item.categories) * font_px * 0.55 + 12)
            plot_w = width - left - font_px * 4
            band = (height - top) / count
            scale = plot_w / (high - low)
            zero = left + (0 - low) * scale
            for i, category in enumerate(item.categories):
                y0 = top + i * band
                text(left - 10, y0 + band / 2 + font_px * 0.35, category, anchor="end")
                bar_h = band * 0.6 / n_series
                for k, ((_, vs), color) in enumerate(zip(item.series, item.colors)):
                    v = vs[i]
                    y = y0 + band * 0.2 + k * bar_h
                    x = min(zero, zero + v * scale)
                    out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{abs(v) * scale:.1f}" height="{bar_h:.1f}" '
                               f'fill="{to_hex(color)}"/>')
                    if item.show_values:
                        text(zero + v * scale + 8, y + bar_h / 2 + font_px * 0.35, item.label(v), anchor="start",
                             bold=True)
            out.append(f'<line x1="{zero:.1f}" y1="{top:.1f}" x2="{zero:.1f}" y2="{height:.1f}" stroke="{grid}"/>')
        else:
            bottom = height - font_px * 1.8
            left = 0 if item.show_values else font_px * 3.5
            plot_w = width - left
            scale = (bottom - top) / (high - low)
            zero = bottom - (0 - low) * scale
            if not item.show_values:
                for step in range(5):                 # light horizontal gridlines with the value scale
                    value = low + (high - low) * step / 4
                    y = bottom - (value - low) * scale
                    out.append(f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{width:.1f}" y2="{y:.1f}" '
                               f'stroke="{grid}" stroke-width="0.8"/>')
                    text(left - 8, y + font_px * 0.35, item.label(value), anchor="end", size=font_px * 0.9)
            band = plot_w / count
            for i, category in enumerate(item.categories):
                text(left + band * (i + 0.5), height - font_px * 0.4, category)
            if item.kind == "column":
                bar_w = band * 0.6 / n_series
                for i in range(count):
                    for k, ((_, vs), color) in enumerate(zip(item.series, item.colors)):
                        v = vs[i]
                        x = left + band * i + band * 0.2 + k * bar_w
                        y = min(zero, zero - v * scale)
                        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{abs(v) * scale:.1f}" '
                                   f'fill="{to_hex(color)}"/>')
                        if item.show_values:
                            text(x + bar_w / 2, zero - v * scale - 8, item.label(v), bold=True)
            else:
                for (_, vs), color in zip(item.series, item.colors):
                    points = [(left + band * (i + 0.5), zero - v * scale) for i, v in enumerate(vs)]
                    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
                    out.append(f'<polyline points="{path}" fill="none" stroke="{to_hex(color)}" stroke-width="4"/>')
                    for (x, y), v in zip(points, vs):
                        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{to_hex(color)}"/>')
                        if item.show_values:
                            text(x, y - 14, item.label(v), bold=True)
            out.append(f'<line x1="{left:.1f}" y1="{zero:.1f}" x2="{width:.1f}" y2="{zero:.1f}" stroke="{grid}"/>')

    return (f'<div style="{_rect(item)}"><svg viewBox="0 0 {width:.1f} {height:.1f}" width="100%" height="100%" '
            f'style="overflow:visible;font-family:{family}">{"".join(out)}</svg></div>')


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
        elif isinstance(item, ChartShape):
            parts.append(_chart_html(item))
    return (
        '<div style="position:relative;width:100%;aspect-ratio:16/9;container-type:inline-size;'
        f'overflow:hidden;background:{_fill_css(spec.background)};">{"".join(parts)}</div>'
    )
