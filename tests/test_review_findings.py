"""Regression tests for the code review of v1.2 (each reproduced before fixing)."""
import json

import pytest

from conftest import browser_available
from imgutil import valid_assets

CLAIMS = "bank-grade\tno assessment\n"


def test_an_empty_share_card_png_fails_cleanly(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "og-default.png").write_bytes(b"")
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "og-default.png" in out


def test_a_truncated_png_fails_cleanly(run, tmp_path):
    a = valid_assets(tmp_path)
    blob = (a / "icon-mask.png").read_bytes()
    (a / "icon-mask.png").write_bytes(blob[:60])
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "icon-mask.png" in out


def test_a_second_occurrence_of_a_forbidden_claim_is_examined(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("04.md", 'Never write "bank-grade". Our controls are bank-grade.\n')
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_a_negation_in_one_clause_does_not_clear_the_next(run, write, tmp_path):
    write("01.md", "We banned the word seamless in our style guide, "
                   "yet our seamless checkout remains the highlight.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1
    assert "banned term 'seamless'" in out


def test_a_prohibition_list_after_a_colon_stays_suppressed(run, write, tmp_path):
    write("04.md", "Never use: seamless, revolutionary, synergy.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 0, out


def test_a_research_label_attaches_to_its_own_sentence(run, write, tmp_path):
    write("01.md", "[VERIFIED] Traffic grew. Trusted by leading teams.\n")
    code, out = run("lexicon", tmp_path, "--strict")
    assert code == 1


def test_unbalanced_css_fails_cleanly(run, write, tmp_path):
    write("tokens.css", ":root { --a: #ffffff; }\n@media (prefers-color-scheme: dark) {\n"
                        "  :root { --a: #000000;\n")
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "unbalanced" in out


def test_a_dtcg_colour_without_a_hex_fallback_compares_by_value(run, write, tmp_path):
    write("tokens.css", ":root { --b-c: #ff7f00; }\n")
    write("tokens.json", json.dumps({"b": {"c": {"$type": "color", "$value": {
        "colorSpace": "srgb", "components": [1, 0.498, 0]}}}}))
    code, out = run("tokens", tmp_path)
    assert "mismatch" not in out, out


def test_a_malformed_font_fails_cleanly(ba_run, tmp_path):
    bad = tmp_path / "bad.ttf"
    bad.write_bytes(b"not a font")
    code, out = ba_run("wordmark", bad, "--text", "A", "-o", tmp_path / "w.svg")
    assert code == 1


@pytest.mark.skipif(not browser_available(), reason="no Playwright browser")
def test_a_select_showing_its_default_option_is_checked(run, write):
    write("tokens.css", ":root { --b-ink: #111111; --b-paper: #ffffff; }\n")
    write("pairs.tsv", "body\t--b-ink\t--b-paper\tnormal\n")
    page = write("style-tile.html", "<!doctype html><html><head><style>"
                 ":root { --b-ink: #111111; --b-paper: #ffffff; }"
                 "body{margin:0;background:var(--b-paper);color:var(--b-ink)}"
                 "select{color:#c8c8c8;background:var(--b-paper);border:0}"
                 "</style></head><body><p>Body.</p><select>"
                 "<option value='' selected>Choose a plan</option></select></body></html>")
    code, out = run("render", page)
    assert code == 1
    assert "Choose a plan" in out
