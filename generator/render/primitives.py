"""The drawing vocabulary: everything a slide is made of.

A layout never talks to PowerPoint directly. It only produces a list of these simple
objects ("a rounded box here, a text block there, a picture over there"), all measured
in inches from the top-left corner of the slide. Two separate "painters" then draw the
same list: pptx_backend.py into a .pptx file and html_backend.py into an HTML preview.
That is why the preview in the browser matches the downloaded file.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

# Slide size in inches (16:9)
SLIDE_W = 13.333
SLIDE_H = 7.5

Color = Tuple[int, int, int]


@dataclass
class Gradient:
    """A smooth transition between two colours."""
    start: Color
    end: Color
    direction: str = "diagonal"   # "horizontal" (left to right), "vertical" (top to bottom), "diagonal"


Fill = Union[Color, Gradient, None]


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
    line: Optional[Color] = None   # outline colour
    line_width: float = 1.0        # outline width in points
    shadow: bool = False           # soft drop shadow
    ellipse: bool = False


@dataclass
class Para:
    """One paragraph inside a Text block. Empty settings are taken from the Text block."""
    text: str
    size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color: Optional[Color] = None
    font: Optional[str] = None
    bullet: bool = False
    space_after: Optional[float] = None   # gap after the paragraph, in points


@dataclass
class Text:
    """A block of text that wraps inside its rectangle."""
    x: float
    y: float
    w: float
    h: float
    paragraphs: List[Para]
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
    bullet_color: Optional[Color] = None


@dataclass
class Picture:
    """A photo that fills its rectangle completely; whatever does not fit is cropped evenly."""
    x: float
    y: float
    w: float
    h: float
    key: str                       # which image to draw: a key of the images dict
    radius: float = 0.0


@dataclass
class SlideSpec:
    """Everything needed to draw one slide. Items are drawn in order, later ones on top."""
    background: Fill
    items: List[Union[Box, Text, Picture]] = field(default_factory=list)
    notes: str = ""                # speaker notes
