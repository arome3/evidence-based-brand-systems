# Assets: the files the identity ships as

Stage 5. Researched 2026-09-24. The guidelines specify a wordmark, a mark, an avatar and a share card; this is how they get built, so Iron Law 3 holds for the identity as it does for the tokens. Everything here is produced by `scripts/brandassets.py` and verified by `brandcheck assets`.

## The set

All files live in `BRAND_DIR/assets/`.

| File | What it is | Rule the check enforces |
|---|---|---|
| `wordmark.svg` | The name, outlined from the brand font | Paths only (no `<text>`), a viewBox, nothing outside the file, a construction record |
| `mark.svg` | The symbol or monogram, alone | Paths only, a viewBox, self-contained |
| `icon.svg` | The mark on its ground, for browser tabs | As above; carries a dark-mode style |
| `favicon.ico` | 16 and 32px, for tabs and older agents | Holds a 32px image |
| `apple-touch-icon.png` | 180px home-screen icon | Exactly 180x180 and fully opaque (iOS paints transparency black) |
| `icon-192.png`, `icon-512.png` | Web app manifest icons | Exact sizes |
| `icon-mask.png` | 512px maskable icon | Art inside the safe zone: a centred circle of radius 40% (W3C Web Application Manifest, §2.3, Working Draft 2026-08-13) |
| `avatar.png` | 400px social profile image | Art inside the inscribed circle, so a round crop never cuts it |
| `og-default.png` (+ any `og-*.png`) | Share card | Exactly 1200x630 |
| `manifest.webmanifest` | Names the app and its icons | Real name, 192 + 512 + maskable declared, every file exists at its declared size |
| `head-snippet.html` | The `<link>`/`<meta>` tags | Handoff; `og:image` must become an absolute URL |
| `asset-sheet.html` | Review sheet | Not a deliverable; evidence that the review by eye happened |

The favicon set is the 2026 minimal set (Evil Martians, "How to Favicon", updated 2026-01-21): an ICO, an SVG with a dark-mode style, a 180px Apple icon, 192/512px PNGs and a maskable 512px icon.

**The style tile still carries no image files.** It shows the wordmark and mark as inline SVG, coloured by CSS classes that read tokens. `assets/` is the export set for every other surface.

## Wordmark

```bash
python3 scripts/brandassets.py wordmark fonts/Brand.ttf --text "brand" \
  --variations wght=600 --tracking -0.01 -o assets/wordmark.svg
```

- **Shaped, not placed.** The text is shaped with HarfBuzz, so the font's own kerning, ligatures and features apply. Glyphs drawn at their advance widths lose the kerning, and pairs like `AV` gape.
- **Recorded.** `<metadata>` holds the font file's sha256, family, version, text, size, tracking, features, variable-axis location, cap height and x-height. The mark can be rebuilt after a font update, and the guidelines can state clear space and minimum size in reproducible units (for example, clear space equal to the cap height, in font units, from the record).
- **Themes by `currentColor`.** One file serves light, dark and one-colour use. Do not ship three colour copies of the same paths.
- **Licence.** Outlining an OFL font for a logo is permitted: OFL FAQ 1.1 and 1.1.1, "You remain the author and copyright holder of that newly derived graphic or object." A Reserved Font Name restricts modified *fonts*, not artwork made with them. For any other licence, read it before outlining.
- **Distinctiveness is a legal question, not a design one.** A wordmark set in an unmodified, widely used typeface is easy to imitate. Whether that matters for registration goes to counsel, with the trademark status wording in `01-brand-identity.md`.

## Mark

The mark is the element that must work at 16px, so it is built for 16px first.

- **Derive it from the brand's own vocabulary**, as every graphic device is (`visual-system.md`). A monogram is legitimate: `brandassets wordmark FONT --text R -o r.svg` gives the letter as outlined paths to compose from.
- **Construct it on a grid** in its viewBox (for example, 64 units), paths only, `fill="currentColor"` for the ink. An explicit colour appears only on an accent device the system defines.
- **Readable at 16px on both grounds**, confirmed by eye on the sheet, not assumed.

## Icon set

```bash
python3 scripts/brandassets.py icons assets/mark.svg --out assets --name "Brand" \
  --bg --b-color-bg-page --fg --b-color-text-primary \
  --dark-bg --b-color-bg-page --dark-fg --b-color-text-primary --radius 0.18
```

Name tokens, not colours: `--bg`/`--fg` resolve in the light theme and `--dark-*` in the dark theme, from `tokens.css` beside the `assets/` directory (or `--tokens PATH`). A typed hex stays that hex after the palette moves. The ground must be opaque; the command refuses a translucent one. `--padding` sets the margin around the mark on the square icons. The maskable icon and the avatar ignore it: each fits the mark's bounding-box *diagonal* inside its circle, so no corner of the art can be cut, however wide the mark is. Every PNG carries a provenance record: the source file's sha256 and the tokens it was rendered with. `brandcheck assets` fails a PNG whose mark, page or colour token has changed since it was rendered ("stale"), so a forgotten re-export cannot pass as current.

## Share card and avatar

The share card is an HTML page, `og-card.html` (template: `templates/og-card.html`), built from the tokens with the wordmark inline and the fonts embedded, then rendered offline:

```bash
python3 scripts/brandassets.py png og-card.html --size 1200x630 -o assets/og-default.png
```

Keep `og-card.html` in the brand directory. `brandcheck` then scans its copy with the lexicon and the forbidden claims, compares its pasted tokens with `tokens.css`, and `all` renders it as it is (`render --as-is`), so its pairings must be declared like the tile's. A share card is often the first thing anyone sees of the company, so it carries no proof the company has not earned, the same as every other surface. Make one card per page that makes a distinct argument; the default card says plainly what the company does.

## Review by eye, then verify

```bash
python3 scripts/brandassets.py sheet assets     # writes assets/asset-sheet.html
python3 scripts/brandcheck.py assets BRAND_DIR
```

Keep `asset-sheet.html` beside the assets as the record that the review happened; do not deploy it. Open the sheet and answer, in the design-system self-review: does the mark read at 16px on both grounds, does the wordmark hold at its stated minimum size, and does any crop cut the art? The checker proves the files are well-formed. Only a person can say they are legible.
