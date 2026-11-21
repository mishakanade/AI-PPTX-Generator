"""Reading text out of the document the user attaches."""
import docx
import pypdf
from docx.table import Table


class DocumentReadError(Exception):
    """The attached file could not be turned into text.

    reason is a short code the interface translates: "unsupported", "damaged", "empty" or
    "scan" (a PDF without a text layer). str(error) is an English explanation.
    """

    MESSAGES = {
        "unsupported": "Unsupported file type: {name}.",
        "damaged": "Could not read {name}: the file looks damaged.",
        "empty": "No text found in {name}.",
        "scan": "No text found in {name}. It may be a scan: pages stored as images, not text.",
    }

    def __init__(self, reason, file_name):
        super().__init__(self.MESSAGES[reason].format(name=file_name))
        self.reason = reason
        self.file_name = file_name


def _read_pdf(file):
    reader = pypdf.PdfReader(file)
    pages = [page.extract_text() for page in reader.pages]
    return "\n".join(text for text in pages if text)


def _read_docx(file):
    document = docx.Document(file)
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
