"""The user's own data turned into charts (generator/content/data.py)."""
import io
import json

import pandas as pd
import pytest

from generator.content.data import (
    DataError, bind_data_charts, chart_options, describe_for_prompt, read_tables,
)
from generator.content.schema import parse_deck

FINANCE_RU = "Год;Выручка, млн ₽;Прибыль, млн ₽\n2019;120,5;10\n2020;98;-4\n2021;140;15\n2022;175,2;22\n".encode()
SHARES = b"Mode,Share %\nWalking,31\nPublic transport,28\nCar,30\nBicycle,11\n"


def option(options, kind):
    return next(o for o in options if o.chart.kind == kind)


def test_russian_csv_with_decimal_commas_and_semicolons():
    table = read_tables("finance.csv", FINANCE_RU)[0]
    assert list(table.frame.columns) == ["Год", "Выручка, млн ₽", "Прибыль, млн ₽"]
    assert table.frame["Выручка, млн ₽"].tolist() == [120.5, 98.0, 140.0, 175.2]


def test_chart_kinds_are_chosen_from_the_data():
    options = chart_options(read_tables("finance.csv", FINANCE_RU) + read_tables("modes.csv", SHARES))
    by_title = {o.title.split(" (")[0]: o for o in options}
    assert by_title["Выручка, млн ₽ by Год"].chart.kind == "line"              # years: a trend
    assert by_title["Share % by Mode"].chart.kind == "pie"                    # shares adding up to 100
    combined = by_title["Выручка, млн ₽, Прибыль, млн ₽ by Год"].chart
    assert len(combined.series) == 2
    assert [o.id for o in options] == [f"D{i}" for i in range(1, len(options) + 1)]


def test_long_tables_are_cut_sensibly():
    rows = "\n".join(f"Region number {i},{i * 10}" for i in range(1, 16))
    options = chart_options(read_tables("regions.csv", ("Region,Sales\n" + rows).encode()))
    chart = options[0].chart
    assert chart.kind == "bar" and len(chart.categories) == 8          # long labels: horizontal bars
    assert chart.series[0].values[0] == 150.0 and "8 largest of 15" in options[0].note

    years = "\n".join(f"{2000 + i},{i}" for i in range(15))
    trend = chart_options(read_tables("trend.csv", ("Year,Value\n" + years).encode()))[0]
    assert trend.chart.kind == "line" and trend.chart.categories[-1] == "2014" and "last 8" in trend.note


def test_excel_workbooks_with_several_sheets():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"City": ["A", "B", "C"], "Trips": [5, 7, 9]}).to_excel(writer, sheet_name="Trips", index=False)
        pd.DataFrame({"Note": ["x", "y"]}).to_excel(writer, sheet_name="Notes", index=False)   # no numbers
    tables = read_tables("data.xlsx", buffer.getvalue())
    assert [t.name for t in tables] == ["data.xlsx / Trips"]


@pytest.mark.parametrize("name, content", [
    ("notes.csv", b"a,b\nx,y\nz,w\n"),          # no number column
    ("slides.pptx", b"whatever"),               # wrong kind of file
])
def test_unusable_files_raise_a_clear_error(name, content):
    with pytest.raises(DataError):
        read_tables(name, content)


def test_charts_always_show_the_real_numbers():
    options = chart_options(read_tables("finance.csv", FINANCE_RU))
    answer = {"title": "T", "subtitle": "", "slides": [
        # the model names the chart and even invents numbers of its own: they must be replaced
        {"type": "chart", "title": "Revenue keeps growing", "subtitle": "Up 45% in 3 years", "data_ref": "d1",
         "chart": {"kind": "column", "categories": ["a", "b"], "series": [{"name": "x", "values": [1, 2]}]}},
        {"type": "chart", "title": "Unknown chart", "subtitle": "An insight", "data_ref": "D99"},
    ]}
    deck = bind_data_charts(parse_deck(json.dumps(answer)), options)
    first, second = deck.slides
    assert first.type == "chart" and first.chart.series[0].values == [120.5, 98.0, 140.0, 175.2]
    assert first.title == "Revenue keeps growing"                     # the model's words are kept
    assert second.type == "bullets" and second.bullets == ["An insight"]   # nothing empty is drawn


def test_the_prompt_shows_the_data_and_the_menu():
    tables = read_tables("finance.csv", FINANCE_RU)
    text = describe_for_prompt(tables, chart_options(tables))
    assert "2019,120.5,10" in text and "D1:" in text and '"data_ref"' in text
