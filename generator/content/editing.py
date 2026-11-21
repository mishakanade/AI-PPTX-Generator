"""Editing a generated presentation as plain text, without asking the model again.

Every slide type is shown to the user as a title plus one text box in a simple line format:

    bullets, closing, agenda     one item per line
    cards                        Heading — text          (one card per line)
    stats                        73% — what it means     (one figure per line)
    timeline                     1969 — what happened    (one step per line)
    two_columns                  # Column heading, then its points; a blank line between columns
    table                        cells separated by |, the first line holds the headers
    quote                        the quotation (the author has a field of its own)
    image, statement, section,   one sentence (the subtitle; for a chart, the insight next to it;
    chart                        the chart's numbers are edited in PowerPoint after download)

slide_to_text() produces that text, apply_text() reads it back. The result goes through the
same repair step as the model's answer, so an edit can never produce a slide that cannot be drawn.
The names of the slide types and the hints shown next to the text box are in ui_text.py.
"""
import re

from generator.content.schema import (
    Card, Column, Deck, Slide, Stat, Step, Table, TableRow, normalize_deck,
)

# "Heading — text": a dash with spaces around it separates the two parts. Without the spaces it
# is part of the text, so "1961–1963" or "5-7%" stay whole.
_PAIR = re.compile(r"\s+[—–-]\s+")

def _lines(text):
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _pair(line):
    parts = _PAIR.split(line, maxsplit=1)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (line.strip(), "")


def slide_to_text(slide):
    """The main text of a slide in the line format described above."""
    kind = slide.type
    if kind in ("bullets", "closing", "agenda"):
        return "\n".join(slide.bullets or [])
    if kind == "cards":
        return "\n".join(f"{c.heading} — {c.text}" for c in slide.cards or [])
    if kind == "stats":
        return "\n".join(f"{s.value} — {s.label}" for s in slide.stats or [])
    if kind == "timeline":
        return "\n".join(f"{s.label} — {s.text}" for s in slide.steps or [])
    if kind == "two_columns":
        return "\n\n".join("\n".join([f"# {c.heading}"] + c.bullets) for c in slide.columns or [])
    if kind == "table" and slide.table:
        return "\n".join(" | ".join(row) for row in [slide.table.headers] + [r.cells for r in slide.table.rows])
    if kind == "quote":
        return slide.quote or ""
    return slide.subtitle or ""


def _columns(text):
    columns, current = [], None
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            current = Column(heading=line.lstrip("#").strip(), bullets=[])
            columns.append(current)
        elif line:
            if current is None:
                current = Column(heading="", bullets=[])
                columns.append(current)
            current.bullets.append(line)
        elif current is not None and current.bullets:
            current = None            # a blank line closes the column
    return columns


def apply_text(slide, title, text, author=None):
    """A copy of the slide with the edited title and text. The type, photo and notes are kept."""
    fields = {"type": slide.type, "title": title, "image_keyword": slide.image_keyword, "notes": slide.notes}
    kind, lines = slide.type, _lines(text)
    if kind in ("bullets", "closing", "agenda"):
        fields["bullets"] = lines
    elif kind == "cards":
        fields["cards"] = [Card(heading=h, text=t) for h, t in map(_pair, lines)]
    elif kind == "stats":
        fields["stats"] = [Stat(value=v, label=label) for v, label in map(_pair, lines)]
    elif kind == "timeline":
        fields["steps"] = [Step(label=label, text=t) for label, t in map(_pair, lines)]
    elif kind == "two_columns":
        fields["columns"] = _columns(text)
    elif kind == "table":
        rows = [[cell.strip() for cell in line.split("|")] for line in lines]
        if rows:
            fields["table"] = Table(headers=rows[0], rows=[TableRow(cells=r) for r in rows[1:]])
    elif kind == "quote":
        fields["quote"] = " ".join(lines)
        fields["author"] = author
    else:
        fields["subtitle"] = " ".join(lines)
        if kind == "chart":
            fields["chart"] = slide.chart
    return Slide(**fields)


def apply_edits(deck, title, subtitle, edits):
    """Build the edited deck.

    edits is a list with one entry per slide: None to delete the slide, or a tuple
    (title, text, author) with the new contents. The result is repaired like a model answer.
    """
    slides = [apply_text(slide, *edit) for slide, edit in zip(deck.slides, edits) if edit is not None]
    return normalize_deck(Deck(title=title, subtitle=subtitle, notes=deck.notes, slides=slides))
