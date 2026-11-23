"""Developer tool: make docs/images/slides.jpg, the grid of example slides shown in README.md.

The slides are the built-in example deck in several styles and colour themes, drawn by
LibreOffice exactly as the PDF export draws them, so the picture shows real output.
Needs LibreOffice and PyMuPDF (pip install pymupdf).

Run from the project folder:
    python tools/readme_images.py
"""
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402
from PIL import Image  # noqa: E402

from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo  # noqa: E402
from generator.export import to_pdf  # noqa: E402
from generator.render.builder import build_pptx  # noqa: E402

# (style, colour theme, slide number: 0 is the title slide)
PICKS = [
    ("bold", "Corporate Blue", 0),
    ("editorial", "Paper & Ink", 3),
    ("corporate", "Royal Navy & Gold", 4),
    ("soft", "Lavender Dream", 6),
    ("minimal", "Dark Modern", 9),
    ("corporate", "Teal & Coral", 2),
]
COLUMNS, TILE_W, GAP = 3, 640, 16
BACKGROUND = (243, 244, 246)


def slide_image(style, theme, number, cache={}):  # noqa: B006 - the cache is meant to be shared
    if (style, theme) not in cache:
        pptx = build_pptx(SAMPLE_DECK, style, theme, {SAMPLE_IMAGE: sample_photo()})
        cache[(style, theme)] = pymupdf.open(stream=to_pdf(pptx))
    page = cache[(style, theme)][number]
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(TILE_W * 2 / page.rect.width, TILE_W * 2 / page.rect.width))
    image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
    return image.resize((TILE_W, round(TILE_W * image.height / image.width)), Image.LANCZOS)


def main():
    tiles = [slide_image(*pick) for pick in PICKS]
    tile_h = tiles[0].height
    rows = -(-len(tiles) // COLUMNS)
    grid = Image.new("RGB", (COLUMNS * TILE_W + (COLUMNS + 1) * GAP, rows * tile_h + (rows + 1) * GAP), BACKGROUND)
    for i, tile in enumerate(tiles):
        row, column = divmod(i, COLUMNS)
        grid.paste(tile, (GAP + column * (TILE_W + GAP), GAP + row * (tile_h + GAP)))
    out = ROOT / "docs" / "images" / "slides.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out, quality=85, optimize=True)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
