"""photosource: CC0 stand-ins, picked by number from a sheet, recorded in SOURCES.tsv.

No test touches the network: urlopen is replaced by a fake that serves the
saved search page and generated images, and refuses anything else.
"""
import io
import json
import urllib.request

import pytest

from conftest import FIXTURES

SEARCH_HTML = (FIXTURES / "nappy-search.html").read_bytes()
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@pytest.fixture
def web(ps, monkeypatch):
    """Serve URLs from a dict; record every request; refuse anything unlisted."""
    routes, seen = {}, []

    def urlopen(req, timeout=None):
        url = req.full_url if isinstance(req, urllib.request.Request) else req
        seen.append(url)
        for prefix, body in routes.items():
            if url.startswith(prefix):
                return FakeResponse(body() if callable(body) else body)
        raise OSError(f"network blocked in tests: {url}")

    monkeypatch.setattr(ps.urllib.request, "urlopen", urlopen)
    return routes, seen


def jpeg(colour=(120, 80, 40)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), colour).save(buf, "JPEG")
    return buf.getvalue()


def test_results_are_parsed_in_order_without_the_navigation_thumbnails(ps):
    found = ps.parse_candidates(SEARCH_HTML.decode(), "nappy")
    assert [c["id"] for c in found] == ["77ZSlAKXxaOxfCbGms6UP", "oKvr_lYyu4MjV-u8tnvwZ",
                                        "9DQCDQvC9LxZg6pd-QJY3"]
    first, second, third = found
    assert first["url"] == "https://images.nappy.co/photo/77ZSlAKXxaOxfCbGms6UP.jpg"
    assert first["page"] == "https://nappy.co/photo/woman-on-phone-call%2B77ZSlAKXxaOxfCbGms6UP"
    assert first["title"] == "Woman on a phone call"
    assert second["title"] == "Man & his phone"
    assert third["url"].endswith(".png")


def test_a_page_with_no_photo_links_still_yields_its_images(ps):
    page = '<img src="https://images.nappy.co/photo/abc_DEF-123.jpg?width=10" alt="x">'
    assert [c["id"] for c in ps.parse_candidates(page, "nappy")] == ["abc_DEF-123"]


def test_the_search_url_quotes_multi_word_terms(ps):
    assert ps.search_url("nappy", "woman on phone") == "https://nappy.co/search/woman%20on%20phone"


def test_every_source_declares_what_search_and_get_need(ps):
    for name, cfg in ps.SOURCES.items():
        for key in ("site", "search", "image", "thumb", "full", "licence"):
            assert cfg.get(key), f"{name} lacks {key}"
        assert "{q}" in cfg["search"] and "(?P<id>" in cfg["image"]
    assert ps.SOURCES["nappy"]["licence"] == "CC0 1.0 — nappy.co/license"


def test_search_writes_numbered_candidates_thumbnails_and_sheets(ps, cli, web, tmp_path):
    pytest.importorskip("PIL", reason="the sheets need Pillow")
    routes, seen = web
    routes["https://nappy.co/search/"] = SEARCH_HTML
    routes["https://images.nappy.co/photo/"] = jpeg
    code, out = cli(ps, "search", "phone", "--out", tmp_path)
    assert code == 0, out
    cands = json.loads((tmp_path / "candidates.json").read_text())
    assert [c["n"] for c in cands] == [1, 2, 3]
    assert {c["term"] for c in cands} == {"phone"}
    assert all((tmp_path / c["thumb"]).exists() for c in cands)
    assert (tmp_path / "sheet0.jpg").exists()
    thumbs = [u for u in seen if u.startswith("https://images.nappy.co/")]
    assert thumbs and all(u.endswith(ps.SOURCES["nappy"]["thumb"]) for u in thumbs)


def test_a_second_search_keeps_the_numbers_and_adds_only_new_photos(ps, cli, web, tmp_path):
    pytest.importorskip("PIL", reason="the sheets need Pillow")
    routes, _ = web
    routes["https://nappy.co/search/phone"] = SEARCH_HTML
    routes["https://nappy.co/search/call"] = (
        b'<a href="/photo/call%2BNEW_id-1"><img src="https://images.nappy.co/photo/NEW_id-1.jpg"'
        b' alt="New"></a><a href="/photo/x%2B77ZSlAKXxaOxfCbGms6UP"><img '
        b'src="https://images.nappy.co/photo/77ZSlAKXxaOxfCbGms6UP.jpg"></a>')
    routes["https://images.nappy.co/photo/"] = jpeg
    cli(ps, "search", "phone", "--out", tmp_path)
    code, out = cli(ps, "search", "call", "--out", tmp_path)
    assert code == 0, out
    cands = json.loads((tmp_path / "candidates.json").read_text())
    assert [(c["n"], c["id"]) for c in cands][-1] == (4, "NEW_id-1")
    assert len(cands) == 4


def test_a_failed_thumbnail_is_listed_but_warned(ps, cli, web, tmp_path):
    pytest.importorskip("PIL", reason="the sheets need Pillow")
    routes, _ = web
    routes["https://nappy.co/search/"] = SEARCH_HTML
    routes["https://images.nappy.co/photo/77Z"] = b"<html>blocked</html>"
    routes["https://images.nappy.co/photo/"] = jpeg
    code, out = cli(ps, "search", "phone", "--out", tmp_path)
    assert code == 0, out
    assert "#1: no thumbnail" in out
    cands = json.loads((tmp_path / "candidates.json").read_text())
    assert cands[0]["thumb"] is None and cands[1]["thumb"]


def test_a_search_that_cannot_fetch_fails(ps, cli, web, tmp_path):
    code, out = cli(ps, "search", "phone", "--out", tmp_path)
    assert code == 1 and "cannot fetch" in out


def _candidates(tmp_path):
    cands = [{"n": 1, "source": "nappy", "id": "77ZSlAKXxaOxfCbGms6UP", "term": "phone",
              "url": "https://images.nappy.co/photo/77ZSlAKXxaOxfCbGms6UP.jpg",
              "page": "https://nappy.co/photo/woman-on-phone-call%2B77ZSlAKXxaOxfCbGms6UP",
              "title": "Woman on a phone call", "thumb": "thumbs/001.jpg"},
             {"n": 2, "source": "nappy", "id": "9DQCDQvC9LxZg6pd-QJY3", "term": "phone",
              "url": "https://images.nappy.co/photo/9DQCDQvC9LxZg6pd-QJY3.png", "page": None,
              "title": "", "thumb": None}]
    (tmp_path / "candidates.json").write_text(json.dumps(cands))
    return cands


def test_get_downloads_full_size_and_appends_sources_rows(ps, cli, web, tmp_path):
    routes, seen = web
    routes["https://images.nappy.co/photo/77Z"] = JPEG_MAGIC
    routes["https://images.nappy.co/photo/9DQ"] = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    _candidates(tmp_path)
    hi = tmp_path / "hi"
    code, out = cli(ps, "get", tmp_path, 1, 2, "--out", hi)
    assert code == 0, out
    assert seen == ["https://images.nappy.co/photo/77ZSlAKXxaOxfCbGms6UP.jpg"
                    + ps.SOURCES["nappy"]["full"],
                    "https://images.nappy.co/photo/9DQCDQvC9LxZg6pd-QJY3.png"
                    + ps.SOURCES["nappy"]["full"]]
    assert (hi / "nappy-77ZSlAKXxaOxfCbGms6UP.jpg").read_bytes() == JPEG_MAGIC
    assert (hi / "nappy-9DQCDQvC9LxZg6pd-QJY3.png").exists()
    rows = [r.split("\t") for r in (hi / "SOURCES.tsv").read_text().splitlines()]
    assert rows[0] == ["file", "source_url", "page_url", "source_site", "licence", "fetched",
                       "use"]
    assert len(rows) == 3
    f, url, page, site, licence, fetched, use = rows[1]
    assert f == "nappy-77ZSlAKXxaOxfCbGms6UP.jpg"
    assert url == "https://images.nappy.co/photo/77ZSlAKXxaOxfCbGms6UP.jpg"
    assert page.startswith("https://nappy.co/photo/")
    assert (site, licence) == ("nappy.co", "CC0 1.0 — nappy.co/license")
    assert len(fetched) == 10 and fetched[4] == "-"
    assert use == "stand-in: replace with commissioned photography; never present as a customer"
    assert rows[2][2] == ""                         # no page URL known: the cell stays empty


def test_getting_a_photo_twice_does_not_duplicate_its_row(ps, cli, web, tmp_path):
    routes, _ = web
    routes["https://images.nappy.co/photo/"] = JPEG_MAGIC
    _candidates(tmp_path)
    cli(ps, "get", tmp_path, 1, "--out", tmp_path / "hi")
    code, out = cli(ps, "get", tmp_path, 1, "--out", tmp_path / "hi")
    assert code == 0 and "already in SOURCES.tsv" in out
    assert len((tmp_path / "hi" / "SOURCES.tsv").read_text().splitlines()) == 2


def test_get_refuses_an_unknown_number_and_a_non_image(ps, cli, web, tmp_path):
    routes, _ = web
    routes["https://images.nappy.co/photo/"] = b"<!doctype html><p>Access denied"
    _candidates(tmp_path)
    code, out = cli(ps, "get", tmp_path, 1, 9, "--out", tmp_path / "hi")
    assert code == 1
    assert "#9: not in" in out and "did not return an image" in out
    assert not (tmp_path / "hi" / "SOURCES.tsv").exists()


def test_get_without_a_search_fails(ps, cli, tmp_path):
    code, out = cli(ps, "get", tmp_path, 1, "--out", tmp_path / "hi")
    assert code == 1 and "run photosource search first" in out
