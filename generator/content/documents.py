"""Reading text out of the document the user attaches."""
import pypdf


def extract_text_from_file(uploaded_file):
    """Read text from the uploaded file"""
    if uploaded_file is None:
        return ""
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    elif uploaded_file.name.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        except Exception:
            return ""
    return ""
