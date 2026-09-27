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


def claims(write):
    write("forbidden-claims.txt", "bank-grade\tno assessment\n")


def test_all_fails_without_a_style_tile(run, write, tmp_path):
    brand(write)
    claims(write)
    code, out = run("all", tmp_path)
    assert code == 1
    assert "style-tile.html" in out


def test_all_fails_when_the_rendered_layer_cannot_run(run, write, tmp_path, monkeypatch, bc):
    brand(write)
    claims(write)
    write("style-tile.html", "<!doctype html><html><body><p>x</p></body></html>")
    monkeypatch.setattr(bc, "playwright_ready", lambda: "no browser in this test")
    code, out = run("all", tmp_path)
    assert code == 1
    assert "FAIL  the rendered layer did not run" in out


def test_all_can_skip_render_only_when_told_to(run, write, tmp_path, monkeypatch, bc):
    brand(write)
    claims(write)
    write("style-tile.html", "<!doctype html><html><body><p>x</p></body></html>")
    monkeypatch.setattr(bc, "playwright_ready", lambda: "no browser in this test")
    code, out = run("all", tmp_path, "--no-render")
    assert "skipped by request" in out
    assert "did not run" not in out


def test_all_help_lists_what_all_runs(run, capsys, bc):
    import pytest as _pytest
    with _pytest.raises(SystemExit):
        bc.main(["all", "--help"])
    out = capsys.readouterr().out
    assert "tokens, contrast, lexicon, fonts, assets and render" in " ".join(out.split())


def test_all_fails_without_a_generated_tokens_json(run, write, tmp_path):
    brand(write)
    claims(write)
    code, out = run("all", tmp_path, "--no-render")
    assert "FAIL  no tokens.json" in out


def test_all_fails_a_hand_written_tokens_json(run, write, tmp_path):
    brand(write)
    claims(write)
    write("tokens.json", '{"b":{"ink":{"$type":"color","$value":{"colorSpace":"srgb",'
                         '"components":[0.066667,0.066667,0.066667],"hex":"#111111"}},'
                         '"paper":{"$type":"color","$value":{"colorSpace":"srgb",'
                         '"components":[1,1,1],"hex":"#ffffff"}}}}')
    code, out = run("all", tmp_path, "--no-render")
    assert "FAIL  tokens.json was not produced by `brandcheck export`" in out


def test_each_font_family_is_checked_against_its_own_licence(run, write, tmp_path, fixture_font):
    brand(write)
    for fam, lic in (("inter", "inter-LICENSE.txt"), ("plex", "ibm-plex-LICENSE.txt")):
        (tmp_path / "fonts" / fam).mkdir(parents=True)
        shutil.copy(fixture_font, tmp_path / "fonts" / fam / f"{fam}.ttf")
        shutil.copy(FIXTURES / "licences" / lic, tmp_path / "fonts" / fam / "OFL.txt")
    code, out = run("all", tmp_path, "--no-render")
    inter = out.split("FONTS · inter.ttf")[1].split("FONTS ·")[0]
    plex = out.split("FONTS · plex.ttf")[1].split("ASSETS")[0]
    assert "no Reserved Font Name declared" in inter
    assert 'Reserved Font Name "Plex"' in plex


def test_all_warns_when_no_fonts_ship(run, write, tmp_path):
    brand(write)
    code, out = run("all", tmp_path, "--no-render")
    assert "no fonts/" in out


def test_all_fails_bundled_fonts_it_cannot_read(run, write, tmp_path, fixture_font, monkeypatch):
    import builtins
    brand(write)
    (tmp_path / "fonts").mkdir()
    shutil.copy(fixture_font, tmp_path / "fonts" / "Brand.ttf")
    real_import = builtins.__import__

    def no_fonttools(name, *a, **k):
        if name.startswith("fontTools"):
            raise ImportError("no fontTools")
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_fonttools)
    code, out = run("all", tmp_path, "--no-render")
    assert "FAIL  fontTools not installed" in out
