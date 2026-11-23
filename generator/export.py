"""Converting the finished .pptx to PDF with LibreOffice, when it is installed.

Python cannot draw a PowerPoint file by itself, so the conversion is done by LibreOffice
running without a window ("headless"). Where LibreOffice is not installed the app simply
does not offer PDF.

Fonts: the slides are laid out for Calibri, Arial and Georgia. Linux usually has free fonts
with exactly the same letter widths for the first two (Carlito, Liberation Sans), and
LibreOffice finds them by itself. Georgia has no such twin, and without a hint LibreOffice
takes a much wider serif font, so that text runs out of its boxes. FONT_HINTS tells it to
prefer fonts that are no wider than Georgia.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Where LibreOffice is installed by default when it is not on the PATH.
KNOWN_PLACES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]
TIMEOUT = 180     # seconds; the first start of LibreOffice can be slow

# A font settings file for fontconfig, the program that picks fonts for LibreOffice on Linux.
# It keeps all of the computer's own settings and adds the preferred stand-ins for Georgia:
# Gelasio has Georgia's widths (Latin letters only), Liberation Serif is a little narrower,
# so text drawn with it always fits.
FONT_HINTS = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <alias binding="same">
    <family>Georgia</family>
    <prefer><family>Gelasio</family><family>Liberation Serif</family><family>Tinos</family></prefer>
  </alias>
</fontconfig>
"""


class ExportError(Exception):
    """The PDF could not be made. The message is shown to the user."""


def find_soffice():
    """The path of LibreOffice's program, or None if it is not installed."""
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    return next((place for place in KNOWN_PLACES if os.path.exists(place)), None)


def to_pdf(pptx_bytes):
    """The presentation as PDF bytes. Raises ExportError if LibreOffice is missing or fails."""
    soffice = find_soffice()
    if not soffice:
        raise ExportError("LibreOffice is not installed.")
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        source = folder / "presentation.pptx"
        source.write_bytes(pptx_bytes)
        # A separate LibreOffice profile for every conversion: two conversions at the same
        # time would otherwise wait for each other's lock on the shared profile, or fail.
        profile = (folder / "profile").as_uri()
        command = [soffice, f"-env:UserInstallation={profile}", "--headless", "--convert-to", "pdf",
                   "--outdir", str(folder), str(source)]
        try:
            subprocess.run(command, capture_output=True, timeout=TIMEOUT, check=False, env=font_environment(folder))
        except subprocess.TimeoutExpired as e:
            raise ExportError("LibreOffice took too long to make the PDF.") from e
        except OSError as e:
            raise ExportError(f"LibreOffice could not be started: {e}") from e
        result = folder / "presentation.pdf"
        if not result.exists() or result.stat().st_size == 0:
            raise ExportError("LibreOffice did not produce a PDF.")
        return result.read_bytes()


def font_environment(folder):
    """The environment for LibreOffice: on Linux, with FONT_HINTS added to the font settings."""
    env = dict(os.environ)
    if os.path.exists("/etc/fonts/fonts.conf") and "FONTCONFIG_FILE" not in env:
        hints = Path(folder) / "fonts.conf"
        hints.write_text(FONT_HINTS, encoding="utf-8")
        env["FONTCONFIG_FILE"] = str(hints)
    return env
