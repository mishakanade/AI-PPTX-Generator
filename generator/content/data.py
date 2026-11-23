"""The user's own data: tables from CSV or Excel files turned into charts with the real numbers.

The model never types the numbers of these charts. The app reads the tables, prepares a
"menu" of possible charts (D1, D2, ...), and shows the model the data and the menu. A chart
slide only names the menu item (data_ref = "D2") and writes the title and the insight;
bind_data_charts() then fills the chart from the table itself. A wrong number from the
model can therefore never reach a chart.
"""
import io
import re
from dataclasses import dataclass, field

import pandas as pd

from generator.content.schema import Chart, ChartSeries, Slide

MAX_CATEGORIES = 8        # what a chart slide can show (see schema._normalize_chart)
MAX_SERIES = 3
PROMPT_ROWS = 40          # rows of each table shown to the model
MONTHS = ("jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
          "янв|фев|мар|апр|май|мая|июн|июл|авг|сен|окт|ноя|дек")
# years, quarters ("Q3", "2024 Q1"), year-month ("2024-03") and month names ("March 2024", "мар 24")
TIME_LIKE = re.compile(rf"^(\d{{4}}|q[1-4]|\d{{4}}[-/ ]?(q[1-4]|\d{{1,2}})|({MONTHS})[a-zа-я]*\.?\s?\d{{0,4}})$",
                       re.IGNORECASE)


class DataError(Exception):
    """A data file could not be read. The message is shown to the user."""


@dataclass
class Table:
    name: str                  # file name, plus the sheet name for Excel workbooks
    frame: pd.DataFrame        # first column: labels; the other columns: numbers


@dataclass
class ChartOption:
    id: str                    # "D1", "D2", ... - what a slide puts into data_ref
    title: str                 # what the chart shows, for the model
    chart: Chart               # ready to draw, with the real numbers
    note: str = ""             # e.g. "the 8 largest of 15 rows"
    columns: list[str] = field(default_factory=list)


# ----- reading -------------------------------------------------------------------------------

def _clean(frame, name):
    """Keep a label column and the numeric columns; numbers like '1 234,5' or '12%' are understood."""
    frame = frame.dropna(how="all").dropna(axis=1, how="all")
    if frame.shape[1] < 2 or frame.shape[0] < 2:
        return None
    frame.columns = [str(c).strip() or f"column {i + 1}" for i, c in enumerate(frame.columns)]
    label_column = frame.columns[0]
    result = pd.DataFrame({label_column: frame[label_column].astype(str).str.strip()})
    for column in frame.columns[1:]:
        values = frame[column]
        if not pd.api.types.is_numeric_dtype(values):      # text cells: "1 234,5", "12%"
            values = (values.astype(str).str.replace(" ", "", regex=False).str.replace(" ", "", regex=False)
                      .str.replace("%", "", regex=False).str.replace(",", ".", regex=False))
        numbers = pd.to_numeric(values, errors="coerce")
        if numbers.notna().mean() >= 0.8:        # a column is numeric when most of its cells are numbers
            result[column] = numbers
    if result.shape[1] < 2:
        return None
    result = result.dropna(subset=list(result.columns[1:]), how="all").reset_index(drop=True)
    return Table(name=name, frame=result) if len(result) >= 2 else None


def read_tables(file_name, content):
    """All usable tables in one uploaded file (CSV, or every sheet of an Excel workbook)."""
    lower = file_name.lower()
    try:
        if lower.endswith((".xlsx", ".xlsm")):
            sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)
            raw = [(f"{file_name} / {sheet}" if len(sheets) > 1 else file_name, frame)
                   for sheet, frame in sheets.items()]
        elif lower.endswith((".csv", ".txt")):
            text = content.decode("utf-8-sig", errors="ignore")
            # ";" is the usual separator where "," is the decimal mark (Russian Excel, for example)
            separator = ";" if text.count(";") > text.count(",") else ","
            raw = [(file_name, pd.read_csv(io.StringIO(text), sep=separator))]
        else:
            raise DataError(f"Unsupported data file: {file_name}. Use CSV or XLSX.")
    except DataError:
        raise
    except Exception as e:
        raise DataError(f"Could not read {file_name}: {e}") from e
    tables = [table for name, frame in raw if (table := _clean(frame, name))]
    if not tables:
        raise DataError(f"No table with a label column and number columns was found in {file_name}.")
    return tables


# ----- the chart menu ------------------------------------------------------------------------

def _kind(labels, values):
    """Line for time, doughnut for shares of a whole, bars for long labels, columns otherwise."""
    if sum(bool(TIME_LIKE.match(label.strip())) for label in labels) >= len(labels) * 0.7:
        return "line"
    if values and all(v >= 0 for v in values) and 95 <= sum(values) <= 105 and len(labels) <= 8:
        return "pie"
    if max(len(label) for label in labels) > 14:
        return "bar"
    return "column"


def chart_options(tables):
    """The menu: one chart per numeric column, plus one combined chart when a table has 2-3 of them."""
    options = []

    def add(title, frame, columns, table):
        labels = frame.iloc[:, 0].tolist()
        first = frame[columns[0]].fillna(0).tolist()
        kind = _kind(labels, first) if len(columns) == 1 else (
            "line" if _kind(labels, first) == "line" else "column")
        note = ""
        if len(frame) > MAX_CATEGORIES:
            if kind == "line":
                frame, note = frame.tail(MAX_CATEGORIES), f"the last {MAX_CATEGORIES} of {len(labels)} rows"
            else:
                frame = frame.sort_values(columns[0], ascending=False).head(MAX_CATEGORIES)
                note = f"the {MAX_CATEGORIES} largest of {len(labels)} rows"
            if kind == "pie":
                kind = "column"
        chart = Chart(kind=kind, categories=frame.iloc[:, 0].tolist(),
                      series=[ChartSeries(name=c, values=[float(v) for v in frame[c].fillna(0)]) for c in columns])
        options.append(ChartOption(id=f"D{len(options) + 1}", title=title, chart=chart, note=note, columns=columns))

    for table in tables:
        frame = table.frame
        numeric = list(frame.columns[1:])
        for column in numeric:
            add(f"{column} by {frame.columns[0]} ({table.name})", frame, [column], table)
        if 2 <= len(numeric) <= MAX_SERIES:
            add(f"{', '.join(numeric)} by {frame.columns[0]} ({table.name})", frame, numeric, table)
    return options


def describe_for_prompt(tables, options):
    """The data and the chart menu, as text for the prompt."""
    lines = ["YOUR DATA (the user's own tables; quote numbers exactly as they appear here):"]
    for table in tables:
        shown = table.frame.head(PROMPT_ROWS)
        lines += [f"Table \"{table.name}\" ({len(table.frame)} rows):", shown.to_csv(index=False).strip()]
        if len(table.frame) > PROMPT_ROWS:
            lines.append(f"... {len(table.frame) - PROMPT_ROWS} more rows not shown")
        lines.append("")
    lines.append("PREPARED CHARTS (built from the tables above):")
    for option in options:
        extra = f"; shows {option.note}" if option.note else ""
        lines.append(f"  {option.id}: {option.title} ({option.chart.kind} chart{extra})")
    lines += [
        "",
        'For every chart about this data use a "chart" slide with "data_ref" set to the id of a prepared '
        'chart (for example "D1") and leave "chart" empty: the numbers are filled in from the data. '
        'Put the insight the chart supports into "subtitle". Use the most telling 1-3 prepared charts.',
    ]
    return "\n".join(lines)


def bind_data_charts(deck, options):
    """Fill chart slides that name a prepared chart with the real data. Returns a new deck.

    A chart slide that names an unknown chart and has no chart of its own becomes a bullet
    slide with its insight, so nothing empty is ever drawn.
    """
    by_id = {option.id: option for option in options}
    slides = []
    for slide in deck.slides:
        if slide.data_ref and slide.data_ref in by_id:
            slide = slide.model_copy(update={"type": "chart", "chart": by_id[slide.data_ref].chart})
        elif slide.type == "chart" and slide.chart is None:
            text = slide.subtitle or slide.title
            slide = Slide(type="bullets", title=slide.title, bullets=[text], notes=slide.notes,
                          image_keyword=slide.image_keyword)
        slides.append(slide)
    return deck.model_copy(update={"slides": slides})
