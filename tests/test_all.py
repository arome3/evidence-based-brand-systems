"""`all` runs every check that applies to a brand directory."""
import shutil

import pytest

from conftest import FIXTURES, browser_available

TOKENS = ":root { --b-ink: #111111; --b-paper: #ffffff; }\n"


def brand(write):
    write("tokens.css", TOKENS)
    write("pairs.tsv", "body\t--b-ink\t--b-paper\tnormal\n")


@pytest.mark.skipif(not browser_available(), reason="no Playwright browser")
def test_all_renders_the_style_tile(run, write, tmp_path):
    brand(write)
    write("style-tile.html", "<!doctype html><html><head><style>" + TOKENS +
          "body{background:var(--b-paper);color:var(--b-ink)}</style></head>"
          "<body><p>Copy.</p></body></html>")
    code, out = run("all", tmp_path)
    assert "RENDER" in out


def test_all_checks_every_bundled_font_against_its_licence(run, write, tmp_path, fixture_font):
    brand(write)
    (tmp_path / "fonts").mkdir()
    shutil.copy(fixture_font, tmp_path / "fonts" / "Brand.ttf")
    shutil.copy(FIXTURES / "licences" / "inter-LICENSE.txt", tmp_path / "fonts" / "OFL.txt")
    code, out = run("all", tmp_path)
    assert "FONTS · Brand.ttf" in out
    assert "licence file present" in out


def test_all_fails_a_bundled_font_without_its_licence(run, write, tmp_path, fixture_font):
    brand(write)
    (tmp_path / "fonts").mkdir()
    shutil.copy(fixture_font, tmp_path / "fonts" / "Brand.ttf")
    code, out = run("all", tmp_path)
    assert code == 1
    assert "licence" in out
