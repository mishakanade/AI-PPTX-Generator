"""Opening pictures that come from outside (uploads, project files) safely.

A picture file is compressed: a small PNG can say "I am 40,000 x 40,000 pixels" and need
several gigabytes of memory once opened (a "decompression bomb"). The size is written at the
start of the file, so it is checked before the picture is decoded.

Photos straight from a phone are also often far larger than a slide needs (a 12-megapixel
photo is 4000 pixels wide; a slide is about 2000 pixels wide even on a large screen), and many
are stored sideways with a note "turn me" (EXIF orientation) that PowerPoint may ignore.
fit_for_slides makes them a sensible size and turns them the right way up.
"""
from io import BytesIO

from PIL import Image, ImageOps

MAX_PIXELS = 50_000_000      # 50 megapixels: more than any normal photo, far less than a bomb
MAX_SIDE = 2560              # pixels; uploaded photos are scaled down to this
EXIF_ORIENTATION = 0x0112


def open_image(data):
    """The picture in these bytes, fully loaded. Raises ValueError if it is not a picture or too large."""
    try:
        image = Image.open(BytesIO(data))
    except Exception as e:
        raise ValueError("not an image") from e
    if image.width * image.height > MAX_PIXELS:
        raise ValueError(f"the image is too large ({image.width} x {image.height} pixels)")
    try:
        image.load()
    except Exception as e:
        raise ValueError("the image is damaged") from e
    return image


def fit_for_slides(data, max_side=MAX_SIDE):
    """The picture no larger than max_side on its longer side and the right way up, as bytes.

    A picture that needs neither change is returned as it was, unchanged byte for byte.
    Raises ValueError like open_image.
    """
    image = open_image(data)
    turned = image.getexif().get(EXIF_ORIENTATION, 1) not in (1, None)
    if max(image.size) <= max_side and not turned:
        return data
    keep_format = image.format
    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_side, max_side), Image.LANCZOS)    # keeps the proportions
    buffer = BytesIO()
    has_transparency = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    if has_transparency or keep_format == "PNG":
        image.save(buffer, "PNG", optimize=True)
    else:
        image.convert("RGB").save(buffer, "JPEG", quality=88)
    return buffer.getvalue()
