"""brandassets builds the files the guidelines specify; brandcheck verifies them."""
import json
import re

import pytest

from conftest import browser_available
from fontfactory import ADVANCES, KERN_AV
from imgutil import MARK_SVG

browser = pytest.mark.skipif(not browser_available(), reason="no Playwright browser")


def test_layout_applies_the_fonts_kerning(ba, fixture_font):
    placed = ba.layout(fixture_font, "AV")
    assert [g.name for g in placed] == ["A", "V"]
    assert placed[1].x == ADVANCES["A"] + KERN_AV


def test_tracking_is_added_between_glyphs_in_em(ba, fixture_font):
    placed = ba.layout(fixture_font, "AV", tracking=0.1)
    assert placed[1].x == ADVANCES["A"] + KERN_AV + 100


def test_the_wordmark_is_outlined_and_records_its_construction(ba_run, fixture_font, tmp_path):
    out = tmp_path / "assets" / "wordmark.svg"
    code, _ = ba_run("wordmark", fixture_font, "--text", "RAV", "-o", out)
    assert code == 0
    svg = out.read_text()
    assert "<text" not in svg and "viewBox" in svg and 'fill="currentColor"' in svg
    record = json.loads(re.search(r"<metadata>(.*?)</metadata>", svg, re.S).group(1))
    assert record["text"] == "RAV"
    assert len(record["fontSha256"]) == 64
    assert record["unitsPerEm"] == 1000


def test_the_wordmark_passes_the_logo_check(run, ba_run, fixture_font, tmp_path):
    ba_run("wordmark", fixture_font, "--text", "RAV", "-o", tmp_path / "assets" / "wordmark.svg")
    code, out = run("assets", tmp_path)
    assert "wordmark.svg: outlined, self-contained vector" in out
    assert "construction record" not in out


def test_a_translucent_icon_ground_is_refused(ba_run, tmp_path):
    (tmp_path / "mark.svg").write_text(MARK_SVG)
    code, out = ba_run("icons", tmp_path / "mark.svg", "--out", tmp_path, "--name", "Brand",
                       "--bg", "#07110f80", "--fg", "#f0efe9")
    assert code == 1
    assert "opaque" in out


@browser
def test_icons_and_a_share_card_make_a_set_that_passes(run, ba_run, fixture_font, tmp_path):
    a = tmp_path / "assets"
    a.mkdir()
    (a / "mark.svg").write_text(MARK_SVG)
    ba_run("wordmark", fixture_font, "--text", "RAV", "-o", a / "wordmark.svg")
    code, out = ba_run("icons", a / "mark.svg", "--out", a, "--name", "Brand",
                       "--bg", "#07110f", "--fg", "#f0efe9", "--dark-bg", "#f0efe9",
                       "--dark-fg", "#07110f")
    assert code == 0, out
    card = tmp_path / "og.html"
    card.write_text("<!doctype html><html><body style='margin:0;background:#07110f;color:#f0efe9'>"
                    "<h1 style='font:700 72px system-ui;margin:80px'>Brand</h1></body></html>")
    code, out = ba_run("png", card, "--size", "1200x630", "-o", a / "og-default.png")
    assert code == 0, out
    code, out = run("assets", tmp_path)
    assert code == 0, out


@browser
def test_a_wide_mark_stays_inside_the_maskable_safe_zone(run, ba_run, tmp_path):
    a = tmp_path / "assets"
    a.mkdir()
    (a / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 20">'
                                '<path d="M0 0h200v20H0z"/></svg>')
    ba_run("icons", a / "mark.svg", "--out", a, "--name", "Brand", "--bg", "#07110f",
           "--fg", "#f0efe9")
    code, out = run("assets", tmp_path)
    assert "icon-mask.png: 512x512, inside the maskable safe zone" in out
    assert "avatar.png: 400x400, survives a circular crop" in out


@browser
def test_png_renders_offline_at_the_requested_size(bc, ba_run, tmp_path):
    page = tmp_path / "card.html"
    page.write_text("<!doctype html><html><head>"
                    "<link rel=stylesheet href='https://example.invalid/x.css'></head>"
                    "<body style='margin:0;background:#fff'>Card</body></html>")
    code, out = ba_run("png", page, "--size", "1200x630", "-o", tmp_path / "card.png")
    assert code == 0, out
    img = bc.read_png(str(tmp_path / "card.png"), decode=False)
    assert (img.width, img.height) == (1200, 630)


@browser
def test_the_review_sheet_is_self_contained(ba_run, fixture_font, tmp_path):
    a = tmp_path / "assets"
    a.mkdir()
    (a / "mark.svg").write_text(MARK_SVG)
    ba_run("wordmark", fixture_font, "--text", "RAV", "-o", a / "wordmark.svg")
    ba_run("icons", a / "mark.svg", "--out", a, "--name", "Brand", "--bg", "#07110f",
           "--fg", "#f0efe9")
    code, out = ba_run("sheet", a)
    assert code == 0, out
    html = (a / "asset-sheet.html").read_text()
    assert "data:image/png;base64," in html
    assert not re.search(r"""(?:src|href)=["'](?!data:|#)""", html)
