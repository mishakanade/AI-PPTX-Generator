"""Design styles: the "character" of a presentation, independent of its colours.

A style decides the fonts, how a slide title is presented, what decorates the
background, how a card or a photo looks, and how the cover slides are composed.
It never chooses colours itself: it takes them from the Palette, so every style
works with every colour theme.

Each style is a class with the same set of methods (see `Style`). The slide layouts
in render/layouts.py call these methods and never need to know which style is active.
To add a style: subclass `Style`, override what should differ, add it to STYLES.
"""
from generator.design.colors import WHITE, contrast, mix
from generator.render.layout_tools import MARGIN as M
from generator.render.layout_tools import Area, CardLook, heading, measured, rule, shorten, stack
from generator.render.primitives import SLIDE_H as H
from generator.render.primitives import SLIDE_W as W
from generator.render.primitives import Box, Gradient, Para, Picture, SlideSpec, Text
from generator.render.textfit import count_lines, simple_text


class Style:
    """Base style. Subclasses override attributes and methods to create their look."""
    key = "base"
    name = "Base"
    description = ""

    heading_font = "Calibri"
    body_font = "Calibri"
    heading_bold = True
    body_size = 20            # base size of body text, in points
    bullet_char = "•"
    image_radius = 0.0        # rounded photo corners, in inches
    image_bleed = False       # True: photos run to the slide edges instead of sitting in a frame
    quote_italic = False
    stats_emphasis = False    # True: number cards use the strong, filled variant
    table_header = "accent"   # "accent": filled header row, "line": bold text over a rule, "deep": dark band
    cover_title_size = 50

    # ----- pieces every content slide is assembled from ---------------------------------

    def background(self, ctx):
        return ctx.palette.bg

    def decorate(self, ctx):
        """Shapes behind the content of a regular slide: ornaments, footer, page number."""
        return []

    def frame(self, ctx, title, right=None):
        """Draw the slide title. Returns (items, area that is left for the content)."""
        raise NotImplementedError

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        """Draw one card and say where its text goes and in which colours."""
        raise NotImplementedError

    def image_frame(self, ctx, x, y, w, h, key):
        """Draw a photo inside the given rectangle."""
        return [Picture(x, y, w, h, key, radius=self.image_radius)]

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        """A full-slide composition. kind is "title", "section" or "closing"."""
        raise NotImplementedError

    # ----- helpers for subclasses ---------------------------------------------------------

    def page_number(self, ctx, color, x=None, y=H - 0.55, text=None):
        x = W - M - 2.0 if x is None else x
        return simple_text(x, y, 2.0, 0.3, text or f"{ctx.number:02d}", font=self.body_font,
                           size=11, color=color, align="right")

    def cover_text(self, ctx, kind, title, subtitle, bullets, x, w, title_color, sub_color,
                   text_color, bullet_color, align="left", bullet_marks=True):
        """Title, subtitle and (for the closing slide) takeaways as ONE text block.

        Keeping them in a single block matters: if the viewer's computer lacks the font and
        the title wraps differently, the lines below simply move down instead of overlapping.
        """
        size = round({"title": 1.0, "section": 0.86, "closing": 0.76}[kind] * self.cover_title_size)
        smallest = round(size * 0.68)
        while size > smallest and count_lines(title, self.heading_font, size, w, self.heading_bold) > 3:
            size -= 1
        paragraphs = [Para(title, size=size, bold=self.heading_bold, font=self.heading_font,
                           color=title_color, space_after=20)]
        if subtitle:
            paragraphs.append(Para(subtitle, size=22, color=sub_color, space_after=26))
        for bullet in bullets or []:
            paragraphs.append(Para(bullet, size=20, bullet=bullet_marks, space_after=10))
        return measured(Text(x, 0, w, 0, paragraphs, font=self.body_font, size=20, color=text_color,
                             align=align, bullet_char=self.bullet_char, bullet_color=bullet_color))


# ---------------------------------------------------------------------------------------
class Minimal(Style):
    key = "minimal"
    name = "Minimal"
    description = "Airy, thin lines, calm type"
    heading_bold = False
    table_header = "line"
    cover_title_size = 54

    def decorate(self, ctx):
        return [self.page_number(ctx, ctx.palette.muted)]

    def frame(self, ctx, title, right=None):
        p, right = ctx.palette, right or W - M
        t = heading(title, M, 0.62, right - M, self.heading_font, 32, p.title, bold=False)
        line_y = t.y + t.h + 0.18
        top = line_y + 0.5
        items = self.decorate(ctx) + [t, Box(M, line_y, 0.7, 0.045, fill=p.accent)]
        return items, Area(M, top, right - M, 6.75 - top)

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        p = ctx.palette
        box = Box(x, y, w, h, fill=None, line=p.line, line_width=1)
        return CardLook([box], Area(x + 0.3, y + 0.3, w - 0.6, h - 0.6), p.title, p.text, p.accent)

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        p = ctx.palette
        line_x = W - 3.4
        items = [Box(line_x, 0, 0.014, H, fill=p.line), Box(line_x - 0.075, H / 2 - 0.08, 0.16, 0.16, fill=p.accent)]
        parts = []
        if kind == "section":
            parts.append((simple_text(M, 0, 3, 0.35, f"{ctx.number:02d}", font=self.body_font, size=16,
                                      bold=True, color=p.accent), 0.3))
        parts.append((Box(M, 0, 0.9, 0.06, fill=p.accent), 0.45))
        parts.append((self.cover_text(ctx, kind, title, subtitle, bullets, M, line_x - M - 0.7,
                                      p.title, p.muted, p.text, p.accent), 0))
        items += stack(parts, 0.9, 6.6)
        if kind != "title":
            items.append(self.page_number(ctx, p.muted))
        return SlideSpec(self.background(ctx), items)


# ---------------------------------------------------------------------------------------
class Editorial(Style):
    key = "editorial"
    name = "Editorial"
    description = "Serif headlines, edge-to-edge photos"
    heading_font = "Georgia"
    bullet_char = "–"
    image_bleed = True
    quote_italic = True
    table_header = "line"
    cover_title_size = 52

    def _masthead(self, ctx, right, with_title=True):
        """The thin rule at the top with the slide number and the deck title under it."""
        p = ctx.palette
        items = [rule(M, 0.6, right - M, p.title, 0.025),
                 simple_text(M, 0.74, 1.5, 0.3, f"{ctx.number:02d}", font=self.body_font, size=12,
                             bold=True, color=p.accent)]
        if with_title:
            items.append(simple_text(right - 6.0, 0.74, 6.0, 0.3, shorten(ctx.deck_title, 58),
                                     font=self.body_font, size=11, color=p.muted, align="right"))
        return items

    def decorate(self, ctx):
        return self._masthead(ctx, W - M)

    def frame(self, ctx, title, right=None):
        p, right = ctx.palette, right or W - M
        t = heading(title, M, 1.25, right - M, self.heading_font, 34, p.title)
        top = t.y + t.h + 0.45
        return self._masthead(ctx, right) + [t], Area(M, top, right - M, 6.85 - top)

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        p = ctx.palette
        return CardLook([rule(x, y, w, p.title, 0.03)], Area(x, y + 0.28, w - 0.15, h - 0.28),
                        p.title, p.text, p.accent)

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        p = ctx.palette
        band_x = W - 3.6
        items = [Box(band_x, 0, W - band_x, H, fill=p.accent)]
        if kind == "section":
            items.append(simple_text(band_x, 0, W - band_x, H, f"{ctx.number:02d}", font=self.heading_font,
                                     size=110, bold=True, color=p.on_accent, align="center", valign="middle"))
        else:
            items.append(rule(band_x + 0.7, H - 1.2, 1.0, p.on_accent, 0.04))
        if kind != "title":
            items += self._masthead(ctx, band_x - 0.7, with_title=False)
        parts = [(rule(M, 0, 1.2, p.title, 0.045), 0.45)]
        parts.append((self.cover_text(ctx, kind, title, subtitle, bullets, M, band_x - M - 0.8,
                                      p.title, p.muted, p.text, p.accent), 0))
        items += stack(parts, 1.3, 6.7)
        return SlideSpec(self.background(ctx), items)


# ---------------------------------------------------------------------------------------
class Corporate(Style):
    key = "corporate"
    name = "Corporate"
    description = "Header band, solid colour blocks"
    heading_font = "Arial"
    body_font = "Arial"
    body_size = 18
    bullet_char = "▪"
    stats_emphasis = True
    table_header = "deep"
    cover_title_size = 42

    def decorate(self, ctx):
        p = ctx.palette
        return [
            rule(M, 6.98, W - 2 * M, p.line, 0.012),
            simple_text(M, 7.07, 8.0, 0.25, shorten(ctx.deck_title), font=self.body_font, size=10, color=p.muted),
            self.page_number(ctx, p.muted, y=7.07, text=f"{ctx.number} / {ctx.total}"),
        ]

    def frame(self, ctx, title, right=None):
        p, right = ctx.palette, right or W - M
        t = heading(title, M, 0, right - M, self.heading_font, 28, p.on_deep)
        band_h = max(1.25, t.h + 0.7)
        t.y = (band_h - t.h) / 2
        top = band_h + 0.5
        items = [Box(0, 0, W, band_h, fill=p.deep), Box(0, 0, 0.28, band_h, fill=p.accent), t]
        return items + self.decorate(ctx), Area(M, top, right - M, 6.65 - top)

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        p = ctx.palette
        inner = Area(x + 0.3, y + 0.37, w - 0.6, h - 0.67)
        if emphasis:
            items = [Box(x, y, w, h, fill=p.deep), Box(x, y, w, 0.07, fill=p.accent)]
            return CardLook(items, inner, p.on_deep, mix(p.on_deep, p.deep, 0.2), p.accent_on_deep)
        items = [Box(x, y, w, h, fill=p.surface), Box(x, y, w, 0.07, fill=p.accent)]
        return CardLook(items, inner, p.title, p.text, p.accent)

    def image_frame(self, ctx, x, y, w, h, key):
        # the photo sits on top of an accent block shifted down and to the right
        offset = 0.18
        return [Box(x + offset, y + offset, w - offset, h - offset, fill=ctx.palette.accent),
                Picture(x, y, w - offset, h - offset, key)]

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        p = ctx.palette
        split = 8.7
        items = [
            Box(0, 0, split, H, fill=p.deep),
            Box(split, 0, W - split, H, fill=p.accent),
            Box(split + 0.9, 2.5, 5.6, 5.6, fill=p.on_accent, alpha=0.10, ellipse=True),
            Box(split + 2.3, -1.5, 3.6, 3.6, fill=p.on_accent, alpha=0.08, ellipse=True),
            Box(split + 0.7, 0.8, 1.2, 1.2, fill=None, line=p.on_accent, line_width=2),
        ]
        if kind == "section":
            items.append(simple_text(split, 0, W - split, H, f"{ctx.number:02d}", font=self.heading_font,
                                     size=104, bold=True, color=p.on_accent, align="center", valign="middle"))
        parts = [(Box(M, 0, 1.0, 0.09, fill=p.accent_on_deep), 0.45)]
        parts.append((self.cover_text(ctx, kind, title, subtitle, bullets, M, split - M - 0.9, p.on_deep,
                                      mix(p.on_deep, p.deep, 0.28), p.on_deep, p.accent_on_deep), 0))
        items += stack(parts, 0.9, 6.6)
        return SlideSpec(p.bg, items)


# ---------------------------------------------------------------------------------------
class Soft(Style):
    key = "soft"
    name = "Soft"
    description = "Rounded cards, soft shadows"
    image_radius = 0.3
    cover_title_size = 48

    def background(self, ctx):
        return mix(ctx.palette.bg, ctx.palette.accent, 0.06)

    def _paper(self, ctx):
        """The colour of the cards: lighter than the slide, like a sheet of paper lying on it."""
        p = ctx.palette
        return mix(p.bg, WHITE, 0.10) if p.is_dark else mix(p.bg, WHITE, 0.8)

    def decorate(self, ctx):
        a = ctx.palette.accent
        return [Box(W - 2.9, -1.8, 4.4, 4.4, fill=a, alpha=0.10, ellipse=True),
                Box(-1.4, H - 1.8, 3.2, 3.2, fill=a, alpha=0.08, ellipse=True)]

    def frame(self, ctx, title, right=None):
        p, right = ctx.palette, right or W - M
        pill = [Box(M, 0.6, 1.25, 0.38, fill=p.accent_soft, radius=0.19),
                simple_text(M, 0.6, 1.25, 0.38, f"{ctx.number:02d} / {ctx.total:02d}", font=self.body_font,
                            size=11, bold=True, color=p.accent, align="center", valign="middle")]
        t = heading(title, M, 1.18, right - M, self.heading_font, 32, p.title)
        top = t.y + t.h + 0.42
        return self.decorate(ctx) + pill + [t], Area(M, top, right - M, 6.85 - top)

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        p = ctx.palette
        inner = Area(x + 0.35, y + 0.35, w - 0.7, h - 0.7)
        if emphasis:
            return CardLook([Box(x, y, w, h, fill=p.accent, radius=0.22, shadow=True)], inner,
                            p.on_accent, p.on_accent, p.on_accent)
        return CardLook([Box(x, y, w, h, fill=self._paper(ctx), radius=0.22, shadow=True)], inner,
                        p.title, p.text, p.accent)

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        p = ctx.palette
        card = Area(1.4, 1.05, W - 2.8, H - 2.1)
        items = [
            Box(W - 4.4, -2.2, 6.2, 6.2, fill=p.accent, alpha=0.13, ellipse=True),
            Box(-2.2, H - 3.2, 5.4, 5.4, fill=p.accent, alpha=0.10, ellipse=True),
            Box(0.9, 0.55, 1.1, 1.1, fill=p.accent, alpha=0.16, ellipse=True),
            Box(card.x, card.y, card.w, card.h, fill=self._paper(ctx), radius=0.45, shadow=True),
        ]
        x, w = card.x + 0.9, card.w - 1.8
        if kind == "section":
            tag = [(Box(W / 2 - 0.5, 0, 1.0, 0.42, fill=p.accent, radius=0.21), 0.4)]
        else:
            tag = [(Box(W / 2 - 0.45, 0, 0.9, 0.12, fill=p.accent, radius=0.06), 0.45)]
        parts = tag + [(self.cover_text(ctx, kind, title, subtitle, bullets, x, w, p.title, p.text,
                                        p.text, p.accent, align="center", bullet_marks=False), 0)]
        items += stack(parts, card.y + 0.5, card.bottom - 0.5)
        if kind == "section":
            pill = tag[0][0]
            items.append(simple_text(pill.x, pill.y, pill.w, pill.h, f"{ctx.number:02d}", font=self.body_font,
                                     size=13, bold=True, color=p.on_accent, align="center", valign="middle"))
        return SlideSpec(self.background(ctx), items)


# ---------------------------------------------------------------------------------------
class Bold(Style):
    key = "bold"
    name = "Bold"
    description = "Gradients, heavy headlines"
    heading_font = "Arial"
    image_bleed = True
    stats_emphasis = True
    cover_title_size = 56

    def background(self, ctx):
        p = ctx.palette
        return Gradient(p.bg, mix(p.bg, p.accent, 0.22), "diagonal")

    def _card_fill(self, ctx):
        p = ctx.palette
        return mix(p.bg, WHITE, 0.10) if p.is_dark else mix(p.bg, WHITE, 0.6)

    def _big_number(self, ctx, right):
        """The huge, pale slide number in the corner."""
        p = ctx.palette
        return simple_text(right - 3.0, 0.3, 3.0, 1.5, f"{ctx.number:02d}", font=self.heading_font, size=84,
                           bold=True, color=mix(p.bg, p.accent, 0.3), align="right")

    def decorate(self, ctx):
        return [self._big_number(ctx, W - M)]

    def frame(self, ctx, title, right=None):
        p = ctx.palette
        x = M + 0.38
        if right is None:
            # full-width slide: the big number sits in the corner, the title leaves room for it
            right = W - M
            decor = [self._big_number(ctx, right)]
            title_w = right - x - 2.3
        else:
            # a photo takes the right side: no number, the title may use the whole column
            decor = []
            title_w = right - x
        t = heading(title, x, 0.72, title_w, self.heading_font, 34, p.title)
        top = t.y + t.h + 0.55
        bar = Box(M, t.y + 0.06, 0.14, t.h - 0.1, fill=p.accent)
        return decor + [bar, t], Area(M, top, right - M, 6.85 - top)

    def card(self, ctx, x, y, w, h, index=0, emphasis=False):
        p = ctx.palette
        inner = Area(x + 0.42, y + 0.32, w - 0.72, h - 0.64)
        if emphasis:
            fill = Gradient(p.accent, mix(p.accent, p.deep, 0.35), "diagonal")
            return CardLook([Box(x, y, w, h, fill=fill)], inner, p.on_accent, p.on_accent, p.on_accent)
        items = [Box(x, y, w, h, fill=self._card_fill(ctx)), Box(x, y, 0.1, h, fill=p.accent)]
        return CardLook(items, inner, p.title, p.text, p.accent)

    def cover(self, ctx, kind, title, subtitle="", bullets=None):
        p = ctx.palette
        end = mix(p.accent, p.deep, 0.4)
        # the text colour has to stay readable across the whole gradient
        ink = max((WHITE, (22, 24, 30)), key=lambda c: min(contrast(c, p.accent), contrast(c, end)))
        items = [
            Box(W - 5.6, -2.3, 7.0, 7.0, fill=ink, alpha=0.07, ellipse=True),
            Box(W - 3.3, 3.5, 5.2, 5.2, fill=ink, alpha=0.06, ellipse=True),
        ]
        if kind == "section":
            items.append(simple_text(W - M - 4.0, 0.5, 4.0, 2.3, f"{ctx.number:02d}", font=self.heading_font,
                                     size=130, bold=True, color=mix(p.accent, ink, 0.3), align="right"))
        # the text is pinned to the bottom of its box and grows upwards; the bar sits under it
        text = self.cover_text(ctx, kind, title, subtitle, bullets, M, 9.4, ink,
                               mix(ink, p.accent, 0.15), ink, ink)
        text.y, text.h, text.valign = 0.9, H - 2.45, "bottom"
        items += [text, Box(M, H - 1.15, 1.6, 0.12, fill=ink)]
        return SlideSpec(Gradient(p.accent, end, "diagonal"), items)


STYLES = {style.key: style for style in (Minimal(), Editorial(), Corporate(), Soft(), Bold())}
DEFAULT_STYLE = "minimal"
