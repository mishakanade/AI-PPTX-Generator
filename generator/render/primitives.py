"""The drawing vocabulary: everything a slide is made of.

A layout never talks to PowerPoint directly. It only produces a list of these simple
objects ("a rounded box here, a text block there, a picture over there"), all measured
in inches from the top-left corner of the slide. Two separate "painters" then draw the
same list: pptx_backend.py into a .pptx file and html_backend.py into an HTML preview.
That is why the preview in the browser matches the downloaded file.
"""
from dataclasses import dataclass, field

# Slide size in inches (16:9)
SLIDE_W = 13.333
SLIDE_H = 7.5

Color = tuple[int, int, int]


@dataclass
class Gradient:
    """A smooth transition between two colours."""
    start: Color
    end: Color
    direction: str = "diagonal"   # "horizontal" (left to right), "vertical" (top to bottom), "diagonal"


Fill = Color | Gradient | None


@dataclass
class Box:
    """A rectangle, rounded rectangle or ellipse. Lines are just very thin boxes."""
    x: float
    y: float
    w: float
    h: float
    fill: Fill = None
    alpha: float = 1.0             # 1 = solid, 0 = invisible (only for plain colour fills)
    radius: float = 0.0            # corner radius in inches
    line: Color | None = None   # outline colour
    line_width: float = 1.0        # outline width in points
    shadow: bool = False           # soft drop shadow
    ellipse: bool = False


@dataclass
class Para:
    """One paragraph inside a Text block. Empty settings are taken from the Text block."""
    text: str
    size: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    color: Color | None = None
    font: str | None = None
    bullet: bool = False
    space_after: float | None = None   # gap after the paragraph, in points


@dataclass
class Text:
    """A block of text that wraps inside its rectangle."""
    x: float
    y: float
    w: float
    h: float
    paragraphs: list[Para]
    font: str = "Calibri"
    size: float = 18               # in points
    color: Color = (0, 0, 0)
    bold: bool = False
    italic: bool = False
    align: str = "left"            # left / center / right
    valign: str = "top"            # top / middle / bottom
    line_spacing: float = 1.0      # 1.0 = single spacing
    space_after: float = 0         # default gap after each paragraph, in points
    bullet_char: str = "•"
    bullet_color: Color | None = None


@dataclass
class Picture:
    """A photo that fills its rectangle completely; whatever does not fit is cropped evenly."""
    x: float
    y: float
    w: float
    h: float
    key: str                       # which image to draw: a key of the images dict
    radius: float = 0.0
    alt: str = ""                  # description for screen readers ("alternative text")


@dataclass
class ChartShape:
    """A native, editable PowerPoint chart (drawn as SVG in the preview)."""
    x: float
    y: float
    w: float
    h: float
    kind: str                       # "column", "bar", "line" or "pie" (drawn as a doughnut)
    categories: list[str]
    series: list[tuple[str, list[float]]]   # (name, one value per category)
    colors: list[Color]             # one per series; for pie, one per category
    text_color: Color
    grid_color: Color
    background: Color               # slide colour, used for the gaps between doughnut slices
    font: str = "Calibri"
    font_size: float = 14
    unit: str = ""

    @property
    def decimals(self):
        """How many decimal places the numbers need (0, 1 or 2)."""
        values = [v for _, vs in self.series for v in vs]
        for places in (0, 1):
            if all(abs(v * 10 ** places - round(v * 10 ** places)) < 1e-9 for v in values):
                return places
        return 2

    def label(self, value):
        """A value as it is printed on the chart: 7 000, 12.5%, 3.2 bn $."""
        text = f"{value:,.{self.decimals}f}".replace(",", "\u00a0")   # digit groups split by a non-breaking space
        if not self.unit:
            return text
        return text + (self.unit if self.unit == "%" else "\u00a0" + self.unit)

    @property
    def show_values(self):
        """Values are written on the bars / points when that stays readable: a single series.

        A doughnut never carries them: its values are part of the legend instead.
        """
        return len(self.series) == 1 and self.kind != "pie"

    @property
    def legend(self):
        return self.kind == "pie" or len(self.series) > 1


@dataclass
class SlideSpec:
    """Everything needed to draw one slide. Items are drawn in order, later ones on top."""
    background: Fill
    items: list[Box | Text | Picture | ChartShape] = field(default_factory=list)
    notes: str = ""                # speaker notes
    title: str = ""                # the slide's title: the text block that shows it becomes
                                   # PowerPoint's real title (outline view, navigation, screen readers)
