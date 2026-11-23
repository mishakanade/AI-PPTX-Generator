"""Reading text out of the document the user attaches.

DOCX (and XLSX, see data.py) files are zip archives: compressed folders of XML files.
A malicious archive of a few kilobytes can unpack to many gigabytes (a "zip bomb"), so
check_archive looks at the sizes written in the archive before anything is unpacked.
A PDF is read page by page only until there is more text than the app can use.
"""
import io
import zipfile

import docx
import pypdf
from docx.table import Table

MAX_UNPACKED = 300_000_000     # bytes an archive may unpack to; real documents need a few MB
MAX_TEXT = 400_000             # characters; more than the long-document reading uses (llm.py)


def check_archive(data):
    """Raise ValueError if these bytes are not a zip archive or would unpack to too much."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            unpacked = sum(entry.file_size for entry in archive.infolist())
    except zipfile.BadZipFile as e:
        raise ValueError("not a zip archive") from e
    if unpacked > MAX_UNPACKED:
        raise ValueError(f"the file unpacks to {unpacked // 1_000_000} MB")


class DocumentReadError(Exception):
    """The attached file could not be turned into text.

    reason is a short code the interface translates: "unsupported", "damaged", "empty",
    "scan" (a PDF without a text layer) or "too_big" (it would unpack to far too much).
    str(error) is an English explanation.
    """

    MESSAGES = {
        "unsupported": "Unsupported file type: {name}.",
        "damaged": "Could not read {name}: the file looks damaged.",
        "empty": "No text found in {name}.",
        "scan": "No text found in {name}. It may be a scan: pages stored as images, not text.",
        "too_big": "{name} is too large to read: it unpacks to hundreds of megabytes.",
    }

    def __init__(self, reason, file_name):
        super().__init__(self.MESSAGES[reason].format(name=file_name))
        self.reason = reason
        self.file_name = file_name


def _read_pdf(file):
    reader = pypdf.PdfReader(file)
    pages, length = [], 0
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
        length += len(text)
        if length > MAX_TEXT:            # enough: the rest would not be used anyway
            break
    return "\n".join(text for text in pages if text)


def _read_docx(file):
    data = file.read()
    try:
        check_archive(data)
    except ValueError as e:
        raise DocumentReadError("too_big" if "unpacks" in str(e) else "damaged", file.name) from e
    document = docx.Document(io.BytesIO(data))
    parts = []
    # iter_inner_content() walks paragraphs and tables in the order they appear in the document.
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        else:
            parts.append(block.text)
    return "\n".join(part for part in parts if part.strip())


def extract_text_from_file(uploaded_file):
    """Return the text of an uploaded TXT, PDF or DOCX file ("" when no file is attached).

    Raises DocumentReadError when a file is attached but no text can be read from it.
    """
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    try:
        if name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8", errors="ignore")
        elif name.endswith(".pdf"):
            text = _read_pdf(uploaded_file)
        elif name.endswith(".docx"):
            text = _read_docx(uploaded_file)
        else:
            raise DocumentReadError("unsupported", uploaded_file.name)
    except DocumentReadError:
        raise
    except Exception as e:
        raise DocumentReadError("damaged", uploaded_file.name) from e

    if not text.strip():
        raise DocumentReadError("scan" if name.endswith(".pdf") else "empty", uploaded_file.name)
    return text


def split_text(text, size):
    """Cut a long text into parts of at most `size` characters, at paragraph or sentence ends
    where possible, so that no fact is cut in half."""
    parts, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
            if cut > size // 2:                    # a natural break in the second half of the part
                end = start + cut + 1
        part = text[start:end].strip()
        if part:
            parts.append(part)
        start = end
    return parts
