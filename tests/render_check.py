"""Checking the layout against a real renderer: LibreOffice draws the .pptx, we look at the PDF.

The layout engine predicts how much room every text needs (textfit.py). The ordinary tests
check those predictions against themselves; this check asks a real program to draw the
file and reads back where each piece of text actually ended up:

- no text outside the slide, and none missing (LibreOffice leaves out text beyond the edge);
- every text stays inside the box the layout gave it (it did not wrap into more lines
  than predicted and run out of the bottom);
- texts of different boxes do not overlap.

How the text is found: the PDF knows each run of text ("span") with its position, but not
which box of ours it came from. So every span is matched to the box whose text contains
it, the nearest one if several do. Charts are drawn by LibreOffice itself and skipped.

The result is only exact where LibreOffice draws the fonts with the widths the layout engine
assumes; fonts_are_known() checks that (see generator/export.py for the fonts it uses).
Needs LibreOffice and PyMuPDF (pip install pymupdf).
"""
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from generator.export import font_environment, to_pdf
from generator.render.pptx_backend import specs_to_pptx
from generator.render.primitives import SLIDE_H, SLIDE_W, ChartShape, Text

PT = 72                   # PDF coordinates are in points: 72 per inch
SIDE_SLACK = 0.06         # inches a line may stick out sideways (italic overhang, rounding)
BOTTOM_SLACK = 0.35       # part of the font size a line may go below its box (descenders);
                          # a whole extra line is about 1.2 font sizes, so it is always caught
OVERLAP_SLACK = 0.04      # inches two spans of different boxes may overlap (touching lines)

BULLET_CHARS = "•▪–—·"     # what bullets are drawn with; a bullet comes as a span of its own

# Office font -> fonts LibreOffice may draw it with: the same widths, or (Georgia) narrower ones
KNOWN_STAND_INS = {"Calibri": ["Carlito"], "Arial": ["Liberation Sans", "Arimo"],
                   "Georgia": ["Gelasio", "Liberation Serif", "Tinos"]}


@dataclass
class Span:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float

    def overlap(self, other):
        w = min(self.x1, other.x1) - max(self.x0, other.x0)
        h = min(self.y1, other.y1) - max(self.y0, other.y0)
        return min(w, h)


def normalize(text):
    return re.sub(r"\s+", "", text)


def fonts_are_known(fonts):
    """True if LibreOffice on this computer draws every font with the original or a known stand-in."""
    if not shutil.which("fc-match"):
        return False
    with tempfile.TemporaryDirectory() as folder:
        env = font_environment(folder)          # the same font settings the PDF export uses
        for font in fonts:
            found = subprocess.run(["fc-match", "-f", "%{family}", font], capture_output=True, text=True,
                                   env=env).stdout
            if not any(name in found for name in [font, *KNOWN_STAND_INS.get(font, [])]):
                return False
    return True


def spans(page):
    """Every non-empty run of text on a PDF page, in inches, trailing spaces left out."""
    found = []
    import pymupdf
    # by default text outside the page is left out: here it is exactly what is looked for
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_MEDIABOX_CLIP
    for block in page.get_text("rawdict", flags=flags)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                chars = [c for c in span["chars"] if c["c"].strip()]
                if not chars:
                    continue
                x0 = min(c["bbox"][0] for c in chars) / PT
                x1 = max(c["bbox"][2] for c in chars) / PT
                found.append(Span("".join(c["c"] for c in span["chars"]).strip(), x0, span["bbox"][1] / PT,
                                  x1, span["bbox"][3] / PT, span["size"]))
    return found


def owner(span, texts):
    """The text box this span was drawn from: one whose text contains it, the nearest."""
    piece = normalize(span.text).lstrip(BULLET_CHARS)
    candidates = [t for t in texts if piece and piece in normalize(" ".join(p.text for p in t.paragraphs))]

    def distance(t):
        cx, cy = (span.x0 + span.x1) / 2, (span.y0 + span.y1) / 2
        return max(t.x - cx, cx - t.x - t.w, 0) + max(t.y - cy, cy - t.y - t.h, 0)
    return min(candidates, key=distance, default=None)


def decoration(text):
    """A big quotation mark or a similar one-character ornament: it may overhang on purpose."""
    return len(normalize(" ".join(p.text for p in text.paragraphs))) <= 1


def page_problems(spec, page):
    texts = [item for item in spec.items if isinstance(item, Text)]
    charts = [item for item in spec.items if isinstance(item, ChartShape)]
    problems, placed = [], []
    for span in spans(page):
        cx, cy = (span.x0 + span.x1) / 2, (span.y0 + span.y1) / 2
        if span.x0 < -0.01 or span.y0 < -0.01 or span.x1 > SLIDE_W + 0.01 or span.y1 > SLIDE_H + 0.01:
            problems.append(f"off the slide: {span.text!r}")
        if not span.text.strip(BULLET_CHARS):
            continue                       # a bullet sign: its text follows as the next span
        if any(c.x <= cx <= c.x + c.w and c.y <= cy <= c.y + c.h for c in charts):
            continue                       # chart labels are LibreOffice's own business
        box = owner(span, texts)
        if box is None:
            problems.append(f"text that belongs to no box: {span.text!r}")
            continue
        placed.append((span, box))
        if decoration(box):
            continue
        out = {"left": box.x - span.x0, "right": span.x1 - box.x - box.w, "top": box.y - span.y0}
        side, amount = max(out.items(), key=lambda kv: kv[1])
        if amount > SIDE_SLACK + (span.size / PT * 0.25 if side == "top" else 0):
            problems.append(f"sticks out {amount:.2f} in on the {side}: {span.text!r}")
        below = span.y1 - box.y - box.h
        if below > BOTTOM_SLACK * span.size / PT:
            problems.append(f"runs {below:.2f} in below its box: {span.text!r}")
    for box in texts:
        wanted = normalize(" ".join(p.text for p in box.paragraphs))
        drawn = sum(len(normalize(span.text)) for span, owner_box in placed if owner_box is box)
        if wanted and drawn < len(wanted) and not decoration(box):
            problems.append(f"not drawn, or only in part: {wanted[:40]!r}")
    for i, (a, box_a) in enumerate(placed):
        for b, box_b in placed[i + 1:]:
            if box_a is not box_b and a.overlap(b) > OVERLAP_SLACK and not (decoration(box_a) or decoration(box_b)):
                problems.append(f"overlaps another text: {a.text!r} and {b.text!r}")
    return problems


def render_problems(specs, images):
    """[(slide number from 1, problem)] for these slide descriptions drawn by LibreOffice."""
    import pymupdf
    document = pymupdf.open(stream=to_pdf(specs_to_pptx(specs, images)))
    if len(document) != len(specs):
        return [(0, f"the PDF has {len(document)} pages for {len(specs)} slides")]
    return [(number, problem) for number, (spec, page) in enumerate(zip(specs, document), 1)
            for problem in page_problems(spec, page)]
