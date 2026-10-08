"""boardcheck: text that runs out of its slide, its poster or its clipping box."""
import pytest

from conftest import ROOT, browser_available

pytestmark = pytest.mark.skipif(not browser_available(), reason="no Playwright browser")

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:sans-serif}
.slide{width:1600px;height:900px;position:relative;overflow:hidden;background:#f0efe9;color:#07110f}
.poster{position:absolute;left:100px;top:100px;width:560px;height:700px;background:#07110f;
        color:#fff;padding:40px}
.poster h2{font-size:104px;line-height:1}
.cap{position:absolute;width:400px;background:#fff;padding:16px;font-size:20px}
</style></head><body>%s</body></html>"""

CLEAN = """<section class="slide">
  <div class="poster"><h2>Never<br>miss<br>a call</h2><p>Example poster</p></div>
  <div class="cap" style="right:90px;bottom:90px">Example: booked for 3pm</div>
  <p style="position:absolute;left:900px;top:100px;font-size:40px">A headline that fits</p>
</section>"""

SPILL = """<section class="slide">
  <div class="poster"><h2 style="white-space:nowrap">Never miss a call</h2></div>
</section>"""

# The caption's wrapper has no size and sits at the slide's corner, so the
# caption is laid out entirely past the right and bottom edges.
OFF_SLIDE = """<section class="slide">
  <div style="position:absolute;right:0;bottom:0;width:0;height:0">
    <div class="cap" style="left:40px;top:40px">Example: booked for 3pm</div>
  </div>
</section>"""

OVERLAP = """<section class="slide">
  <p style="position:absolute;left:100px;top:100px;font-size:48px">First label here</p>
  <p style="position:absolute;left:110px;top:105px;font-size:48px">Second label here</p>
</section>"""


def board(write, body, name="board.html"):
    return write(name, PAGE % body)


def test_a_clean_slide_passes(bdc, cli, write):
    code, out = cli(bdc, board(write, CLEAN))
    assert code == 0, out
    assert "slide 1:" in out and "inside the slide" in out
    assert "WARN" not in out


def test_a_headline_spilling_past_its_poster_fails(bdc, cli, write):
    code, out = cli(bdc, board(write, SPILL))
    assert code == 1
    assert "Never miss a call" in out
    assert "spills" in out and "div.poster" in out


def test_a_caption_positioned_off_the_slide_fails(bdc, cli, write):
    code, out = cli(bdc, board(write, OFF_SLIDE))
    assert code == 1
    assert "booked for 3pm" in out and "off the 1600x900 slide" in out


def test_overlapping_text_warns_but_passes(bdc, cli, write):
    code, out = cli(bdc, board(write, OVERLAP))
    assert code == 0, out
    assert "WARN" in out and "overlap by" in out
    assert "First label here" in out and "Second label here" in out


def test_overlap_can_be_marked_deliberate(bdc, cli, write):
    code, out = cli(bdc, board(write, OVERLAP.replace("<p style", "<p data-overlap-ok style", 1)))
    assert code == 0
    assert "overlap by" not in out


def test_text_cut_off_by_a_clipping_box_fails(bdc, cli, write):
    body = ("<section class='slide'><div style='position:absolute;left:100px;top:100px;"
            "width:300px;height:80px;overflow:hidden'><p style='font-size:40px;"
            "white-space:nowrap'>A line far too long for its box</p></div></section>")
    code, out = cli(bdc, board(write, body))
    assert code == 1
    assert "cut off by div" in out


def test_a_deliberate_overhang_can_be_marked(bdc, cli, write):
    code, out = cli(bdc, board(write, SPILL.replace("<h2 ", "<h2 data-overflow-ok ")))
    assert code == 0, out


def test_text_under_another_element_warns(bdc, cli, write):
    body = ("<section class='slide'><p style='position:absolute;left:100px;top:100px;"
            "font-size:40px'>Hidden headline</p><div style='position:absolute;left:80px;"
            "top:80px;width:600px;height:120px;background:#c33'></div></section>")
    code, out = cli(bdc, board(write, body))
    assert code == 0, out
    assert "covered by div" in out


def test_each_slide_is_reported_by_its_number(bdc, cli, write):
    code, out = cli(bdc, board(write, CLEAN + SPILL))
    assert code == 1
    assert "slide 1:" in out and "slide 2: \"Never miss a call\"" in out


def test_no_matching_slide_fails_with_a_hint(bdc, cli, write):
    code, out = cli(bdc, board(write, "<main><p>Poster</p></main>"))
    assert code == 1 and "--slide-selector" in out
    code, out = cli(bdc, board(write, "<main><p>Poster</p></main>"), "--slide-selector", "main")
    assert code == 0, out


def test_vw_sized_slides_are_measured_at_the_starting_viewport(bdc, cli, write):
    page = ("<!doctype html><html><head><style>body{margin:0}.s{width:100vw;height:56.25vw;"
            "position:relative;overflow:hidden}</style></head><body><section class=s>"
            "<p style='position:absolute;right:20px;top:20px'>Corner</p></section></body></html>")
    code, out = cli(bdc, write("vw.html", page), "--slide-selector", "section.s",
                    "--viewport", "1280x720")
    assert code == 0, out
    assert "(1280x720)" in out


def test_the_board_template_passes(bdc, cli):
    template = ROOT / "skills" / "evidence-based-brand-systems" / "templates" / "board.html"
    code, out = cli(bdc, template, "--offline")
    assert code == 0, out
