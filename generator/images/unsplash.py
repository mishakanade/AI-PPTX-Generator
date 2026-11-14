"""Finding and downloading illustrations from Unsplash."""
import json
import urllib.parse
import urllib.request

from generator import config


def fetch_image_bytes(keyword: str):
    """Find a photo on Unsplash by keyword and return its bytes, or None if nothing was found."""
    if not config.UNSPLASH_CLIENT_ID:
        return None  # no key: skip the request instead of waiting for it to be rejected
    clean_keyword = urllib.parse.quote(keyword.strip())
    api_url = f"https://api.unsplash.com/search/photos?query={clean_keyword}&per_page=1&orientation=landscape&client_id={config.UNSPLASH_CLIENT_ID}"
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = data.get("results", [])
        if not results:
            return None
        img_url = results[0]["urls"]["regular"]
        img_req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(img_req, timeout=7) as img_resp:
            return img_resp.read()
    except Exception:
        return None


def fetch_images_for_slides(slides_data):
    """Download the picture for every slide once.

    Returns a dict {image_keyword: image bytes}. Slides whose picture was not found
    are simply absent from it. The renderer takes this dict, so the same pictures can
    be reused when the presentation is rebuilt in another theme.
    """
    images = {}
    for slide_info in slides_data.get("slides", []):
        keyword = slide_info.get("image_keyword")
        if not isinstance(keyword, str) or not keyword.strip() or keyword in images:
            continue
        image = fetch_image_bytes(keyword)
        if image:
            images[keyword] = image
    return images
