"""Slide layouts: one function per slide type.

Each function receives the context (palette, style, slide number...) and one slide of
content, and returns a SlideSpec - the list of boxes, texts and pictures to draw.
Layouts decide *where* things go and how big the text is; *how* things look
(card shape, title treatment, fonts) is asked from the active style.
"""
import math

from generator.design.colors import WHITE, series_colors
from generator.render.layout_tools import MARGIN as M
from generator.render.layout_tools import Area, Ctx, heading, measured, rule, stack
from generator.render.primitives import SLIDE_H as H
from generator.render.primitives import SLIDE_W as W
from generator.render.primitives import Box, ChartShape, Para, Picture, SlideSpec, Text
from generator.render.textfit import (
    POINTS_PER_INCH, apply_scale, best_scale, count_lines, fit, fit_single_line, line_height,
    simple_text, text_height, text_width,
)

GAP = 0.4   # space between cards and columns, in inches


def _image_key(ctx, slide):
    """The slide's picture key if that picture was really downloaded, otherwise None."""
    key = slide.image_keyword
    return key if key and key in ctx.images else None


def _words(texts):
    return sum(len(str(t).split()) for t in texts)


def _vertical_start(area, content_h):
    """Where a group of the given height starts: slightly above the middle of the free space."""
    spare = max(0.0, area.h - content_h)
    return area.y + spare * 0.38


# ----- cards: shared by "cards", "stats" and "two_columns" --------------------------------

def _card_grid(ctx, area, contents, columns, emphasis=False, max_scale=1.4, height_share=0.8, valign="top"):
    """Draw equal cards in a grid.

    contents is a list of functions, one per card: each takes the card's look (colours)
    and returns the paragraphs of that card. All cards of a row get the same height:
    as much as the fullest one needs, but never more than the area allows.
    """
    style = ctx.style
    rows = [contents[i:i + columns] for i in range(0, len(contents), columns)]
    card_w = (area.w - GAP * (columns - 1)) / columns
    max_h = (area.h - GAP * (len(rows) - 1)) / len(rows)

    # First pass: build the texts and measure how tall each card wants to be.
    probe = style.card(ctx, 0, 0, card_w, max_h, 0, emphasis)
    pad_h = max_h - probe.inner.h   # vertical padding the style adds inside a card
    blocks, needed = [], 0.0
    for build in contents:
        block = Text(0, 0, probe.inner.w, 0, build(probe), font=style.body_font, size=16,
                     color=probe.text_color, space_after=6, valign=valign,
                     bullet_char=style.bullet_char, bullet_color=probe.accent_color)
        blocks.append(block)
        needed = max(needed, text_height(block) + pad_h)
    # a single row of cards takes `height_share` of the area; two rows share all of it
    card_h = min(max_h, max(needed, area.h * height_share if len(rows) == 1 else max_h))

    # One size factor for all cards, so they stay consistent: shrink if the fullest card
    # overflows, grow (up to max_scale) if even the fullest card is half empty.
    inner_h = card_h - pad_h
    scale = min(best_scale(block, inner_h, max_scale=max_scale, fill=0.8) for block in blocks)

    # Second pass: place the cards and put each text into its card.
    total_h = card_h * len(rows) + GAP * (len(rows) - 1)
    y = _vertical_start(area, total_h)
    items, index = [], 0
    for row in rows:
        for col in range(len(row)):
            x = area.x + col * (card_w + GAP)
            look = style.card(ctx, x, y, card_w, card_h, index, emphasis)
            block = blocks[index]
            block.x, block.y, block.w, block.h = look.inner.x, look.inner.y, look.inner.w, look.inner.h
            items += look.items + [apply_scale(block, scale)]
            index += 1
        y += card_h + GAP
    return items


# ----- one layout per slide type ----------------------------------------------------------

def layout_bullets(ctx, slide):
    style, p = ctx.style, ctx.palette
    key = _image_key(ctx, slide)
    bullets = slide.bullets or []
    # every second bullet slide with a photo is mirrored, so neighbours do not look identical
    photo_left = ctx.variant % 2 == 1
    pictures = []

    if key and style.image_bleed:
        # the photo takes a whole side of the slide, from top to bottom
        panel_w = W - 8.3
        if photo_left:
            items, area = style.frame(ctx, slide.title, left=panel_w + 0.65)
            pictures = [Picture(0, 0, panel_w, H, key)]
        else:
            items, area = style.frame(ctx, slide.title, right=W - panel_w - 0.65)
            pictures = [Picture(W - panel_w, 0, panel_w, H, key)]
    elif key:
        items, full = style.frame(ctx, slide.title)
        image_w = full.w * 0.42
        text_w = full.w - image_w - 0.6
        image_x = full.x if photo_left else full.right - image_w
        pictures = style.image_frame(ctx, image_x, full.y, image_w, full.h, key)
        area = Area(full.right - text_w if photo_left else full.x, full.y, text_w, full.h)
    else:
        items, full = style.frame(ctx, slide.title)
        if len(bullets) >= 5 and _words(bullets) / len(bullets) <= 12:
            # many short points and the whole width free: two columns read better than one long list
            return SlideSpec(style.background(ctx), items + _bullet_columns(ctx, full, bullets))
        area = Area(full.x, full.y, min(full.w, 9.6), full.h)

    # Long items are paragraphs, short ones are bullet points: paragraphs get no bullet marks.
    as_paragraphs = bullets and _words(bullets) / len(bullets) > 22
    size = style.body_size + (0 if key else 2)
    text = Text(area.x, area.y, area.w, area.h, [Para(b, bullet=not as_paragraphs) for b in bullets],
                font=style.body_font, size=size, color=p.text, space_after=size * 0.7,
                line_spacing=1.05, bullet_char=style.bullet_char, bullet_color=p.accent)
    return SlideSpec(style.background(ctx), items + [fit(text, max_scale=1.35, fill=0.8)] + pictures)


def _bullet_columns(ctx, area, bullets):
    """Short bullet points split into two columns that share one font size."""
    style, p = ctx.style, ctx.palette
    half = (len(bullets) + 1) // 2
    gap = 0.7
    col_w = (area.w - gap) / 2
    size = style.body_size + 2
    blocks = [
        Text(area.x + i * (col_w + gap), area.y, col_w, area.h, [Para(b, bullet=True) for b in part],
             font=style.body_font, size=size, color=p.text, space_after=size * 0.7, line_spacing=1.05,
             bullet_char=style.bullet_char, bullet_color=p.accent)
        for i, part in enumerate((bullets[:half], bullets[half:]))
    ]
    scale = min(best_scale(block, max_scale=1.4, fill=0.7) for block in blocks)
    for block in blocks:
        apply_scale(block, scale)
    # short lists would huddle under the title: place the pair of columns a little above the middle
    content_h = min(area.h, max(text_height(block) for block in blocks))
    for block in blocks:
        block.y, block.h = _vertical_start(area, content_h), content_h
    return blocks


def _marker(ctx, x, y, size, number):
    """A list number in the style's marker: a filled circle, a filled square or just the digits."""
    style, p = ctx.style, ctx.palette
    label = f"{number:02d}"
    if style.marker == "plain":
        return [simple_text(x, y, size, size, label, font=style.heading_font, size=round(size * 72 * 0.5),
                            bold=True, color=p.accent, valign="middle")]
    shape = Box(x, y, size, size, fill=p.accent, ellipse=style.marker == "circle")
    return [shape, simple_text(x, y, size, size, label, font=style.heading_font, size=round(size * 72 * 0.34),
                               bold=True, color=p.on_accent, align="center", valign="middle")]


def layout_image(ctx, slide):
    style, p = ctx.style, ctx.palette
    key = _image_key(ctx, slide)
    if not key:
        # no photo was found: a statement slide still works without it
        return style.cover(ctx, "section", slide.title, slide.subtitle or "")

    # Title and subtitle are one block pinned to the bottom, so they can never overlap.
    title_size = 46
    while title_size > 32 and count_lines(slide.title, style.heading_font, title_size, 9.6, style.heading_bold) > 3:
        title_size -= 1
    paragraphs = [Para(slide.title, size=title_size, bold=style.heading_bold, font=style.heading_font,
                       color=WHITE, space_after=16)]
    if slide.subtitle:
        paragraphs.append(Para(slide.subtitle, size=22))
    text = Text(M, 0.9, 9.6, H - 2.45, paragraphs, font=style.body_font, size=22, color=(236, 236, 236),
                valign="bottom")
    items = [Picture(0, 0, W, H, key),
             Box(0, 0, W, H, fill=(0, 0, 0), alpha=0.5),   # dark veil so white text stays readable
             text,
             Box(M, H - 1.15, 1.2, 0.08, fill=p.accent)]
    items.append(style.page_number(ctx, (220, 220, 220)))
    return SlideSpec((0, 0, 0), items)


def layout_two_columns(ctx, slide):
    style = ctx.style
    items, area = style.frame(ctx, slide.title)

    def column(col):
        def build(look):
            paragraphs = [Para(col.heading, size=21, bold=True, font=style.heading_font,
                               color=look.heading_color, space_after=12)] if col.heading else []
            return paragraphs + [Para(b, size=17, bullet=True, space_after=8) for b in col.bullets]
        return build

    items += _card_grid(ctx, area, [column(c) for c in slide.columns], columns=2)
    return SlideSpec(style.background(ctx), items)


def layout_cards(ctx, slide):
    style = ctx.style
    items, area = style.frame(ctx, slide.title)
    cards = slide.cards

    def card(i, c):
        def build(look):
            return [
                Para(f"{i + 1:02d}", size=13, bold=True, color=look.accent_color, space_after=8),
                Para(c.heading, size=20, bold=True, font=style.heading_font, color=look.heading_color, space_after=8),
                Para(c.text, size=16),
            ]
        return build

    if ctx.variant % 2 == 1:
        items += _card_rows(ctx, area, cards)
    else:
        columns = 2 if len(cards) == 4 else len(cards)
        items += _card_grid(ctx, area, [card(i, c) for i, c in enumerate(cards)], columns)
    return SlideSpec(style.background(ctx), items)


def _card_rows(ctx, area, cards):
    """Cards as a numbered list: one row per card, a number marker on the left, rules between rows."""
    style, p = ctx.style, ctx.palette
    gap = 0.3
    row_h = min(1.6, (area.h - gap * (len(cards) - 1)) / len(cards))
    marker = min(0.78, row_h * 0.72)
    text_x = area.x + marker + 0.45
    blocks = [
        Text(text_x, 0, area.right - text_x, row_h, [
            Para(c.heading, size=21, bold=True, font=style.heading_font, color=p.title, space_after=4),
            Para(c.text, size=17),
        ], font=style.body_font, size=17, color=p.text, valign="middle")
        for c in cards
    ]
    scale = min(best_scale(block, max_scale=1.2, fill=0.9) for block in blocks)

    y = _vertical_start(area, row_h * len(cards) + gap * (len(cards) - 1))
    items = []
    for i, block in enumerate(blocks):
        block.y = y
        items += _marker(ctx, area.x, y + (row_h - marker) / 2, marker, i + 1)
        items.append(apply_scale(block, scale))
        if i < len(blocks) - 1:
            items.append(rule(text_x, y + row_h + gap / 2, area.right - text_x, p.line, 0.012))
        y += row_h + gap
    return items


def layout_stats(ctx, slide):
    style = ctx.style
    items, area = style.frame(ctx, slide.title)
    stats = slide.stats

    def value_size_for(columns):
        """All figures share one size: the largest at which the longest of them fits on one line."""
        card_w = (area.w - GAP * (columns - 1)) / columns
        inner_w = style.card(ctx, 0, 0, card_w, 3.0, 0, style.stats_emphasis).inner.w
        return min(fit_single_line(s.value, style.heading_font, 66, inner_w, bold=True, min_size=20)
                   for s in stats)

    columns = len(stats)
    value_size = value_size_for(columns)
    if len(stats) == 4 and value_size < 40:
        # four long figures in one row would be tiny: arrange them 2 x 2 instead
        columns = 2
        value_size = value_size_for(columns)

    def stat(s):
        def build(look):
            return [
                Para(s.value, size=value_size, bold=True, font=style.heading_font,
                     color=look.accent_color, space_after=10),
                Para(s.label, size=18),
            ]
        return build

    if ctx.variant % 2 == 1 and len(stats) <= 3:
        items += _open_stats(ctx, area, stats)
    else:
        # figures were already sized to fit one line, so this grid must not enlarge them further
        items += _card_grid(ctx, area, [stat(s) for s in stats], columns,
                            emphasis=style.stats_emphasis, max_scale=1.0, height_share=0.62, valign="middle")
    return SlideSpec(style.background(ctx), items)


def _open_stats(ctx, area, stats):
    """Figures without cards: very large numbers in columns divided by thin vertical lines."""
    style, p = ctx.style, ctx.palette
    gap = 0.9
    col_w = (area.w - gap * (len(stats) - 1)) / len(stats)
    value_size = min(fit_single_line(s.value, style.heading_font, 88, col_w, bold=True, min_size=24) for s in stats)
    value_h = value_size * line_height(style.heading_font) / POINTS_PER_INCH
    labels = [Text(0, 0, col_w, 0, [Para(s.label)], font=style.body_font, size=20, color=p.text,
                   line_spacing=1.05) for s in stats]
    label_room = area.h - value_h - 0.5
    scale = min(best_scale(label, label_room, max_scale=1.0) for label in labels)
    label_h = min(label_room, max(text_height(apply_scale(label, scale)) for label in labels))

    content_h = value_h + 0.25 + 0.05 + 0.25 + label_h
    y = _vertical_start(area, content_h)
    items = []
    for i, (stat, label) in enumerate(zip(stats, labels)):
        x = area.x + i * (col_w + gap)
        items.append(simple_text(x, y, col_w, value_h, stat.value, font=style.heading_font, size=value_size,
                                 bold=True, color=p.accent))
        items.append(Box(x, y + value_h + 0.25, 0.6, 0.05, fill=p.accent))
        label.x, label.y, label.h = x, y + value_h + 0.55, label_h
        items.append(label)
        if i:
            items.append(Box(x - gap / 2, y, 0.015, content_h, fill=p.line))   # divider between columns
    return items


def layout_quote(ctx, slide):
    style, p = ctx.style, ctx.palette
    x, w = M + 0.9, W - 2 * M - 1.8
    paragraphs = [Para(slide.quote, size=34, italic=style.quote_italic, font=style.heading_font,
                       color=p.title, space_after=24)]
    if slide.author:
        paragraphs.append(Para("— " + slide.author, size=18, bold=True))
    # quotation and author are one block: the author line always stays under the quotation
    quote = Text(x, 0, w, 4.0, paragraphs, font=style.body_font, size=18, color=p.text, line_spacing=1.1)
    quote = measured(fit(quote))
    # the decorative opening quotation mark is drawn in a serif font in every style
    mark = simple_text(x - 0.08, 0, 2.0, 1.15, "“", font="Georgia", size=120, bold=True, color=p.accent)
    items = style.decorate(ctx) + stack([(mark, 0.0), (quote, 0.0)], 0.9, 6.7)
    return SlideSpec(style.background(ctx), items)


def layout_timeline(ctx, slide):
    style, p = ctx.style, ctx.palette
    items, area = style.frame(ctx, slide.title)
    steps = slide.steps
    gap = 0.4
    col_w = (area.w - gap * (len(steps) - 1)) / len(steps)

    # Labels share one size. A label may take two lines, but a single word is never broken.
    def labels_fit(size):
        for s in steps:
            longest_word = max(s.label.split() or [""], key=len)
            if text_width(longest_word, style.heading_font, size, bold=True) > col_w * 0.96:
                return False
            if count_lines(s.label, style.heading_font, size, col_w, bold=True) > 2:
                return False
        return True

    label_size = 26
    while label_size > 12 and not labels_fit(label_size):
        label_size -= 1
    label_lines = max(count_lines(s.label, style.heading_font, label_size, col_w, bold=True) for s in steps)
    label_h = label_lines * label_size * line_height(style.heading_font) / POINTS_PER_INCH
    texts = [Text(0, 0, col_w, 0, [Para(s.text)], font=style.body_font, size=16, color=p.text,
                  line_spacing=1.05) for s in steps]
    # all step texts share one size: smaller if the longest does not fit, larger if there is room
    available = area.h - label_h - 1.0
    scale = min(best_scale(t, available, max_scale=1.3, fill=0.55) for t in texts)
    for t in texts:
        apply_scale(t, scale)
    text_h = min(max(text_height(t) for t in texts), available)

    dot = 0.24
    y = _vertical_start(area, label_h + 0.3 + dot + 0.3 + text_h)
    line_y = y + label_h + 0.3 + dot / 2
    items.append(rule(area.x, line_y - 0.015, area.w, p.line, 0.03))
    for i, (step, text) in enumerate(zip(steps, texts)):
        x = area.x + i * (col_w + gap)
        items.append(simple_text(x, y, col_w, label_h, step.label, font=style.heading_font, size=label_size,
                                 bold=True, color=p.title, valign="bottom"))
        items.append(Box(x, line_y - dot / 2, dot, dot, fill=p.accent, ellipse=True))
        text.x, text.y, text.h = x, line_y + dot / 2 + 0.3, text_h
        items.append(text)
    return SlideSpec(style.background(ctx), items)


def layout_table(ctx, slide):
    style, p = ctx.style, ctx.palette
    items, area = style.frame(ctx, slide.title)
    headers, rows = slide.table.headers, [row.cells for row in slide.table.rows]
    pad_x, pad_y = 0.2, 0.14
    font = style.body_font
    # Column widths follow the content: a column with long sentences gets more room than a
    # column with years. The limits keep any column from becoming a sliver or eating the table.
    weights = []
    for i, header in enumerate(headers):
        longest = max(text_width(text, font, 16, bold=True) for text in [header] + [cells[i] for cells in rows])
        weights.append(min(max(longest, 1.3), 4.2))
    widths = [area.w * weight / sum(weights) for weight in weights]

    def row_height(cells, size, all_bold=False):
        lines = max(count_lines(cell, font, size, widths[i] - 2 * pad_x, bold=all_bold or i == 0)
                    for i, cell in enumerate(cells))
        return lines * size * line_height(font) / POINTS_PER_INCH + 2 * pad_y

    # the largest text size at which the whole table fits into the area
    for size in range(20, 9, -1):
        header_h = max(row_height(headers, size, all_bold=True), 0.55)
        heights = [row_height(cells, size) for cells in rows]
        if header_h + sum(heights) <= area.h:
            break
    # a small table would huddle at the top: give its rows more breathing room (up to a limit)
    spare = area.h * 0.85 - (header_h + sum(heights))
    if spare > 0:
        extra = min(0.3, spare / (len(rows) + 1))
        header_h += extra
        heights = [h + extra for h in heights]

    header_ink = {"accent": p.on_accent, "deep": p.on_deep, "line": p.title}[style.table_header]
    y = area.y
    if style.table_header == "line":
        items.append(rule(area.x, y + header_h - 0.03, area.w, p.title, 0.03))
    else:
        items.append(Box(area.x, y, area.w, header_h, fill=p.accent if style.table_header == "accent" else p.deep))

    def draw_row(cells, y, h, color, bold_first, all_bold=False):
        x = area.x
        for i, cell in enumerate(cells):
            first = bold_first and i == 0
            items.append(simple_text(x + pad_x, y, widths[i] - 2 * pad_x, h, cell, font=font, size=size,
                                     bold=all_bold or first, color=p.title if first else color, valign="middle"))
            x += widths[i]

    draw_row(headers, y, header_h, header_ink, bold_first=False, all_bold=True)
    y += header_h
    for n, (cells, h) in enumerate(zip(rows, heights)):
        if n % 2 == 1:
            items.append(Box(area.x, y, area.w, h, fill=p.surface))    # zebra stripes
        draw_row(cells, y, h, p.text, bold_first=True)
        y += h
        items.append(rule(area.x, y - 0.012, area.w, p.line, 0.012))
    return SlideSpec(style.background(ctx), items)


def layout_chart(ctx, slide):
    style, p = ctx.style, ctx.palette
    items, area = style.frame(ctx, slide.title)
    chart = slide.chart
    colors = series_colors(p, len(chart.categories) if chart.kind == "pie" else len(chart.series))

    chart_w = area.w
    if slide.subtitle:
        # the main insight sits in a narrow column on the right, next to the chart
        side_w = 3.4
        chart_w = area.w - side_w - 0.6
        side_x = area.right - side_w
        insight = Text(side_x, 0, side_w, area.h * 0.8, [Para(slide.subtitle)], font=style.heading_font,
                       size=24, color=p.title, bold=style.heading_bold, line_spacing=1.05)
        insight = measured(fit(insight))
        items += stack([(Box(side_x, 0, 0.6, 0.06, fill=p.accent), 0.3), (insight, 0)], area.y, area.bottom)

    items.append(ChartShape(
        area.x, area.y, chart_w, area.h, kind=chart.kind, categories=chart.categories,
        series=[(s.name, s.values) for s in chart.series], colors=colors, text_color=p.text,
        grid_color=p.line, background=style.chart_background(ctx), font=style.body_font,
        font_size=14, unit=chart.unit or "",
    ))
    return SlideSpec(style.background(ctx), items)


def layout_statement(ctx, slide):
    style, p = ctx.style, ctx.palette
    # 8.9 in wide: the message never reaches the slide-number corner that some styles decorate
    x, w = M + 0.6, 8.9
    label = measured(Text(x, 0, w, 0, [Para(slide.title)], font=style.body_font, size=18, bold=True,
                          color=p.accent))
    message = heading(slide.subtitle, x, 0, w, style.heading_font, 52, p.title, bold=style.heading_bold,
                      max_lines=4, min_size=32)
    parts = [(label, 0.25), (Box(x, 0, 1.0, 0.07, fill=p.accent), 0.45), (message, 0)]
    return SlideSpec(style.background(ctx), style.decorate(ctx) + stack(parts, 1.9, 6.7))


def layout_agenda(ctx, slide):
    style, p = ctx.style, ctx.palette
    items, area = style.frame(ctx, slide.title)
    parts = slide.bullets
    columns = 2 if len(parts) > 4 else 1
    rows = math.ceil(len(parts) / columns)
    col_gap, row_gap = 0.8, 0.25
    col_w = (area.w - col_gap) / 2 if columns == 2 else min(area.w, 8.5)
    row_h = min(1.0, (area.h - row_gap * (rows - 1)) / rows)
    marker = min(0.66, row_h * 0.8)

    blocks = [Text(0, 0, col_w - marker - 0.35, row_h, [Para(part)], font=style.heading_font, size=24,
                   color=p.title, bold=style.heading_bold, valign="middle") for part in parts]
    scale = min(best_scale(block) for block in blocks)
    top = _vertical_start(area, rows * row_h + (rows - 1) * row_gap)
    for i, block in enumerate(blocks):
        x = area.x + (i // rows) * (col_w + col_gap)
        y = top + (i % rows) * (row_h + row_gap)
        items += _marker(ctx, x, y + (row_h - marker) / 2, marker, i + 1)
        block.x, block.y = x + marker + 0.35, y
        items.append(apply_scale(block, scale))
        if i % rows < rows - 1 and i < len(blocks) - 1:
            items.append(rule(block.x, y + row_h + row_gap / 2, block.w, p.line, 0.012))
    return SlideSpec(style.background(ctx), items)


def layout_section(ctx, slide):
    return ctx.style.cover(ctx, "section", slide.title, slide.subtitle or "")


def layout_closing(ctx, slide):
    return ctx.style.cover(ctx, "closing", slide.title, slide.subtitle or "", slide.bullets)


LAYOUTS = {
    "bullets": layout_bullets,
    "image": layout_image,
    "two_columns": layout_two_columns,
    "cards": layout_cards,
    "stats": layout_stats,
    "chart": layout_chart,
    "statement": layout_statement,
    "agenda": layout_agenda,
    "quote": layout_quote,
    "timeline": layout_timeline,
    "table": layout_table,
    "section": layout_section,
    "closing": layout_closing,
}


def build_specs(deck, style, palette, image_keys, credits=None):
    """Turn a whole Deck into slide descriptions: the title slide plus one per content slide.

    Speaker notes are the slide's own notes, followed by the photo credit (credits maps
    picture keys to an author line) on slides that show a photo.
    """
    credits = credits or {}
    total = len(deck.slides) + 1
    ctx = Ctx(palette=palette, style=style, number=1, total=total, deck_title=deck.title, images=set(image_keys))
    cover = style.cover(ctx, "title", deck.title, deck.subtitle)
    cover.notes = deck.notes or ""
    specs = [cover]
    seen = {}   # how many slides of each type were drawn so far: chooses the layout variant
    for i, slide in enumerate(deck.slides):
        ctx.number = i + 2
        ctx.variant = seen.get(slide.type, 0)
        seen[slide.type] = ctx.variant + 1
        spec = LAYOUTS[slide.type](ctx, slide)
        for item in spec.items:
            if isinstance(item, Picture) and not item.alt and not str(slide.image_keyword).startswith("upload-"):
                item.alt = slide.image_keyword or ""     # the photo search phrase describes the photo
        # speaker notes: what to say, then (if the slide shows a photo) who took the photo
        notes = [slide.notes] if slide.notes else []
        if _image_key(ctx, slide) and slide.type in ("bullets", "image") and credits.get(slide.image_keyword):
            notes.append(credits[slide.image_keyword])
        spec.notes = "\n\n".join(notes)
        specs.append(spec)
    return specs
