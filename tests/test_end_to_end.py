"""A complete brand directory, built only with the skill's own tools, passes
`brandcheck all`. Proves the checks do not contradict one another, and that
a system that follows the skill can actually ship."""
import base64
import re
import shutil

import pytest

from conftest import FIXTURES, browser_available
from imgutil import MARK_SVG

pytestmark = pytest.mark.skipif(not browser_available(), reason="no Playwright browser")

TOKENS = """:root {
  --b-core-neutral-0: #ffffff; --b-core-neutral-100: #f0efe9; --b-core-neutral-300: #b9bdb9;
  --b-core-neutral-500: #5f6763; --b-core-neutral-800: #1b2421; --b-core-neutral-900: #16201d;
  --b-core-neutral-950: #07110f; --b-core-accent-500: #f59e0b; --b-core-accent-700: #8a4b00;
}
:root {
  color-scheme: light;
  --b-color-bg-page: var(--b-core-neutral-100); --b-color-bg-surface: var(--b-core-neutral-0);
  --b-color-text-primary: var(--b-core-neutral-900); --b-color-text-meta: var(--b-core-neutral-500);
  --b-color-border-control: var(--b-core-neutral-500); --b-color-accent: var(--b-core-accent-700);
  --b-color-focus-ring: var(--b-core-accent-700); --b-color-text-on-accent: var(--b-core-neutral-0);
  --b-font-sans: "Fixture Sans", system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark;
  --b-color-bg-page: var(--b-core-neutral-950); --b-color-bg-surface: var(--b-core-neutral-800);
  --b-color-text-primary: var(--b-core-neutral-100); --b-color-text-meta: var(--b-core-neutral-300);
  --b-color-border-control: var(--b-core-neutral-300); --b-color-accent: var(--b-core-accent-500);
  --b-color-focus-ring: var(--b-core-accent-500); --b-color-text-on-accent: var(--b-core-neutral-950); } }
:root[data-theme="dark"] {
  color-scheme: dark;
  --b-color-bg-page: var(--b-core-neutral-950); --b-color-bg-surface: var(--b-core-neutral-800);
  --b-color-text-primary: var(--b-core-neutral-100); --b-color-text-meta: var(--b-core-neutral-300);
  --b-color-border-control: var(--b-core-neutral-300); --b-color-accent: var(--b-core-accent-500);
  --b-color-focus-ring: var(--b-core-accent-500); --b-color-text-on-accent: var(--b-core-neutral-950); }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after {
  animation-duration: .001ms !important; transition-duration: .001ms !important;
  animation-iteration-count: 1 !important; } }
"""
PAIRS = """body on page\t--b-color-text-primary\t--b-color-bg-page\tnormal
body on surface\t--b-color-text-primary\t--b-color-bg-surface\tnormal
meta on page\t--b-color-text-meta\t--b-color-bg-page\tnormal
label on accent\t--b-color-text-on-accent\t--b-color-accent\tnormal
focus ring vs page\t--b-color-focus-ring\t--b-color-bg-page\tui
focus ring vs surface\t--b-color-focus-ring\t--b-color-bg-surface\tui
border vs surface\t--b-color-border-control\t--b-color-bg-surface\tui
"""


def page(font_b64, wordmark, body, extra=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Fixture</title>
<style>
@font-face {{ font-family: "Fixture Sans"; src: url(data:font/ttf;base64,{font_b64}) format("truetype"); }}
{TOKENS}
body {{ margin: 0; background: var(--b-color-bg-page); color: var(--b-color-text-primary);
       font-family: var(--b-font-sans); }}
main {{ padding: 16px; }}
.wm {{ height: 24px; color: var(--b-color-text-primary); }} .wm svg {{ height: 100%; width: auto; }}
.meta {{ color: var(--b-color-text-meta); }}
.card {{ background: var(--b-color-bg-surface); padding: 16px; }}
button {{ background: var(--b-color-accent); color: var(--b-color-text-on-accent); border: 0;
         font: inherit; padding: 8px 12px; }}
input {{ border: 1px solid var(--b-color-border-control); background: var(--b-color-bg-surface);
        color: var(--b-color-text-primary); font: inherit; }}
a {{ color: var(--b-color-text-primary); }}
:focus-visible {{ outline: 2px solid var(--b-color-focus-ring); outline-offset: 2px; }}
{extra}
</style></head><body>{body.replace("WORDMARK", wordmark)}</body></html>
"""


def test_a_complete_brand_directory_passes_all(run, ba_run, tmp_path, fixture_font):
    root = tmp_path
    (root / "fonts").mkdir()
    shutil.copy(fixture_font, root / "fonts" / "FixtureSans.ttf")
    shutil.copy(FIXTURES / "licences" / "inter-LICENSE.txt", root / "fonts" / "OFL.txt")
    (root / "tokens.css").write_text(TOKENS)
    (root / "pairs.tsv").write_text(PAIRS)
    (root / "forbidden-claims.txt").write_text("bank-grade\tno independent assessment\n")
    (root / "01-brand-identity.md").write_text(
        "# Identity\n\nReconciliation software for finance teams.\n\n"
        '## Prohibited\n\nNever describe the product as "bank-grade".\n')

    a = root / "assets"
    a.mkdir()
    (a / "mark.svg").write_text(MARK_SVG)
    assert ba_run("wordmark", fixture_font, "--text", "RAV", "-o", a / "wordmark.svg")[0] == 0
    assert ba_run("icons", a / "mark.svg", "--out", a, "--name", "Fixture", "--bg", "#07110f",
                  "--fg", "#f0efe9")[0] == 0
    wm = re.sub(r"<metadata>.*?</metadata>", "", (a / "wordmark.svg").read_text(), flags=re.S)
    font_b64 = base64.b64encode(fixture_font.read_bytes()).decode()

    (root / "style-tile.html").write_text(page(font_b64, wm, """
<main><nav><span class="wm">WORDMARK</span></nav>
<h1>Reconciliation for finance teams</h1><p class="meta">Specimen, illustrative only.</p>
<div class="card"><p>Card copy.</p><label>Account <input value="0000"></label></div>
<p><button type="button">Request access</button> <a href="#top">Read the method</a></p></main>"""))
    (root / "og-card.html").write_text(page(font_b64, wm, """
<main><div class="wm">WORDMARK</div><h1>Reconciliation for finance teams</h1>
<p class="meta">fixture.example</p></main>""",
        "body { width: 1200px; height: 630px; }"))
    assert ba_run("png", root / "og-card.html", "--size", "1200x630",
                  "-o", a / "og-default.png")[0] == 0

    assert run("export", root)[0] == 0
    code, out = run("all", root, "--glyphs", "RAV0")
    assert code == 0, out
    for section in ("TOKENS", "CONTRAST", "LEXICON", "FONTS", "ASSETS", "RENDER"):
        assert section in out
