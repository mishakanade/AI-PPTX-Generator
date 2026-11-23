"""Photo search and download, against a fake Unsplash (httpx's MockTransport answers instead).

The other tests replace fetch_photos as a whole; these check what it does inside: one distinct
photo per slide, the key sent in a header and never in the address, the credit line, the
download report Unsplash's terms ask for, and what happens on a refused key or a broken file.
"""
import httpx
import pytest

from generator.design.sample_deck import SAMPLE_DECK, sample_photo
from generator.images import unsplash

PHOTO = sample_photo()


def candidate(photo_id):
    return {"id": photo_id, "urls": {"regular": f"https://images.example/{photo_id}.jpg"},
            "user": {"name": f"Author {photo_id}", "links": {"html": f"https://unsplash.com/@{photo_id}"}},
            "links": {"download_location": f"https://api.unsplash.com/photos/{photo_id}/download"}}


class FakeUnsplash:
    """Answers searches from `results` ({query: [photo ids]}) and serves every photo."""

    def __init__(self, results, status=200, broken=()):
        self.results, self.status, self.broken = results, status, set(broken)
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        if request.url.path == "/search/photos":
            if self.status != 200:
                return httpx.Response(self.status, json={"errors": ["no"]})
            ids = self.results.get(request.url.params["query"], [])
            return httpx.Response(200, json={"results": [candidate(i) for i in ids]})
        if request.url.path.endswith("/download"):
            return httpx.Response(200, json={"url": "x"})
        photo_id = request.url.path.strip("/").removesuffix(".jpg")
        return httpx.Response(200, content=b"not a picture" if photo_id in self.broken else PHOTO)

    @property
    def reported(self):
        return sorted(r.url.path.split("/")[2] for r in self.requests if r.url.path.endswith("/download"))


@pytest.fixture
def fake(monkeypatch):
    def install(results, **kwargs):
        server = FakeUnsplash(results, **kwargs)
        real_client = httpx.Client
        monkeypatch.setattr(unsplash.httpx, "Client",
                            lambda **options: real_client(transport=httpx.MockTransport(server.handle), **options))
        return server
    return install


def test_every_slide_gets_its_own_photo_with_credit_and_a_download_report(fake):
    server = fake({"city": ["a", "b"], "street": ["a", "c"]})      # both searches find "a" first
    photos, warnings = unsplash.fetch_photos(["city", "street", "city", "", None], client_id="key-1")
    assert warnings == [] and set(photos) == {"city", "street"}
    assert photos["city"].photo_id == "a" and photos["street"].photo_id == "c"
    assert photos["street"].credit == "Photo by Author c on Unsplash"
    assert photos["street"].author_url.endswith("?utm_source=ai_pptx_generator&utm_medium=referral")
    assert photos["city"].preview_url.startswith("data:image/jpeg;base64,")
    assert server.reported == ["a", "c"]                            # only the photos actually used
    searches = [r for r in server.requests if r.url.path == "/search/photos"]
    assert all(r.headers["Authorization"] == "Client-ID key-1" for r in searches)
    assert all("key-1" not in str(r.url) for r in server.requests)  # never in an address (logs)


def test_a_refused_key_gives_a_warning_and_no_photos(fake):
    fake({"city": ["a"]}, status=401)
    assert unsplash.fetch_photos(["city"], client_id="wrong") == ({}, ["unsplash_limit"])


def test_a_broken_photo_is_left_out_and_not_reported(fake):
    server = fake({"city": ["a"], "street": ["b"]}, broken={"b"})
    photos, _ = unsplash.fetch_photos(["city", "street"], client_id="k")
    assert set(photos) == {"city"} and server.reported == ["a"]


def test_nothing_is_asked_without_a_key_or_keywords(fake, monkeypatch):
    server = fake({"city": ["a"]})
    monkeypatch.setattr(unsplash.config, "UNSPLASH_CLIENT_ID", None)
    assert unsplash.fetch_photos(["city"]) == ({}, [])
    assert unsplash.fetch_photos([], client_id="k") == ({}, [])
    assert server.requests == []


def test_another_photo_skips_the_ones_already_shown(fake):
    fake({"city": ["a", "b", "c"]})
    photo, warnings = unsplash.fetch_another("city", {"a", "b"}, client_id="k")
    assert photo.photo_id == "c" and warnings == []
    assert unsplash.fetch_another("city", {"a", "b", "c"}, client_id="k") == (None, [])


def test_another_photo_with_a_refused_key(fake):
    fake({}, status=403)
    assert unsplash.fetch_another("city", set(), client_id="k") == (None, ["unsplash_limit"])


def test_keywords_come_only_from_slides_that_can_show_a_photo():
    keywords = unsplash.keywords_for(SAMPLE_DECK)
    assert keywords and all(isinstance(k, str) and k for k in keywords)
    photo_slides = [s for s in SAMPLE_DECK.slides if s.type in ("bullets", "image") and s.image_keyword]
    assert keywords == [s.image_keyword for s in photo_slides]
