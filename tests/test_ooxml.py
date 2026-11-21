"""The order of XML elements in the generated .pptx, for the parts this project writes by hand.

PowerPoint is strict: if child elements appear in another order than the OOXML schema
(ECMA-376) prescribes, it reports the file as damaged and offers to "repair" it, while
LibreOffice and python-pptx happily open it. These sequences are copied from the schema
for every element whose children the code adds or reorders itself.
"""
import io
import itertools
import zipfile

import pytest
from lxml import etree

from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_DECK_RU, SAMPLE_IMAGE, sample_photo
from generator.design.styles import STYLES
from generator.render.builder import build_pptx
from tests.stress_deck import IMG, STRESS_DECK

FILLS = ["noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill"]
# element -> its allowed children, in schema order (alternatives share one position)
ORDER = {
    "spPr": ["xfrm", ["custGeom", "prstGeom"], FILLS, "ln", ["effectLst", "effectDag"], "scene3d", "sp3d", "extLst"],
    "pPr": ["lnSpc", "spcBef", "spcAft", ["buClrTx", "buClr"], ["buSzTx", "buSzPct", "buSzPts"],
            ["buFontTx", "buFont"], ["buNone", "buAutoNum", "buChar", "buBlip"], "tabLst", "defRPr", "extLst"],
    "rPr": ["ln", FILLS, ["effectLst", "effectDag"], "highlight", ["uLnTx", "uLn"], ["uFillTx", "uFill"],
            "latin", "ea", "cs", "sym", "hlinkClick", "hlinkMouseOver", "rtl", "extLst"],
    "blipFill": ["blip", "srcRect", ["tile", "stretch"]],
    "pic": ["nvPicPr", "blipFill", "spPr", "style", "extLst"],
    "sp": ["nvSpPr", "spPr", "style", "txBody", "extLst"],
    "sld": ["cSld", "clrMapOvr", "transition", "timing", "extLst"],
    "chartSpace": ["date1904", "lang", "roundedCorners", "AlternateContent", "clrMapOvr", "pivotSource",
                   "protection", "chart", "spPr", "txPr", "externalData", "printSettings", "userShapes", "extLst"],
    "plotArea": ["layout", ["barChart", "lineChart", "pieChart", "doughnutChart"], ["catAx", "valAx"],
                 "dTable", "spPr", "extLst"],
    "effectLst": ["blur", "fillOverlay", "glow", "innerShdw", "outerShdw", "prstShdw", "reflection", "softEdge"],
}
REPEATABLE = {"plotArea"}      # several axes in a row are allowed


def position(spec, name):
    for i, slot in enumerate(spec):
        if name == slot or (isinstance(slot, list) and name in slot):
            return i
    return None


def problems_in(xml):
    found = []
    for element in etree.fromstring(xml).iter():
        if not isinstance(element.tag, str):
            continue
        parent = etree.QName(element).localname
        spec = ORDER.get(parent)
        if not spec:
            continue
        last = -1
        for child in element:
            if not isinstance(child.tag, str):
                continue
            name = etree.QName(child).localname
            pos = position(spec, name)
            if pos is None:
                found.append(f"<{name}> is not allowed inside <{parent}>")
            elif pos < last or (pos == last and parent not in REPEATABLE and not isinstance(spec[pos], list)):
                found.append(f"<{name}> is out of order inside <{parent}>")
            else:
                last = max(last, pos)
    return found


DECKS = {"sample": (SAMPLE_DECK, SAMPLE_IMAGE), "sample-ru": (SAMPLE_DECK_RU, SAMPLE_IMAGE), "stress": (STRESS_DECK, IMG)}


@pytest.mark.parametrize("deck_name, style", list(itertools.product(DECKS, STYLES)))
def test_generated_xml_follows_the_schema_order(deck_name, style):
    deck, image = DECKS[deck_name]
    data = build_pptx(deck, style, "Corporate Blue", {image: sample_photo()}, credits={image: "Photo by X"})
    archive = zipfile.ZipFile(io.BytesIO(data))
    problems = []
    for name in archive.namelist():
        if name.startswith(("ppt/slides/slide", "ppt/charts/chart")) and name.endswith(".xml"):
            problems += [f"{name}: {p}" for p in problems_in(archive.read(name))]
    assert not problems, "\n".join(sorted(set(problems))[:20])


def test_the_checker_itself_catches_a_wrong_order():
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    wrong = f'<a:pPr xmlns:a="{a}"><a:buChar char="x"/><a:buClr/><a:spcAft/></a:pPr>'.encode()
    right = f'<a:pPr xmlns:a="{a}"><a:spcAft/><a:buClr/><a:buChar char="x"/></a:pPr>'.encode()
    assert len(problems_in(wrong)) == 2 and problems_in(right) == []
    unknown = f'<a:spPr xmlns:a="{a}"><a:prstGeom/><a:bogus/></a:spPr>'.encode()
    assert problems_in(unknown) == ["<bogus> is not allowed inside <spPr>"]
