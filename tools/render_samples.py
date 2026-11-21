"""Developer tool: save the example presentation in every style, to look at the designs.

No API keys are needed: the content is the built-in example deck (or, with --stress,
a deck of deliberately long Russian texts used by the tests) and the photo is drawn.

Run from the project folder:
    python tools/render_samples.py                       all styles, theme Corporate Blue
    python tools/render_samples.py --theme "Dark Modern"
    python tools/render_samples.py --stress --pdf        long texts; also PDF (needs LibreOffice)

The files are written to samples/ (not tracked by git).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo  # noqa: E402
from generator.design.styles import STYLES  # noqa: E402
from generator.design.themes import THEMES  # noqa: E402
from generator.render.builder import build_pptx  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--theme", default="Corporate Blue", choices=list(THEMES), metavar="NAME")
    parser.add_argument("--stress", action="store_true", help="use the long-text test deck")
    parser.add_argument("--pdf", action="store_true", help="also convert to PDF with LibreOffice")
    args = parser.parse_args()

    if args.stress:
        from tests.stress_deck import IMG, STRESS_DECK
        deck, images, label = STRESS_DECK, {IMG: sample_photo()}, "stress"
    else:
        deck, images, label = SAMPLE_DECK, {SAMPLE_IMAGE: sample_photo()}, "sample"

    out = ROOT / "samples"
    out.mkdir(exist_ok=True)
    theme_slug = "".join(ch for ch in args.theme if ch.isalnum())
    files = []
    for key, style in STYLES.items():
        path = out / f"{label}_{key}_{theme_slug}.pptx"
        path.write_bytes(build_pptx(deck, key, args.theme, images))
        files.append(path)
        print(f"{style.name:10} -> {path.relative_to(ROOT)}")

    if args.pdf:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            print("LibreOffice is not installed, PDF files were not made.")
            return
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out), *map(str, files)],
                       check=True, capture_output=True)
        print(f"PDF files are in {out.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
