"""Developer tool: regenerate generator/render/font_metrics.json.

The renderer has to know how wide a piece of text will be *before* PowerPoint draws it,
otherwise it cannot pick a font size that fits. This script reads character widths from
open fonts that were designed to have exactly the same widths as the Office fonts
(Carlito = Calibri, Liberation Sans = Arial) and saves them into a small JSON table.
Georgia has no such twin, so it is approximated from Liberation Serif (Times) made wider.

Needs: pip install fonttools, and the fonts below (present on most Linux systems).
Run:   python tools/build_font_metrics.py
"""
import json
from pathlib import Path

from fontTools.ttLib import TTFont

FONT_DIR = Path("/usr/share/fonts/truetype")
# Office font -> (regular file, bold file, width multiplier for regular, for bold)
SOURCES = {
    "Calibri": ("crosextra/Carlito-Regular.ttf", "crosextra/Carlito-Bold.ttf", 1.0, 1.0),
    "Arial": ("liberation/LiberationSans-Regular.ttf", "liberation/LiberationSans-Bold.ttf", 1.0, 1.0),
    # Georgia is noticeably wider than Times; the multipliers are deliberately on the safe side.
    "Georgia": ("liberation/LiberationSerif-Regular.ttf", "liberation/LiberationSerif-Bold.ttf", 1.16, 1.2),
}
# Line height at "single" spacing, as a multiple of the font size (from the real fonts' metrics).
LINE_HEIGHT = {"Calibri": 1.22, "Arial": 1.15, "Georgia": 1.14}

CHARS = (
    "".join(chr(c) for c in range(32, 127))            # ASCII
    + "".join(chr(c) for c in range(0xC0, 0x100))      # accented Latin letters
    + "".join(chr(c) for c in range(0x400, 0x460))     # Cyrillic
    + "–—‘’“”„«»…•·№€£°×±"
)


def widths(path, scale):
    font = TTFont(FONT_DIR / path)
    cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    known = [hmtx[cmap[ord(ch)]][0] for ch in CHARS if ord(ch) in cmap]
    average = sum(known) / len(known)
    # Widths are stored in thousandths of the font size.
    return [round((hmtx[cmap[ord(ch)]][0] if ord(ch) in cmap else average) * scale * 1000 / upm) for ch in CHARS]


def main():
    data = {"chars": CHARS, "fonts": {}}
    for name, (regular, bold, regular_scale, bold_scale) in SOURCES.items():
        data["fonts"][name] = {
            "line_height": LINE_HEIGHT[name],
            "regular": widths(regular, regular_scale),
            "bold": widths(bold, bold_scale),
        }
    out = Path(__file__).resolve().parent.parent / "generator" / "render" / "font_metrics.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(CHARS)} characters, {len(SOURCES)} fonts)")


if __name__ == "__main__":
    main()
