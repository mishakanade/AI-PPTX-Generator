"""Painter #1: draws slide descriptions (SlideSpec) into a real .pptx file.

python-pptx covers most of what is needed. A few things it has no method for
(transparency, soft shadows, real bullets, rounded picture corners) are written
straight into the file's XML in the small `_set_...` helpers below.
"""
from io import BytesIO

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_MARK
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from generator.render.primitives import SLIDE_H, SLIDE_W, Box, ChartShape, Gradient, Picture, Text
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
    if item.alt:
        # PowerPoint's "alt text": read aloud by screen readers instead of the image
        picture._element.nvPicPr.cNvPr.set("descr", item.alt)


CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "pie": XL_CHART_TYPE.DOUGHNUT,
}


def _number_format(item):
    """Excel-style number format matching ChartShape.label: '#,##0.0" bn $"'."""
    fmt = "#,##0" + ("." + "0" * item.decimals if item.decimals else "")
    if item.unit:
        fmt += '"' + (item.unit if item.unit == "%" else " " + item.unit).replace('"', "") + '"'
    return fmt


def _no_fill_background(chart):
    """Make the chart area and the plot area transparent, so the slide shows through."""
    space = chart._chartSpace
    chart = space.find(qn("c:chart"))
    for parent, anchor in ((space, chart), (chart.find(qn("c:plotArea")), None)):
        sp_pr = parent.find(qn("c:spPr"))
        if sp_pr is None:
            sp_pr = etree.SubElement(parent, qn("c:spPr"))
            if anchor is not None:            # in the chart space, spPr must come right after <c:chart>
                anchor.addnext(sp_pr)
        for child in list(sp_pr):
            sp_pr.remove(child)
        etree.SubElement(sp_pr, qn("a:noFill"))
        line = etree.SubElement(sp_pr, qn("a:ln"))
        etree.SubElement(line, qn("a:noFill"))


def _style_axis(axis, item, color, show_labels=True):
    axis.major_tick_mark = XL_TICK_MARK.NONE
    axis.minor_tick_mark = XL_TICK_MARK.NONE
    axis.format.line.color.rgb = _rgb(color)
    axis.tick_labels.font.size = Pt(item.font_size)
    axis.tick_labels.font.color.rgb = _rgb(item.text_color)
    if not show_labels:
        axis.visible = False


def _draw_chart(slide, item):
    data = CategoryChartData(number_format=_number_format(item))
    if item.kind == "pie":
        # the legend is the only place a doughnut shows its values: "USA — 48.5%"
        data.categories = [f"{name} — {item.label(value)}" for name, value in zip(item.categories, item.series[0][1])]
    else:
        data.categories = item.categories
    for name, values in item.series:
        data.add_series(name, values)
    frame = slide.shapes.add_chart(CHART_TYPES[item.kind], Inches(item.x), Inches(item.y),
                                   Inches(item.w), Inches(item.h), data)
    chart = frame.chart
    chart.has_title = False
    chart.font.name = item.font
    chart.font.size = Pt(item.font_size)
    chart.font.color.rgb = _rgb(item.text_color)
    _no_fill_background(chart)

    chart.has_legend = item.legend
    if item.legend:
        chart.legend.position = XL_LEGEND_POSITION.RIGHT if item.kind == "pie" else XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(item.font_size + (3 if item.kind == "pie" else 0))
        chart.legend.font.color.rgb = _rgb(item.text_color)

    plot = chart.plots[0]
    plot.vary_by_categories = item.kind == "pie"
    if item.show_values:
        plot.has_data_labels = True
        labels = plot.data_labels
        labels.number_format = _number_format(item)
        labels.number_format_is_linked = False
        labels.font.size = Pt(item.font_size + 1)
        labels.font.bold = True
        labels.font.color.rgb = _rgb(item.text_color)
        if item.kind in ("column", "bar"):
            labels.position = XL_LABEL_POSITION.OUTSIDE_END
        elif item.kind == "line":
            labels.position = XL_LABEL_POSITION.ABOVE

    if item.kind == "pie":
        # a doughnut: one colour per slice, thin gaps in the slide colour between the slices
        hole = chart._chartSpace.find(".//" + qn("c:holeSize"))
        if hole is not None:
            hole.set("val", "58")
        for index, point in enumerate(plot.series[0].points):
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = _rgb(item.colors[index])
            point.format.line.color.rgb = _rgb(item.background)
            point.format.line.width = Pt(2)
        return

    for index, series in enumerate(plot.series):
        color = _rgb(item.colors[index])
        if item.kind == "line":
            series.smooth = False
            series.format.line.color.rgb = color
            series.format.line.width = Pt(3)
            series.marker.style = XL_MARKER_STYLE.CIRCLE
            series.marker.size = 9
            series.marker.format.fill.solid()
            series.marker.format.fill.fore_color.rgb = color
            series.marker.format.line.color.rgb = color
        else:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = color
    if item.kind in ("column", "bar"):
        plot.gap_width = 70
        plot.overlap = -10 if len(item.series) > 1 else 0

    _style_axis(chart.category_axis, item, item.grid_color)
    if item.kind == "bar":
        chart.category_axis.reverse_order = True   # first category on top, as people read
    value_axis = chart.value_axis
    # with numbers written on the bars the value scale is redundant; otherwise show it with light gridlines
    _style_axis(value_axis, item, item.grid_color, show_labels=not item.show_values)
    value_axis.format.line.fill.background()
    value_axis.has_major_gridlines = not item.show_values
    if value_axis.has_major_gridlines:
        value_axis.major_gridlines.format.line.color.rgb = _rgb(item.grid_color)
        value_axis.major_gridlines.format.line.width = Pt(0.75)
    value_axis.tick_labels.number_format = _number_format(item)
    value_axis.tick_labels.number_format_is_linked = False


# Transitions between slides: name -> the element inside <p:transition> (ECMA-376 basic set)
TRANSITIONS = {
    "fade": ("fade", {}),
    "push": ("push", {"dir": "u"}),     # the new slide pushes the old one up
    "wipe": ("wipe", {"dir": "r"}),     # the new slide is revealed from the left
}


def _set_transition(slide, name):
    """<p:transition spd="med"><p:fade/></p:transition>, placed where the schema wants it."""
    element, attributes = TRANSITIONS[name]
    transition = etree.Element(qn("p:transition"), spd="med")
    etree.SubElement(transition, qn(f"p:{element}"), **attributes)
    sld = slide._element
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(transition)        # schema order: cSld, clrMapOvr, transition, timing, extLst


def draw_slide(presentation, spec, images, transition=None):
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
        elif isinstance(item, ChartShape):
            _draw_chart(slide, item)
    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes
    if transition in TRANSITIONS:
        _set_transition(slide, transition)
    return slide


def specs_to_pptx(specs, images, title="", transition=None):
    """Draw all slide descriptions and return the finished .pptx file as bytes."""
    presentation = Presentation()
    presentation.slide_width = Inches(SLIDE_W)
    presentation.slide_height = Inches(SLIDE_H)
    presentation.core_properties.title = title
    for spec in specs:
        draw_slide(presentation, spec, images, transition)
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
