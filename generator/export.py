"""Converting the finished .pptx to PDF with LibreOffice, when it is installed.

Python cannot draw a PowerPoint file by itself, so the conversion is done by LibreOffice
running without a window ("headless"). Where LibreOffice is not installed the app simply
does not offer PDF.
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
            subprocess.run(command, capture_output=True, timeout=TIMEOUT, check=False)
        except subprocess.TimeoutExpired as e:
            raise ExportError("LibreOffice took too long to make the PDF.") from e
        except OSError as e:
            raise ExportError(f"LibreOffice could not be started: {e}") from e
        result = folder / "presentation.pdf"
        if not result.exists() or result.stat().st_size == 0:
            raise ExportError("LibreOffice did not produce a PDF.")
        return result.read_bytes()
