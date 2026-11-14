"""Finding and downloading illustrations from Unsplash."""
import json
import urllib.parse
import urllib.request
from io import BytesIO

from generator import config


def fetch_image_bytes(keyword: str):
    """Load an image from Unsplash by keyword"""
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
            return BytesIO(img_resp.read())
    except Exception:
        return None
