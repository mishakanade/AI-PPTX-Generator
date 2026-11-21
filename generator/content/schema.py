"""The shape of a presentation: which slide types exist and which fields each one has.

These classes do two jobs:
  1. They are sent to Gemini as the required answer format, so the model cannot return
     a field or a slide type that the renderer does not know.
  2. The answer is checked against them (`parse_deck`), and anything that is still
     unusable (a "cards" slide without cards, 9 columns in a table...) is repaired or
     turned into a plain bullet slide by `normalize_deck`, so the renderer can trust the data.
"""
import json
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

SlideType = Literal[
    "bullets", "image", "two_columns", "cards", "stats", "chart", "quote", "statement", "timeline", "table",
    "agenda", "section", "closing",
]

# One line per type for the prompt: when to use it and which fields to fill.
SLIDE_TYPE_GUIDE = {
    "bullets": 'Default explanatory slide. Fill "bullets" and "image_keyword".',
    "image": 'A strong visual moment: a full-screen photo with a short statement. Fill "subtitle" (one sentence) and "image_keyword".',
    "two_columns": 'Comparison or two sides of one idea (before/after, pros/cons, A vs B). Fill "columns" with exactly 2 items.',
    "cards": 'Several parallel ideas of equal weight (features, principles, reasons). Fill "cards" with 2-4 items.',
    "stats": 'Key numbers. Fill "stats" with 2-4 items; "value" is a short figure like "73%" or "4.2M", "label" explains it. Only use numbers that are real and that you are confident about.',
    "chart": 'Numbers that are easier to see than to read: a trend, a comparison or shares of a whole. Fill "chart": "kind" is "column", "bar", "line" or "pie"; 2-8 "categories"; 1-3 "series", each with a "name" and exactly one number in "values" per category (pie: exactly one series). Put the unit (such as "%" or "bn $") in "unit", not in the numbers. Only real data you are confident about. Optionally put the main insight in "subtitle" (one sentence).',
    "quote": 'One memorable quotation. Fill "quote" and "author". Only use a real, correctly attributed quotation.',
    "statement": 'One key message in very large type, a pause between denser slides. "title" is a 1-3 word label such as "Key idea", "subtitle" is the message itself: one sentence of up to 15 words.',
    "timeline": 'Chronology or a step-by-step process. Fill "steps" with 3-5 items; "label" is a year or a short step name.',
    "table": 'Compact structured data. Fill "table" with 2-4 headers and 2-5 rows; every row has one cell per header.',
    "agenda": 'Table of contents, placed right after the title slide. Fill "bullets" with the 3-6 parts of the presentation, 1-5 words each.',
    "section": 'Divider that opens a new part of a long presentation. Fill only "title" and "subtitle".',
    "closing": 'Final slide with conclusions. Fill "bullets" with 2-4 key takeaways.',
}


class Column(BaseModel):
    heading: str = Field(description="Short column heading")
    bullets: List[str] = Field(description="2-4 short points")


class Card(BaseModel):
    heading: str = Field(description="2-4 word heading")
    text: str = Field(description="One or two sentences")


class Stat(BaseModel):
    value: str = Field(description='A short figure such as "73%", "4.2M" or "1969"')
    label: str = Field(description="What the figure means, up to 8 words")


class Step(BaseModel):
    label: str = Field(description="A year or a short step name, 1-3 words")
    text: str = Field(description="One short sentence")


class ChartSeries(BaseModel):
    name: str = Field(description="What this series measures, e.g. a year or a country")
    values: List[float] = Field(description="Exactly one number per category, without units")


class Chart(BaseModel):
    kind: Literal["column", "bar", "line", "pie"]
    categories: List[str]
    series: List[ChartSeries]
    unit: Optional[str] = Field(default=None, description='Unit of the numbers, such as "%" or "bn $"')


class TableRow(BaseModel):
    cells: List[str]


class Table(BaseModel):
    headers: List[str]
    rows: List[TableRow]


class Slide(BaseModel):
    type: SlideType
    title: str = Field(description="Slide title, up to 8 words")
    subtitle: Optional[str] = None
    bullets: Optional[List[str]] = None
    image_keyword: Optional[str] = Field(
        default=None, description="2-4 English words naming something that can be photographed"
    )
    columns: Optional[List[Column]] = None
    cards: Optional[List[Card]] = None
    stats: Optional[List[Stat]] = None
    steps: Optional[List[Step]] = None
    quote: Optional[str] = None
    author: Optional[str] = None
    table: Optional[Table] = None
    chart: Optional[Chart] = None
    data_ref: Optional[str] = Field(
        default=None, description='Id of a prepared chart built from the user\'s data, e.g. "D1"; only when offered'
    )
    notes: Optional[str] = Field(
        default=None, description="What the presenter says on this slide: 2-4 sentences, not a copy of the slide"
    )


class Deck(BaseModel):
    title: str
    subtitle: str
    slides: List[Slide]
    notes: Optional[str] = Field(default=None, description="What the presenter says on the title slide")


class OutlineSlide(BaseModel):
    type: SlideType
    title: str = Field(description="Slide title, up to 8 words")
    focus: Optional[str] = Field(default=None, description="What the slide will say, one sentence")


class Outline(BaseModel):
    """The plan of a presentation: one line per slide, before any slide is written."""
    title: str
    subtitle: str
    slides: List[OutlineSlide]


class ContentError(Exception):
    """The model's answer could not be turned into a presentation. The message is shown to the user."""


# ---------------------------------------------------------------------------
# Reading and repairing the model's answer
# ---------------------------------------------------------------------------

def _clean(text):
    return " ".join(str(text or "").split())


def _clean_list(items, limit):
    cleaned = [_clean(item) for item in (items or [])]
    return [item for item in cleaned if item][:limit]


def _as_bullets(slide):
    """Collect whatever text a slide has into a flat list, used when its own layout cannot be built."""
    lines = list(slide.bullets or [])
    for column in slide.columns or []:
        lines.append(column.heading)
        lines.extend(column.bullets)
    lines += [f"{card.heading}: {card.text}" for card in slide.cards or []]
    lines += [f"{stat.value} — {stat.label}" for stat in slide.stats or []]
    lines += [f"{step.label}: {step.text}" for step in slide.steps or []]
    if slide.quote:
        lines.append(f"“{slide.quote}”" + (f" — {slide.author}" if slide.author else ""))
    if slide.chart:
        unit = f" {slide.chart.unit}" if slide.chart.unit else ""
        first = slide.chart.series[0].values if slide.chart.series else []
        lines += [f"{name}: {value:g}{unit}" for name, value in zip(slide.chart.categories, first)]
    if slide.table:
        lines += [" · ".join(row.cells) for row in slide.table.rows]
    if slide.subtitle:
        lines.append(slide.subtitle)
    return _clean_list(lines, 6)


def _normalize_slide(slide):
    """Return a copy of the slide that is guaranteed to have what its layout needs."""
    data = {
        "type": slide.type,
        "title": _clean(slide.title) or "Slide",
        "subtitle": _clean(slide.subtitle) or None,
        "image_keyword": _clean(slide.image_keyword) or None,
        "notes": _clean(slide.notes) or None,
    }
    kind = slide.type

    if kind == "two_columns":
        columns = [
            Column(heading=_clean(c.heading), bullets=_clean_list(c.bullets, 5))
            for c in (slide.columns or [])[:2]
        ]
        if len(columns) == 2 and all(c.bullets for c in columns):
            return Slide(**data, columns=columns)
    elif kind == "cards":
        cards = [Card(heading=_clean(c.heading), text=_clean(c.text)) for c in (slide.cards or [])[:4]]
        cards = [c for c in cards if c.heading or c.text]
        if len(cards) >= 2:
            return Slide(**data, cards=cards)
    elif kind == "stats":
        stats = [Stat(value=_clean(s.value), label=_clean(s.label)) for s in (slide.stats or [])[:4]]
        stats = [s for s in stats if s.value]
        if len(stats) >= 2:
            return Slide(**data, stats=stats)
    elif kind == "timeline":
        steps = [Step(label=_clean(s.label), text=_clean(s.text)) for s in (slide.steps or [])[:5]]
        steps = [s for s in steps if s.label or s.text]
        if len(steps) >= 3:
            return Slide(**data, steps=steps)
    elif kind == "quote":
        if _clean(slide.quote):
            return Slide(**data, quote=_clean(slide.quote).strip("\"“”«»"), author=_clean(slide.author) or None)
    elif kind == "table":
        table = slide.table
        headers = _clean_list(table.headers, 4) if table else []
        if len(headers) >= 2:
            rows = []
            for row in table.rows[:5]:
                # every row gets exactly one cell per header: extra cells are cut, missing ones are empty
                cells = [_clean(cell) for cell in row.cells[:len(headers)]]
                cells += [""] * (len(headers) - len(cells))
                if any(cells):
                    rows.append(TableRow(cells=cells))
            if len(rows) >= 2:
                return Slide(**data, table=Table(headers=headers, rows=rows))
    elif kind == "chart" and _clean(slide.data_ref):
        # a chart from the user's data: its numbers are filled in later by data.bind_data_charts
        return Slide(**data, data_ref=_clean(slide.data_ref).upper())
    elif kind == "chart" and slide.chart:
        chart = _normalize_chart(slide.chart)
        if chart:
            return Slide(**data, chart=chart)
    elif kind == "statement":
        statement = data["subtitle"] or (_clean_list(slide.bullets, 1) or [None])[0]
        if statement:
            return Slide(**{**data, "subtitle": statement})
    elif kind == "agenda":
        parts = _clean_list(slide.bullets, 6)
        if len(parts) >= 2:
            return Slide(**data, bullets=parts)
    elif kind == "image":
        return Slide(**data)
    elif kind == "section":
        return Slide(**data)
    elif kind == "closing":
        return Slide(**data, bullets=_clean_list(slide.bullets, 4) or None)
    elif kind == "bullets" and _clean_list(slide.bullets, 7):
        return Slide(**data, bullets=_clean_list(slide.bullets, 7))

    # The slide lacks what its type needs: show its text as plain bullets instead.
    bullets = _as_bullets(slide)
    if bullets:
        return Slide(**{**data, "type": "bullets", "subtitle": None}, bullets=bullets)
    return Slide(**{**data, "type": "section"})


def _normalize_chart(chart):
    """Return a chart whose series all have one value per category, or None if that is impossible."""
    categories = _clean_list(chart.categories, 8)
    series = [s for s in chart.series if s.values][: 1 if chart.kind == "pie" else 3]
    if not categories or not series:
        return None
    # cut everything to the shortest list: a missing value must not be invented
    count = min([len(categories)] + [len(s.values) for s in series])
    if count < 2:
        return None
    series = [ChartSeries(name=_clean(s.name) or f"Series {i + 1}", values=list(s.values[:count]))
              for i, s in enumerate(series)]
    if chart.kind == "pie" and (any(v < 0 for v in series[0].values) or sum(series[0].values) <= 0):
        return None
    unit = _clean(chart.unit)[:12] or None
    return Chart(kind=chart.kind, categories=categories[:count], series=series, unit=unit)


def normalize_deck(deck):
    """Repair a deck so that every slide can be drawn by its layout."""
    return Deck(
        title=_clean(deck.title) or "Presentation",
        subtitle=_clean(deck.subtitle),
        notes=_clean(deck.notes) or None,
        slides=[_normalize_slide(slide) for slide in deck.slides],
    )


def _repair_chart_numbers(chart):
    """Turn chart values like "12,5%" into 12.5 (only needed when the strict schema was not used)."""
    if not isinstance(chart, dict):
        return
    for series in chart.get("series") or []:
        if not isinstance(series, dict) or not isinstance(series.get("values"), list):
            continue
        numbers = []
        for value in series["values"]:
            if isinstance(value, str):
                match = re.search(r"-?\d[\d\s]*(?:[.,]\d+)?", value)
                if not match:
                    break       # one unreadable value: keep the numbers before it
                value = float(match.group(0).replace(" ", "").replace(",", "."))
            numbers.append(value)
        series["values"] = numbers


def parse_deck(raw_text):
    """Turn the model's text answer into a checked and repaired Deck.

    Raises ContentError when the answer is not a presentation at all.
    """
    # Take the outermost {...}: models sometimes wrap JSON in explanations or code fences.
    match = re.search(r"\{.*\}", raw_text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0) if match else raw_text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ContentError("The model returned an answer that is not valid JSON. Please try again.") from e

    # Small repairs for answers produced without the strict schema.
    if isinstance(data, dict):
        data.setdefault("title", "")
        data.setdefault("subtitle", "")
    for slide in data.get("slides", []) if isinstance(data, dict) else []:
        if isinstance(slide, dict):
            slide.setdefault("title", "")
            if slide.get("type") not in SLIDE_TYPE_GUIDE:
                slide["type"] = "bullets"
            if "bullets" not in slide and isinstance(slide.get("content"), list):
                slide["bullets"] = slide["content"]
            _repair_chart_numbers(slide.get("chart"))

    try:
        deck = Deck.model_validate(data)
    except ValidationError as e:
        raise ContentError("The model returned a presentation in an unexpected format. Please try again.") from e

    deck = normalize_deck(deck)
    if not deck.slides:
        raise ContentError("The model returned a presentation without slides. Please try again.")
    return deck


def parse_slide(raw_text):
    """Turn the model's answer for a single slide into a checked and repaired Slide.

    The slide goes through exactly the same checks as a slide of a whole presentation.
    Raises ContentError when the answer is not a slide at all.
    """
    match = re.search(r"\{.*\}", raw_text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0) if match else raw_text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ContentError("The model returned an answer that is not valid JSON. Please try again.") from e
    if not isinstance(data, dict):
        raise ContentError("The model returned a slide in an unexpected format. Please try again.")
    return parse_deck(json.dumps({"title": "", "subtitle": "", "slides": [data]})).slides[0]


def parse_outline(raw_text):
    """Turn the model's plan into a checked Outline (unknown types become "bullets").

    Raises ContentError when the answer is not a plan at all.
    """
    match = re.search(r"\{.*\}", raw_text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0) if match else raw_text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ContentError("The model returned an answer that is not valid JSON. Please try again.") from e
    if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
        raise ContentError("The model returned a plan in an unexpected format. Please try again.")
    slides = []
    for item in data["slides"][:25]:
        if not isinstance(item, dict) or not _clean(item.get("title")):
            continue
        kind = item.get("type") if item.get("type") in SLIDE_TYPE_GUIDE else "bullets"
        slides.append(OutlineSlide(type=kind, title=_clean(item["title"]), focus=_clean(item.get("focus")) or None))
    if not slides:
        raise ContentError("The model returned a plan without slides. Please try again.")
    return Outline(title=_clean(data.get("title")) or "Presentation", subtitle=_clean(data.get("subtitle")),
                   slides=slides)
