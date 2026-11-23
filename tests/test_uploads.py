"""Files from users: hostile or merely unusual uploads end in a clear refusal, never a crash.

Every file a visitor can send is covered: a picture (photo or logo), a document, a data
table and a project file. The app may be published for anyone to use, so a single file must
not be able to fill the server's memory or stop the app.
"""
import io
import json
import random
import zipfile

import docx
import pytest
from PIL import Image

from generator.content import data, documents
from generator.content.documents import DocumentReadError, extract_text_from_file
from generator.content.schema import ContentError, parse_deck
from generator.design.sample_deck import SAMPLE_DECK, SAMPLE_IMAGE, sample_photo
from generator.images.pictures import EXIF_ORIENTATION, MAX_SIDE, fit_for_slides, open_image
from generator.images.unsplash import Photo, own_photo
from generator.project import load_project, save_project
from tests.test_content import Upload
from tests.test_fuzz import damage


def picture(size, mode="RGB", fmt="PNG", **save):
    buffer = io.BytesIO()
    Image.new(mode, size).save(buffer, fmt, **save)
    return buffer.getvalue()


# ----- pictures ----------------------------------------------------------------------------

def test_a_picture_claiming_too_many_pixels_is_refused_before_it_is_decoded():
    bomb = picture((9000, 9000), mode="1")         # 81 megapixels in a file of a few kilobytes
    assert len(bomb) < 100_000
    with pytest.raises(ValueError, match="too large"):
        open_image(bomb)
    with pytest.raises(ValueError):
        own_photo(bomb)


def test_a_large_photo_is_scaled_down_and_turned_the_right_way_up():
    image = Image.new("RGB", (5000, 3000), (200, 30, 30))
    exif = image.getexif()
    exif[EXIF_ORIENTATION] = 6                      # "rotate 90°": the camera was held upright
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    fitted = Image.open(io.BytesIO(own_photo(buffer.getvalue()).data))
    assert fitted.size == (round(3000 * MAX_SIDE / 5000), MAX_SIDE)   # upright now, and smaller
    assert fitted.getexif().get(EXIF_ORIENTATION, 1) == 1


def test_a_small_picture_is_kept_byte_for_byte_and_a_transparent_logo_stays_transparent():
    small = picture((800, 600))
    assert fit_for_slides(small) == small
    logo = Image.open(io.BytesIO(fit_for_slides(picture((3000, 1000), mode="RGBA"), max_side=1200)))
    assert logo.format == "PNG" and logo.mode == "RGBA" and logo.size == (1200, 400)


@pytest.mark.parametrize("junk", [b"", b"not a picture", picture((10, 10))[:40]])
def test_junk_is_not_a_picture(junk):
    with pytest.raises(ValueError):
        own_photo(junk)


# ----- documents and tables ------------------------------------------------------------------

def small_docx():
    document = docx.Document()
    document.add_paragraph("Hello")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_a_document_that_would_unpack_to_too_much_is_refused(monkeypatch):
    monkeypatch.setattr(documents, "MAX_UNPACKED", 1000)        # a real bomb would take seconds to build
    with pytest.raises(DocumentReadError) as caught:
        extract_text_from_file(Upload("bomb.docx", small_docx()))
    assert caught.value.reason == "too_big"


def test_the_archive_check_reads_sizes_without_unpacking():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.xml", b"0" * 5_000_000)
    assert len(buffer.getvalue()) < 50_000                     # 5 MB of zeros pack into a few KB
    documents.check_archive(buffer.getvalue())                  # under the limit: fine
    with pytest.raises(ValueError, match="not a zip"):
        documents.check_archive(b"plain text")


def test_a_data_workbook_that_would_unpack_to_too_much_is_refused(monkeypatch):
    import openpyxl
    workbook = openpyxl.Workbook()
    workbook.active.append(["Year", "Sales"])
    workbook.active.append([2024, 5])
    buffer = io.BytesIO()
    workbook.save(buffer)
    monkeypatch.setattr(documents, "MAX_UNPACKED", 1000)
    with pytest.raises(data.DataError):
        data.read_tables("sales.xlsx", buffer.getvalue())


def test_a_long_pdf_is_read_only_as_far_as_the_text_is_needed(monkeypatch):
    pymupdf = pytest.importorskip("pymupdf")
    pdf = pymupdf.open()
    for number in range(30):
        pdf.new_page().insert_text((72, 72), f"Page {number} " + "word " * 60)
    monkeypatch.setattr(documents, "MAX_TEXT", 1000)
    text = extract_text_from_file(Upload("long.pdf", pdf.tobytes()))
    assert "Page 0" in text and "Page 29" not in text


# ----- project files and answers --------------------------------------------------------------

@pytest.mark.parametrize("text", ["[" * 100_000 + "]" * 100_000,
                                  '{"title": "t", "slides": ' + "[" * 100_000 + "]" * 100_000 + "}"])
def test_json_nested_thousands_of_levels_deep_is_refused_clearly(text):
    with pytest.raises(ContentError):
        parse_deck(text)
    with pytest.raises(ContentError):
        load_project(text)


def test_a_project_with_photos_in_the_wrong_shape_still_opens():
    project = json.loads(save_project(SAMPLE_DECK, {}, "minimal", "Corporate Blue"))
    project["photos"] = [1, 2, 3]
    opened = load_project(json.dumps(project))
    assert opened["photos"] == {} and opened["deck"].title == SAMPLE_DECK.title


VALID_PROJECT = json.loads(save_project(
    SAMPLE_DECK, {SAMPLE_IMAGE: Photo(data=sample_photo(), preview_url="", author="A")}, "bold", "Dark Modern",
    settings={"tone": "x"}, transition="fade", logo=picture((60, 30))))


@pytest.mark.parametrize("seed", range(200))
def test_a_damaged_project_file_opens_or_is_refused_clearly(seed):
    rng = random.Random(seed)
    text = json.dumps(damage(VALID_PROJECT, rng))
    try:
        opened = load_project(text)
    except ContentError:
        return
    assert opened["deck"].slides
    assert isinstance(opened["photos"], dict) and isinstance(opened["settings"], dict)


def test_settings_from_a_file_are_checked_one_by_one():
    from generator.project import DEFAULT_SETTINGS, clean_settings
    assert clean_settings(None) == DEFAULT_SETTINGS
    odd = {"tone": ["x"], "text_amount": "Huge", "goal": "pitch", "speaker_notes": "yes", "auto_review": False,
           "audience": "  seed\n investors " + "x" * 500, "minutes": 10_000}
    cleaned = clean_settings(odd)
    assert cleaned["tone"] == DEFAULT_SETTINGS["tone"] and cleaned["text_amount"] == "Balanced"
    assert cleaned["goal"] == "pitch" and cleaned["auto_review"] is False and cleaned["speaker_notes"] is True
    assert cleaned["audience"].startswith("seed investors x") and len(cleaned["audience"]) == 200
    assert cleaned["minutes"] is None


def test_custom_colours_out_of_range_are_brought_into_range():
    project = json.loads(save_project(SAMPLE_DECK, {}, "minimal", "Corporate Blue"))
    project["theme"] = {"bg": [-5, 300, 10], "title": [0, 0, 0], "text": [1, 2, 3], "accent": [9, 9, 9]}
    assert load_project(json.dumps(project))["theme"]["bg"] == (0, 255, 10)
