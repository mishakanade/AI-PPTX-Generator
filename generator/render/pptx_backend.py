"""Painter #1: draws slide descriptions (SlideSpec) into a real .pptx file.

python-pptx covers most of what is needed. A few things it has no method for
(transparency, soft shadows, real bullets, rounded picture corners) are written
straight into the file's XML in the small `_set_...` helpers below.
"""
from io import BytesIO

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from generator.render.primitives import SLIDE_H, SLIDE_W, Box, Gradient, Picture, Text
from generator.render.textfit import BULLET_INDENT_EM

ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
# python-pptx measures gradient angles counter-clockwise, starting from "left to right"
GRADIENT_ANGLE = {"horizontal": 0, "vertical": 270, "diagonal": 315}
EMU_PER_POINT = 12700


def _rgb(color):
    return RGBColor(*color)


def _apply_fill(fill_format, fill, alpha=1.0):
    """Paint a shape (or the slide background) with a colour or a gradient."""
    if fill is None:
        fill_format.background()   # "no fill"
    elif isinstance(fill, Gradient):
        fill_format.gradient()
        fill_format.gradient_angle = GRADIENT_ANGLE[fill.direction]
        stops = fill_format.gradient_stops
        stops[0].color.rgb = _rgb(fill.start)
        stops[1].color.rgb = _rgb(fill.end)
    else:
        fill_format.solid()
        fill_format.fore_color.rgb = _rgb(fill)
        if alpha < 1.0:
            _set_alpha(fill_format, alpha)


def _set_alpha(fill_format, alpha):
    """Transparency: <a:srgbClr><a:alpha val="45000"/></a:srgbClr> means 45% opaque."""
    color = fill_format._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    etree.SubElement(color, qn("a:alpha"), val=str(int(alpha * 100000)))


def _set_shadow(shape):
    """A soft shadow below the shape."""
    shape.shadow.inherit = False   # creates an empty <a:effectLst> in the right place
    effects = shape._element.spPr.find(qn("a:effectLst"))
    shadow = etree.SubElement(
        effects, qn("a:outerShdw"),
        blurRad=str(Pt(18)), dist=str(Pt(5)), dir="5400000", algn="t", rotWithShape="0",
    )
    color = etree.SubElement(shadow, qn("a:srgbClr"), val="000000")
    etree.SubElement(color, qn("a:alpha"), val="14000")


def _set_bullet(paragraph, char, color, size_pt):
    """Turn a paragraph into a real bullet item with a hanging indent."""
    indent = int(BULLET_INDENT_EM * size_pt * EMU_PER_POINT)
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(indent))       # the whole paragraph is shifted right...
    pPr.set("indent", str(-indent))    # ...and its first line (the bullet) is pulled back
    bullet_color = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(bullet_color, qn("a:srgbClr"), val="{:02X}{:02X}{:02X}".format(*color))
    etree.SubElement(pPr, qn("a:buFont"), typeface="Arial")
    etree.SubElement(pPr, qn("a:buChar"), char=char)


def _set_picture_radius(picture, radius_in, w, h):
    picture.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
    geometry = picture._element.spPr.find(qn("a:prstGeom"))
    adjustments = geometry.find(qn("a:avLst"))
    if adjustments is None:
        adjustments = etree.SubElement(geometry, qn("a:avLst"))
    # the corner size is stored as a share of the shorter side (50000 = fully round)
    value = min(50000, int(radius_in / min(w, h) * 100000))
    etree.SubElement(adjustments, qn("a:gd"), name="adj", fmla=f"val {value}")


def _draw_box(slide, box):
    if box.ellipse:
        kind = MSO_SHAPE.OVAL
    elif box.radius > 0:
        kind = MSO_SHAPE.ROUNDED_RECTANGLE
    else:
        kind = MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(box.x), Inches(box.y), Inches(box.w), Inches(box.h))
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shape.adjustments[0] = min(0.5, box.radius / min(box.w, box.h))
    # New shapes point at the template's default look (blue fill, outline, shadow) through
    # a <p:style> element. Everything is set explicitly here, so that link is removed.
    default_style = shape._element.find(qn("p:style"))
    if default_style is not None:
        shape._element.remove(default_style)
    _apply_fill(shape.fill, box.fill, box.alpha)
    if box.line is None:
        shape.line.fill.background()   # no outline
    else:
        shape.line.color.rgb = _rgb(box.line)
        shape.line.width = Pt(box.line_width)
    if box.shadow:
        _set_shadow(shape)


def _draw_text(slide, block):
    shape = slide.shapes.add_textbox(Inches(block.x), Inches(block.y), Inches(block.w), Inches(block.h))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    # no inner margins: the text starts exactly where the layout placed the box
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = Emu(0)
    frame.vertical_anchor = ANCHOR[block.valign]

    for i, para in enumerate(block.paragraphs):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        size = para.size or block.size
        paragraph.alignment = ALIGN[block.align]
        if block.line_spacing != 1.0:
            paragraph.line_spacing = block.line_spacing
        gap = block.space_after if para.space_after is None else para.space_after
        if gap and i < len(block.paragraphs) - 1:
            paragraph.space_after = Pt(gap)

        run = paragraph.add_run()
        run.text = para.text
        font = run.font
        font.name = para.font or block.font
        font.size = Pt(size)
        font.bold = block.bold if para.bold is None else para.bold
        font.italic = block.italic if para.italic is None else para.italic
        font.color.rgb = _rgb(para.color or block.color)

        if para.bullet:
            _set_bullet(paragraph, block.bullet_char, block.bullet_color or block.color, size)


def _draw_picture(slide, item, images):
    data = images.get(item.key)
    if not data:
        return
    picture = slide.shapes.add_picture(
        BytesIO(data), Inches(item.x), Inches(item.y), Inches(item.w), Inches(item.h)
    )
    # "Cover" crop: the picture was stretched into the frame, so cut off evenly whatever
    # part of it does not match the frame's proportions - the photo is never distorted.
    px_w, px_h = picture.image.size
    image_ratio, frame_ratio = px_w / px_h, item.w / item.h
    if image_ratio > frame_ratio:      # picture is wider than the frame: trim left and right
        extra = (1 - frame_ratio / image_ratio) / 2
        picture.crop_left = picture.crop_right = extra
    else:                              # picture is taller: trim top and bottom
        extra = (1 - image_ratio / frame_ratio) / 2
        picture.crop_top = picture.crop_bottom = extra
    if item.radius > 0:
        _set_picture_radius(picture, item.radius, item.w, item.h)


def draw_slide(presentation, spec, images):
    """Add one slide to the presentation and draw every item of its description."""
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])   # layout 6 is blank
    _apply_fill(slide.background.fill, spec.background)
    for item in spec.items:
        if isinstance(item, Box):
            _draw_box(slide, item)
        elif isinstance(item, Text):
            _draw_text(slide, item)
        elif isinstance(item, Picture):
            _draw_picture(slide, item, images)
    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes
    return slide


def specs_to_pptx(specs, images, title=""):
    """Draw all slide descriptions and return the finished .pptx file as bytes."""
    presentation = Presentation()
    presentation.slide_width = Inches(SLIDE_W)
    presentation.slide_height = Inches(SLIDE_H)
    presentation.core_properties.title = title
    for spec in specs:
        draw_slide(presentation, spec, images)
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
