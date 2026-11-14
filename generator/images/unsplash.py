"""Finding and downloading illustrations from Unsplash.

fetch_photos() does three steps:
  1. search   - ask Unsplash for a few candidate photos per keyword (in parallel),
  2. choose   - give each keyword the first candidate that no other slide already uses,
  3. download - load the chosen photos (in parallel), check them, make small previews.

Unsplash's API terms ask apps to credit the photographer and to report each photo that
is actually used; both are done here (see Photo.credit and _report_download).
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO

import httpx
from PIL import Image

from generator import config

API_URL = "https://api.unsplash.com"
CANDIDATES_PER_KEYWORD = 5
PREVIEW_WIDTH = 640     # pixels; previews are embedded into the page, so they must be small
MAX_WORKERS = 4         # how many requests run at the same time


@dataclass
class Photo:
    data: bytes          # the image file that goes into the .pptx
    preview_url: str     # a small copy as a data: URL, for the preview in the browser
    author: str
    author_url: str

    @property
    def credit(self):
        return f"Photo by {self.author} on Unsplash"


class UnsplashLimitError(Exception):
    """Unsplash refused the request: wrong key or the hourly request limit is used up."""


def _headers():
    # The key travels in a header, not in the address, so it does not end up in logs.
    return {"Authorization": f"Client-ID {config.UNSPLASH_CLIENT_ID}", "Accept-Version": "v1"}


def _search(client, keyword):
    """Return candidate photos for a keyword: a list of dicts from the Unsplash API."""
    response = client.get(
        f"{API_URL}/search/photos",
        params={"query": keyword.strip(), "per_page": CANDIDATES_PER_KEYWORD, "orientation": "landscape"},
        headers=_headers(),
    )
    if response.status_code in (401, 403):
        raise UnsplashLimitError()
    response.raise_for_status()
    return response.json().get("results", [])


def _make_preview(data):
    """Check that the bytes are a real image and return a small JPEG copy as a data: URL."""
    image = Image.open(BytesIO(data))
    image.load()                      # raises an error if the file is damaged
    image = image.convert("RGB")
    if image.width > PREVIEW_WIDTH:
        image = image.resize((PREVIEW_WIDTH, round(image.height * PREVIEW_WIDTH / image.width)))
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _report_download(client, candidate):
    """Tell Unsplash that the photo is used (required by their API terms). Failures are ignored."""
    try:
        client.get(candidate["links"]["download_location"], headers=_headers())
    except Exception:
        pass


def _download(client, candidate):
    """Download one chosen photo. Returns a Photo, or None if anything goes wrong."""
    try:
        response = client.get(candidate["urls"]["regular"])
        response.raise_for_status()
        photo = Photo(
            data=response.content,
            preview_url=_make_preview(response.content),
            author=candidate["user"]["name"],
            author_url=candidate["user"]["links"]["html"] + "?utm_source=ai_pptx_generator&utm_medium=referral",
        )
    except Exception:
        return None
    _report_download(client, candidate)
    return photo


def fetch_photos(keywords):
    """Find and download one photo per keyword.

    Returns (photos, warnings): photos is {keyword: Photo} and simply lacks the keywords
    for which nothing was found; warnings is a list of messages for the user.
    """
    keywords = list(dict.fromkeys(k for k in keywords if isinstance(k, str) and k.strip()))
    if not keywords or not config.UNSPLASH_CLIENT_ID:
        return {}, []

    warnings = []
    with httpx.Client(timeout=10, follow_redirects=True) as client, ThreadPoolExecutor(MAX_WORKERS) as pool:
        # 1. search, all keywords at once
        def safe_search(keyword):
            try:
                return _search(client, keyword)
            except UnsplashLimitError:
                return "limit"
            except Exception:
                return []
        found = dict(zip(keywords, pool.map(safe_search, keywords)))
        if "limit" in found.values():
            warnings.append(
                "Unsplash rejected some requests: the key is invalid or its hourly limit is used up, "
                "so some slides have no photo."
            )

        # 2. choose: the first candidate that is not already taken by another slide
        chosen, used_ids = {}, set()
        for keyword in keywords:
            candidates = found[keyword] if isinstance(found[keyword], list) else []
            pick = next((c for c in candidates if c["id"] not in used_ids), None)
            if pick:
                used_ids.add(pick["id"])
                chosen[keyword] = pick

        # 3. download, all chosen photos at once
        photos = dict(zip(chosen, pool.map(lambda c: _download(client, c), chosen.values())))

    return {keyword: photo for keyword, photo in photos.items() if photo}, warnings


def keywords_for(deck):
    """The search phrases of all slides of a deck that can show a photo."""
    return [slide.image_keyword for slide in deck.slides
            if slide.type in ("bullets", "image") and slide.image_keyword]
