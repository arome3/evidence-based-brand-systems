"""refcapture: references captured as images, in order, with a record.

The browser tests load local pages over file://, so nothing touches the network.
"""
import json

import pytest

from conftest import browser_available

browser = pytest.mark.skipif(not browser_available(), reason="no Playwright browser")


# ── pure logic ──

def test_frames_step_down_the_page_and_end_flush_with_the_bottom(rc):
    assert rc.frame_positions(2600, 900, 900) == [0, 900, 1700]
    assert rc.frame_positions(2700, 900, 900) == [0, 900, 1800]
    assert rc.frame_positions(600, 900, 900) == [0]


def test_a_long_page_is_sampled_evenly_within_the_frame_cap(rc):
    pos = rc.frame_positions(20900, 900, 900, max_frames=5)
    assert pos == [0, 5000, 10000, 15000, 20000]


def test_slugs_are_short_and_filesystem_safe(rc):
    assert rc.slug("https://www.Example.com/work/one?x=1") == "example-com-work-one"
    assert rc.slug("file:///tmp/My Board.html") == "my-board"
    assert len(rc.slug("https://a.com/" + "x" * 200)) <= 60


@pytest.mark.parametrize("label", ["Reject all", "Reject All Cookies", "Decline", "Deny",
                                   "Necessary only", "Only necessary cookies",
                                   "Use necessary cookies only", "Accept only essential cookies",
                                   "Continue without accepting", "No thanks"])
def test_reject_labels_are_recognised(rc, label):
    assert rc.is_reject_label(label)


@pytest.mark.parametrize("label", ["Accept all", "Accept", "Accept cookies", "OK", "Got it",
                                   "Agree", "I agree", "Allow all", "Manage preferences",
                                   "Accept all and reject later", ""])
def test_nothing_that_accepts_is_ever_a_reject_label(rc, label):
    assert not rc.is_reject_label(label)


def test_renditions_of_one_image_are_one_image_kept_in_page_order(rc):
    found = [
        {"src": "https://cdn.behance.net/project_modules/max_1200/aaa.jpg", "w": 1200},
        {"src": "https://cdn.behance.net/project_modules/disp/bbb.png", "w": 600},
        {"src": "https://cdn.behance.net/project_modules/1400/aaa.jpg", "w": 1400},
        {"src": "https://cdn.example.com/c.jpg?resize=800", "w": 800},
        {"src": "https://cdn.example.com/c.jpg?resize=1600", "w": 1600},
    ]
    out = rc.dedupe(found)
    assert [o["src"] for o in out] == [
        "https://cdn.behance.net/project_modules/1400/aaa.jpg",
        "https://cdn.behance.net/project_modules/disp/bbb.png",
        "https://cdn.example.com/c.jpg?resize=1600"]


def test_behance_projects_match_their_module_images(rc):
    assert rc.default_match("https://www.behance.net/gallery/1/x") == "project_modules"
    assert rc.default_match("https://dribbble.com/shots/1") is None


def test_the_index_keeps_one_record_per_url(rc, tmp_path):
    rc.save_record(tmp_path, {"kind": "site", "url": "https://a.com", "files": ["1"]})
    rc.save_record(tmp_path, {"kind": "site", "url": "https://b.com", "files": ["2"]})
    rc.save_record(tmp_path, {"kind": "site", "url": "https://a.com", "files": ["3"]})
    recs = json.loads((tmp_path / "index.json").read_text())
    assert [(r["url"], r["files"]) for r in recs] == [("https://b.com", ["2"]),
                                                     ("https://a.com", ["3"])]


# ── in a browser ──

CONSENT_PAGE = """<!doctype html><html><head><title>Fixture site</title><style>
body{margin:0;font:16px sans-serif}.tall{height:2600px;background:linear-gradient(#fff,#ccc)}
#banner{position:fixed;left:0;right:0;bottom:0;padding:20px;background:#222;color:#fff}
</style></head><body><div class="tall">Top of the page</div>
<div id="banner">We use cookies.
  <button onclick="document.title='ACCEPTED';this.parentNode.remove()">Accept all</button>
  %s
</div></body></html>"""


@browser
def test_site_captures_frames_and_a_full_page_and_only_ever_rejects(rc, cli, tmp_path):
    page = tmp_path / "site.html"
    page.write_text(CONSENT_PAGE % "<button onclick=\"this.parentNode.remove()\">Reject all</button>")
    out = tmp_path / "refs"
    code, text = cli(rc, "site", page, "--out", out, "--widths", "800,390", "--wait", "50")
    assert code == 0, text
    rec = json.loads((out / "index.json").read_text())[0]
    assert rec["kind"] == "site" and rec["url"] == page.resolve().as_uri()
    assert rec["title"] == "Fixture site"                 # never "ACCEPTED"
    assert rec["consent"] == {"800": "Reject all", "390": "Reject all"}
    assert rec["files"] == ["site-800-f01.png", "site-800-f02.png", "site-800-f03.png",
                            "site-800-full.png",
                            "site-390-f01.png", "site-390-f02.png", "site-390-f03.png",
                            "site-390-full.png"]
    assert all((out / f).exists() for f in rec["files"])
    assert rec["date"].endswith("+00:00")


@browser
def test_a_banner_without_a_reject_button_is_left_alone(rc, cli, tmp_path):
    page = tmp_path / "accept-only.html"
    page.write_text(CONSENT_PAGE % "")
    out = tmp_path / "refs"
    code, text = cli(rc, "site", page, "--out", out, "--widths", "800", "--wait", "50")
    assert code == 0, text
    rec = json.loads((out / "index.json").read_text())[0]
    assert rec["title"] == "Fixture site"
    assert rec["consent"] == {"800": None}
    assert "left in place" in text


def _png(path, w, h, colour):
    from PIL import Image
    Image.new("RGB", (w, h), colour).save(path)


@browser
def test_project_downloads_large_images_in_page_order_and_makes_sheets(rc, cli, tmp_path):
    pytest.importorskip("PIL", reason="project needs Pillow")
    site = tmp_path / "gallery"
    site.mkdir()
    _png(site / "one.png", 1000, 600, (200, 0, 0))
    _png(site / "two.png", 900, 900, (0, 200, 0))
    _png(site / "three.png", 1200, 800, (0, 0, 200))
    _png(site / "icon.png", 64, 64, (0, 0, 0))
    # three.png only arrives once the page has been scrolled to the bottom.
    (site / "index.html").write_text("""<!doctype html><html><head><title>Gallery</title>
<style>body{margin:0} img{display:block;width:600px} .gap{height:1500px}</style></head><body>
<img src="icon.png" style="width:32px"><img src="one.png"><div class="gap"></div>
<img src="two.png"><img src="two.png"><div class="gap" id="end"></div>
<script>
let added = false;
addEventListener('scroll', () => {
  if (!added && innerHeight + scrollY >= document.body.scrollHeight - 50) {
    added = true;
    const i = document.createElement('img'); i.src = 'three.png';
    document.body.appendChild(i);
  }
});
</script></body></html>""")
    out = tmp_path / "refs"
    code, text = cli(rc, "project", site / "index.html", "--out", out, "--wait", "50")
    assert code == 0, text
    rec = json.loads((out / "index.json").read_text())[0]
    assert rec["kind"] == "project" and rec["title"] == "Gallery"
    assert rec["files"] == ["01.jpg", "02.jpg", "03.jpg"]
    assert [i["src"].rsplit("/", 1)[-1] for i in rec["images"]] == ["one.png", "two.png",
                                                                      "three.png"]
    assert rec["sheets"] == ["sheet0.jpg"] and (out / "sheet0.jpg").exists()
    from PIL import Image
    with Image.open(out / "01.jpg") as im:
        assert im.size == (1000, 600)
        r, g, b = im.getpixel((500, 300))
        assert r > 150 and g < 60


@browser
def test_project_respects_the_download_cap(rc, cli, tmp_path):
    pytest.importorskip("PIL", reason="project needs Pillow")
    site = tmp_path / "g"
    site.mkdir()
    tags = ""
    for i in range(5):
        _png(site / f"{i}.png", 900, 500, (i * 40, 0, 0))
        tags += f'<img src="{i}.png">'
    (site / "index.html").write_text(f"<!doctype html><html><body>{tags}</body></html>")
    code, text = cli(rc, "project", site / "index.html", "--out", tmp_path / "o", "--max", "2",
                     "--wait", "50")
    assert code == 0, text
    assert "downloading the first 2" in text
    assert sorted(p.name for p in (tmp_path / "o").glob("[0-9]*.jpg")) == ["01.jpg", "02.jpg"]


@browser
def test_project_takes_the_largest_reasonable_srcset_candidate(rc, cli, tmp_path):
    pytest.importorskip("PIL", reason="project needs Pillow")
    site = tmp_path / "g"
    site.mkdir()
    for name, w in (("s.png", 400), ("l.png", 1600), ("xl.png", 4000)):
        _png(site / name, w, 100, (90, 90, 90))
    (site / "index.html").write_text(
        '<!doctype html><html><body><img src="s.png" '
        'srcset="s.png 400w, xl.png 4000w, l.png 1600w"></body></html>')
    code, text = cli(rc, "project", site / "index.html", "--out", tmp_path / "o", "--wait", "50")
    assert code == 0, text
    rec = json.loads((tmp_path / "o" / "index.json").read_text())[0]
    assert [i["src"].rsplit("/", 1)[-1] for i in rec["images"]] == ["l.png"]
