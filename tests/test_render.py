"""The rendered layer: what the browser actually paints, in both themes.

Iron Law 1 says an undeclared pairing is an unverified pairing. Only a
browser knows which pairings a page really renders, so this is where the law
becomes enforceable.
"""
import pytest

from conftest import browser_available

pytestmark = pytest.mark.skipif(not browser_available(), reason="no Playwright browser")

TOKENS = """:root {
  --b-core-ink: #111111; --b-core-paper: #ffffff; --b-core-night: #0b0b0b;
  --b-core-fog: #eeeeee; --b-core-line: #6b6b6b; --b-core-focus: #0050b3;
  --b-core-focus-dark: #7fb2ff; --b-core-line-dark: #9a9a9a;
  --b-color-text: var(--b-core-ink); --b-color-bg: var(--b-core-paper);
  --b-color-border-control: var(--b-core-line); --b-color-focus-ring: var(--b-core-focus);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --b-color-text: var(--b-core-fog); --b-color-bg: var(--b-core-night);
  --b-color-border-control: var(--b-core-line-dark); --b-color-focus-ring: var(--b-core-focus-dark); } }
:root[data-theme="dark"] {
  --b-color-text: var(--b-core-fog); --b-color-bg: var(--b-core-night);
  --b-color-border-control: var(--b-core-line-dark); --b-color-focus-ring: var(--b-core-focus-dark); }
"""
PAIRS = ("body\t--b-color-text\t--b-color-bg\tnormal\n"
         "control border\t--b-color-border-control\t--b-color-bg\tui\n"
         "focus ring\t--b-color-focus-ring\t--b-color-bg\tui\n")
BASE_CSS = """
body { margin: 0; background: var(--b-color-bg); color: var(--b-color-text);
       font: 16px/1.5 system-ui, sans-serif; }
main { padding: 16px; }
input { border: 1px solid var(--b-color-border-control); background: var(--b-color-bg);
        color: var(--b-color-text); }
:focus-visible { outline: 2px solid var(--b-color-focus-ring); outline-offset: 2px; }
a { color: var(--b-color-text); text-decoration: underline; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after {
  animation-duration: .001ms !important; transition-duration: .001ms !important;
  animation-iteration-count: 1 !important; } }
"""


def tile(extra_css="", body='<p>Reconciliation for finance teams.</p>'
         '<label>Account <input value="0000"></label> <a href="#x">Link</a>'):
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<style>{TOKENS}{BASE_CSS}{extra_css}</style></head>"
            f"<body><main>{body}</main></body></html>")


def setup(write, html, pairs=PAIRS):
    write("tokens.css", TOKENS)
    write("pairs.tsv", pairs)
    return write("style-tile.html", html)


def test_a_clean_tile_passes(run, write):
    page = setup(write, tile())
    code, out = run("render", page)
    assert code == 0, out
    assert "all declared" in out


def test_an_undeclared_pairing_fails(run, write):
    page = setup(write, tile(".note { color: #5a5a5a; }",
                             body="<p>Body copy.</p><p class=note>Aside.</p>"))
    code, out = run("render", page)
    assert code == 1
    assert "undeclared" in out
    assert "Aside." in out


def test_rendered_text_below_its_threshold_fails(run, write):
    page = setup(write, tile(".faint { color: #d8d8d8; }",
                             body="<p class=faint>Faint copy.</p>"),
                 PAIRS + "faint\t#d8d8d8\t--b-color-bg\tnormal\tlight\n")
    code, out = run("render", page)
    assert code == 1
    assert "Faint copy." in out


def test_horizontal_overflow_at_reflow_width_fails(run, write):
    page = setup(write, tile(".wide { width: 600px; }",
                             body="<p class=wide>Wide.</p>"))
    code, out = run("render", page)
    assert code == 1
    assert "overflow" in out and "320" in out


def test_a_missing_focus_indicator_fails(run, write):
    page = setup(write, tile("a:focus-visible { outline: none; }"))
    code, out = run("render", page)
    assert code == 1
    assert "focus" in out


def test_motion_that_survives_reduced_motion_fails(run, write):
    css = ("@keyframes spin { to { transform: rotate(1turn); } }"
           ".spin { animation: spin 2s linear infinite !important; }")
    page = setup(write, tile(css, body="<p class=spin>Loading</p>"))
    code, out = run("render", page)
    assert code == 1
    assert "reduced motion" in out


def test_an_exempt_logotype_is_skipped_and_listed(run, write):
    page = setup(write, tile(".logo { color: #dddddd; }",
                             body='<p>Body.</p><span class=logo data-contrast-exempt="logotype">'
                                  "Brand</span>"))
    code, out = run("render", page)
    assert code == 0, out
    assert "exempt" in out


def test_a_surface_the_dark_theme_forgot_fails_when_rendered(run, write):
    css = ".card { background: #ffffff; }"      # a raw light surface in both themes
    page = setup(write, tile(css, body="<div class=card><p>Card copy.</p></div>"))
    code, out = run("render", page)
    assert code == 1
    assert "dark" in out and "Card copy." in out
