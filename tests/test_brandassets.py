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


def test_icon_colours_can_name_tokens(ba, tmp_path):
    # Iron Law 4: the icon ground and ink are tokens, not copied hex values.
    (tmp_path / "tokens.css").write_text(
        ":root { --b-ground: #07110f; --b-ink: #f0efe9; }\n"
        ":root[data-theme='dark'] { --b-ground: #f0efe9; --b-ink: #07110f; }\n")
    colours = ba.resolve_icon_colours(tmp_path / "tokens.css", "--b-ground", "--b-ink",
                                      "--b-ground", "--b-ink")
    assert colours == ("#07110f", "#f0efe9", "#f0efe9", "#07110f")


@browser
def test_a_share_card_rendered_before_its_page_changed_is_stale(run, ba_run, fixture_font, tmp_path):
    a = tmp_path / "assets"
    a.mkdir()
    (a / "mark.svg").write_text(MARK_SVG)
    ba_run("wordmark", fixture_font, "--text", "RAV", "-o", a / "wordmark.svg")
    ba_run("icons", a / "mark.svg", "--out", a, "--name", "Brand", "--bg", "#07110f",
           "--fg", "#f0efe9")
    card = tmp_path / "og-card.html"
    card.write_text("<!doctype html><html><body style='margin:0;background:#07110f'>A</body></html>")
    ba_run("png", card, "--size", "1200x630", "-o", a / "og-default.png")
    code, out = run("assets", tmp_path)
    assert code == 0, out
    card.write_text("<!doctype html><html><body style='margin:0;background:#07110f'>B</body></html>")
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "stale" in out and "og-default.png" in out


@browser
def test_icons_rendered_before_the_mark_changed_are_stale(run, ba_run, fixture_font, tmp_path):
    a = tmp_path / "assets"
    a.mkdir()
    (a / "mark.svg").write_text(MARK_SVG)
    ba_run("icons", a / "mark.svg", "--out", a, "--name", "Brand", "--bg", "#07110f",
           "--fg", "#f0efe9")
    (a / "mark.svg").write_text(MARK_SVG.replace("M16 16h32v32H16z", "M20 20h24v24H20z"))
    code, out = run("assets", tmp_path)
    assert "stale" in out and "mark.svg" in out


def test_icon_colour_flags_accept_token_names_on_the_command_line(ba):
    # `--bg --b-x` reads the token as a new option; `--bg=--b-x` and var() work.
    args = ba.build_parser().parse_args(
        ["icons", "m.svg", "--out", "o", "--name", "B", "--bg=--b-ground",
         "--fg", "var(--b-ink)"])
    assert args.bg == "--b-ground" and args.fg == "var(--b-ink)"


def test_var_syntax_names_a_token_too(ba, tmp_path):
    (tmp_path / "tokens.css").write_text(":root { --b-ground: #07110f; --b-ink: #f0efe9; }\n")
    colours = ba.resolve_icon_colours(tmp_path / "tokens.css", "var(--b-ground)", "--b-ink")
    assert colours[:2] == ("#07110f", "#f0efe9")
