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


def test_as_is_renders_a_single_theme_page_against_every_declared_pair(run, write):
    # A share card pastes one theme's tokens and is rendered once, as it is.
    card = ("<!doctype html><html><head><style>body{margin:0;width:1200px;height:630px;"
            "background:#0b0b0b;color:#eeeeee}</style></head><body><h1>Card</h1></body></html>")
    write("tokens.css", TOKENS)
    write("pairs.tsv", PAIRS)
    page = write("og-card.html", card)
    code, out = run("render", page, "--as-is", "--widths", "1200")
    assert code == 0, out


def test_all_renders_the_share_card_as_is(run, write, tmp_path):
    write("tokens.css", TOKENS)
    write("pairs.tsv", PAIRS)
    write("forbidden-claims.txt", "bank-grade\tno assessment\n")
    write("style-tile.html", tile())
    write("og-card.html", "<!doctype html><html><head><style>body{margin:0;width:1200px;"
          "height:630px;background:#0b0b0b;color:#777777}</style></head>"
          "<body><h1>Card</h1></body></html>")
    code, out = run("all", tmp_path)
    assert "RENDER · " in out and "og-card.html" in out
    assert "undeclared pairing #777777 on #0b0b0b" in out


# Panels need token blocks that cascade into a subtree: the dark block also
# matches [data-theme="dark"], and a light panel re-declares the light values.
CASCADE_TOKENS = TOKENS.replace(':root[data-theme="dark"] {',
                                ':root[data-theme="dark"], [data-theme="dark"] {') + (
    '[data-theme="light"] { --b-color-text: var(--b-core-ink); --b-color-bg: var(--b-core-paper);'
    ' --b-color-border-control: var(--b-core-line); --b-color-focus-ring: var(--b-core-focus); }\n')


def test_a_theme_locked_panel_is_judged_by_its_own_theme(run, write):
    # The style tile shows both themes at once; a dark panel on a light page
    # must match the dark pairings, not fail as undeclared in the light pass.
    write("tokens.css", CASCADE_TOKENS)
    write("pairs.tsv", PAIRS)
    page = write("style-tile.html", tile(
        "[data-theme] { background: var(--b-color-bg); color: var(--b-color-text); }",
        body='<p>Page.</p><div data-theme="dark"><p>Dark panel.</p></div>'
             '<div data-theme="light"><p>Light panel.</p></div>').replace(
        TOKENS, CASCADE_TOKENS))
    code, out = run("render", page)
    assert code == 0, out


def test_a_served_page_can_be_rendered_by_url(run, write, tmp_path):
    import functools
    import http.server
    import threading
    write("tokens.css", TOKENS)
    write("pairs.tsv", PAIRS)
    write("site/index.html", tile())
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(tmp_path / "site"))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        code, out = run("render", url, "--pairs", tmp_path / "pairs.tsv")
    finally:
        server.shutdown()
    assert code == 0, out
    assert "all declared" in out
