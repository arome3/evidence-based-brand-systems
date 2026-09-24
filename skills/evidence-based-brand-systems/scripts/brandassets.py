#!/usr/bin/env python3
"""brandassets — build the logo and icon files a brand system specifies.

The guidelines specify a wordmark, a mark, an icon set, an avatar and a share
card. This builds them from the brand's own font and tokens, so they are
reproducible rather than drawn once and lost. Verify the result with
`brandcheck assets`.

    brandassets wordmark FONT --text TEXT -o wordmark.svg   shaped, outlined, recorded
    brandassets icons MARK.svg --out DIR --name NAME --bg C --fg C
                                                         icon.svg, favicon.ico, PNG set,
                                                         avatar, manifest, head snippet
    brandassets png PAGE.html --size 1200x630 -o og-default.png
                                                         render a page offline to PNG
    brandassets sheet DIR                                asset-sheet.html, for the
                                                         legibility review by eye

`wordmark` needs fontTools and uharfbuzz (pip install fonttools uharfbuzz).
`icons` and `png` need Playwright with Chromium (pip install playwright &&
python -m playwright install chromium). `sheet` is standard library.

Exit code is 0 only if everything was built.
"""
from __future__ import annotations

__version__ = "1.2.0"

import argparse
import base64
import hashlib
import json
import math
import os
import pathlib
import re
import struct
import sys
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brandcheck as bc  # noqa: E402  (shared colour parsing and reporting)

# ─────────────────────────────────────────────────────────── wordmark ──
# A wordmark is text converted to outlines. Two things make that faithful:
# shaping, so the font's own kerning, ligatures and features apply (drawing
# glyphs at their advance widths loses the kerning, and "AV" gapes), and a
# record of how it was made, so it can be rebuilt after a font update or at a
# new weight. Converting OFL glyphs to outlines for a logo is permitted: OFL
# FAQ 1.1 and 1.1.1 (openfontlicense.org/ofl-faq) — "you remain the author and
# copyright holder of that newly derived graphic". The Reserved Font Name
# rule applies to modified FONTS, not to artwork made with them.


class Placed:
    __slots__ = ("name", "x", "y", "advance")

    def __init__(self, name: str, x: int, y: int, advance: int):
        self.name, self.x, self.y, self.advance = name, x, y, advance


def _parse_features(spec: Optional[str]) -> Dict[str, bool]:
    """'ss01,-liga' -> {'ss01': True, 'liga': False}."""
    out: Dict[str, bool] = {}
    for tok in (spec or "").split(","):
        tok = tok.strip()
        if tok:
            out[tok.lstrip("+-")] = not tok.startswith("-")
    return out


def _parse_variations(spec: Optional[str]) -> Dict[str, float]:
    """'wght=600,opsz=48' -> {'wght': 600.0, 'opsz': 48.0}."""
    out: Dict[str, float] = {}
    for tok in (spec or "").split(","):
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.strip()] = float(v)
    return out


def layout(font_path, text: str, tracking: float = 0.0,
           features: Optional[Dict[str, bool]] = None,
           variations: Optional[Dict[str, float]] = None) -> List[Placed]:
    """Shape `text` with HarfBuzz; positions in font units.

    `tracking` is in em and is added between glyphs, never after the last,
    so the ink bounds stay tight.
    """
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont

    face = hb.Face(hb.Blob.from_file_path(str(font_path)))
    font = hb.Font(face)
    if variations:
        font.set_variations(variations)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    order = TTFont(str(font_path), lazy=True).getGlyphOrder()
    track = round(tracking * face.upem)
    placed, x = [], 0
    n = len(buf.glyph_infos)
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        placed.append(Placed(order[info.codepoint], x + pos.x_offset, pos.y_offset, pos.x_advance))
        x += pos.x_advance + (track if i < n - 1 else 0)
    return placed


def _ntos(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def wordmark_svg(font_path, text: str, size: float = 100.0, tracking: float = 0.0,
                 features: Optional[Dict[str, bool]] = None,
                 variations: Optional[Dict[str, float]] = None,
                 fill: str = "currentColor", title: Optional[str] = None) -> str:
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    tt = TTFont(str(font_path))
    upem = tt["head"].unitsPerEm
    glyphs = tt.getGlyphSet(location=variations) if variations else tt.getGlyphSet()
    placed = layout(font_path, text, tracking, features, variations)

    paths, box = [], None
    for g in placed:
        # Font space is y-up; SVG is y-down. Flip about the baseline.
        matrix = (1, 0, 0, -1, g.x, -g.y)
        pen = SVGPathPen(glyphs, ntos=_ntos)
        glyphs[g.name].draw(TransformPen(pen, matrix))
        if pen.getCommands():
            paths.append(pen.getCommands())
        bpen = BoundsPen(glyphs)
        glyphs[g.name].draw(TransformPen(bpen, matrix))
        if bpen.bounds:
            b = bpen.bounds
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                         max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        raise ValueError(f"{text!r} draws no ink in this font")

    os2 = tt["OS/2"] if "OS/2" in tt else None
    name = tt["name"]
    family = name.getBestFamilyName() if hasattr(name, "getBestFamilyName") else None
    record = {
        "generator": f"brandassets {__version__} wordmark",
        "font": os.path.basename(str(font_path)),
        "fontSha256": hashlib.sha256(pathlib.Path(font_path).read_bytes()).hexdigest(),
        "family": family or "",
        "fontVersion": str(name.getDebugName(5) or ""),
        "text": text,
        "unitsPerEm": upem,
        "trackingEm": tracking,
        "features": features or {},
        "variations": variations or {},
        "capHeight": getattr(os2, "sCapHeight", None),
        "xHeight": getattr(os2, "sxHeight", None),
        "baselineY": 0,
        "note": "Coordinates are font units, y-down, baseline at y=0. Clear space and "
                "minimum size in the guidelines are stated in these units.",
    }
    x0, y0, x1, y1 = box
    scale = size / upem
    label = escape(title or text)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_ntos(x0)} {_ntos(y0)} '
        f'{_ntos(x1 - x0)} {_ntos(y1 - y0)}" width="{_ntos((x1 - x0) * scale)}" '
        f'height="{_ntos((y1 - y0) * scale)}" role="img" aria-labelledby="title">\n'
        f'<title id="title">{label}</title>\n'
        f"<metadata>{escape(json.dumps(record, sort_keys=True))}</metadata>\n"
        f'<g fill="{escape(fill)}">\n'
        + "".join(f'<path d="{d}"/>\n' for d in paths)
        + "</g>\n</svg>\n")


def cmd_wordmark(args, rep: bc.Report) -> None:
    rep.section(f"WORDMARK · {args.text!r} in {os.path.basename(args.font)}")
    try:
        svg = wordmark_svg(args.font, args.text, args.size, args.tracking,
                           _parse_features(args.features), _parse_variations(args.variations),
                           args.fill, args.title)
    except ImportError as exc:
        rep.fail(f"{exc}. Install: pip install fonttools uharfbuzz")
        return
    except Exception as exc:                     # noqa: BLE001 - report, never crash
        rep.fail(f"cannot build the wordmark from {args.font}: {exc}")
        return
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    rep.ok(f"wrote {out} (shaped with HarfBuzz, outlined, construction recorded)")


# ────────────────────────────────────────────────────────────── icons ──
# One mark, placed on one ground, rendered to every size the platforms ask
# for. The 2026 minimal set (Evil Martians, "How to Favicon", 2026-01-21):
# favicon.ico (32px, plus 16px), icon.svg (with a dark-mode style), a 180px
# apple-touch-icon, 192px and 512px PNGs, and a 512px maskable icon whose art
# sits inside the safe zone. Plus a 400px avatar that survives a round crop.

_STRIP = re.compile(r"<(title|desc|metadata)\b[^>]*>.*?</\1\s*>", re.S | re.I)


def _mark_parts(path) -> Tuple[Tuple[float, float, float, float], str]:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r"<svg\b([^>]*)>(.*)</svg\s*>", text, re.S | re.I)
    if not m:
        raise ValueError(f"{path}: not an SVG")
    vb = re.search(r"""viewBox\s*=\s*["']([^"']+)["']""", m.group(1))
    if not vb:
        raise ValueError(f"{path}: the mark needs a viewBox so it can be placed")
    nums = [float(v) for v in re.split(r"[\s,]+", vb.group(1).strip())]
    if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
        raise ValueError(f"{path}: unusable viewBox {vb.group(1)!r}")
    return (nums[0], nums[1], nums[2], nums[3]), _STRIP.sub("", m.group(2)).strip()


def tile_svg(vb, inner: str, size: int, fg: str, bg: str, dark_fg: Optional[str] = None,
             dark_bg: Optional[str] = None, pad: float = 0.125, radius: float = 0.0,
             safe: Optional[float] = None) -> str:
    """The mark centred on its ground.

    `safe` is a diameter: the mark's bounding-box DIAGONAL is fitted inside
    it, so no corner of the art can leave a circular crop of that size.
    """
    vx, vy, vw, vh = vb
    s = safe / math.hypot(vw, vh) if safe else size * (1 - 2 * pad) / max(vw, vh)
    tx, ty = (size - vw * s) / 2 - vx * s, (size - vh * s) / 2 - vy * s
    style = f".bg{{fill:{bg}}}.fg{{color:{fg}}}"
    if dark_fg or dark_bg:
        style += (f"@media (prefers-color-scheme:dark){{.bg{{fill:{dark_bg or bg}}}"
                  f".fg{{color:{dark_fg or fg}}}}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'width="{size}" height="{size}"><style>{style}</style>'
            f'<rect class="bg" width="{size}" height="{size}" rx="{_ntos(radius * size)}"/>'
            f'<g class="fg" fill="currentColor" transform="translate({_ntos(tx)} {_ntos(ty)}) '
            f'scale({s:.6f})">{inner}</g></svg>')


def resolve_icon_colours(tokens_path, bg: str, fg: str, dark_bg: Optional[str] = None,
                         dark_fg: Optional[str] = None) -> Tuple[Optional[str], ...]:
    """Icon colours as hex; a value starting with -- names a token.

    Iron Law 4 reaches the icons too: a ground typed as hex stays that hex
    after the palette moves. bg/fg resolve in the light theme, dark_* in dark.
    """
    tok = None

    def one(value, theme):
        nonlocal tok
        if value is None:
            return None
        v = value.strip()
        if v.startswith("--") or v.lower().startswith("var("):
            if tok is None:
                if not tokens_path or not os.path.exists(tokens_path):
                    raise ValueError(f"{value} names a token, but there is no tokens.css "
                                     f"(pass --tokens PATH)")
                tok = bc.parse_token_css(pathlib.Path(tokens_path).read_text(encoding="utf-8"))
            value = bc.resolve_var(v if v.lower().startswith("var(") else f"var({v})",
                                   tok.theme(theme))
            if "var(" in value:
                raise ValueError(f"unknown token in the {theme} theme: {value}")
        return bc.to_hex(bc.parse_colour(value)) if bc.parse_colour(value)[3] >= 1.0 \
            else value
    return (one(bg, "light"), one(fg, "light"), one(dark_bg, "dark"), one(dark_fg, "dark"))


def with_record(png: bytes, record: dict) -> bytes:
    """Embed a provenance record in a PNG tEXt chunk, before IEND.

    `brandcheck assets` reads it back to prove the PNG still matches its
    source file and colour tokens, so a stale export cannot pass as current.
    """
    import zlib
    data = b"brandassets\x00" + json.dumps(record, sort_keys=True).encode("latin-1")
    chunk = (struct.pack(">I", len(data)) + b"tEXt" + data +
             struct.pack(">I", zlib.crc32(b"tEXt" + data) & 0xFFFFFFFF))
    at = png.rfind(b"IEND") - 4
    return png[:at] + chunk + png[at:]


def _sha256(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def ico(images: List[Tuple[int, bytes]]) -> bytes:
    """PNG-in-ICO container (supported by every browser that reads ICO)."""
    head = struct.pack("<HHH", 0, 1, len(images))
    offset, dirs, data = 6 + 16 * len(images), b"", b""
    for size, blob in images:
        dirs += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(blob),
                            offset + len(data))
        data += blob
    return head + dirs + data


class _Browser:
    """One offline Chromium for a batch of renders."""

    def __enter__(self):
        why = bc.playwright_ready()
        if why:
            raise RuntimeError(why)
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch()
        self._ctx = self._b.new_context(device_scale_factor=1)
        self._ctx.route("**/*", lambda r: r.continue_()
                        if r.request.url.startswith(("file:", "data:", "about:")) else r.abort())
        self.page = self._ctx.new_page()
        return self

    def markup(self, html: str, w: int, h: int, transparent: bool = True) -> bytes:
        self.page.set_viewport_size({"width": w, "height": h})
        self.page.set_content("<!doctype html><html><head><style>html,body{margin:0;"
                              "background:transparent}svg{display:block}</style></head>"
                              f"<body>{html}</body></html>")
        return self.page.screenshot(clip={"x": 0, "y": 0, "width": w, "height": h},
                                    omit_background=transparent)

    def page_file(self, path, w: int, h: int) -> bytes:
        self.page.set_viewport_size({"width": w, "height": h})
        self.page.goto(pathlib.Path(path).resolve().as_uri())
        self.page.wait_for_load_state("load")
        return self.page.screenshot(clip={"x": 0, "y": 0, "width": w, "height": h})

    def __exit__(self, *exc):
        self._b.close()
        self._pw.stop()


def cmd_icons(args, rep: bc.Report) -> None:
    out = pathlib.Path(args.out)
    rep.section(f"ICONS · {args.mark} -> {out}")
    tokens_path = args.tokens or str(out.parent / "tokens.css")
    names = [(args.bg, "light"), (args.fg, "light"), (args.dark_bg, "dark"), (args.dark_fg, "dark")]
    try:
        args.bg, args.fg, args.dark_bg, args.dark_fg = resolve_icon_colours(
            tokens_path, args.bg, args.fg, args.dark_bg, args.dark_fg)
        used = [(re.sub(r"^var\(\s*|\s*\)$", "", n.strip()), theme, v)
                for (n, theme), v in zip(names, (args.bg, args.fg, args.dark_bg, args.dark_fg))
                if n and (n.strip().startswith("--") or n.strip().lower().startswith("var("))]
        for c in (args.bg, args.dark_bg):
            if c and bc.parse_colour(c)[3] < 1.0:
                raise ValueError(f"the icon ground {c} must be opaque: iOS paints "
                                 f"transparency black, and a maskable icon needs a full bleed")
        vb, inner = _mark_parts(args.mark)
    except ValueError as exc:
        rep.fail(str(exc))
        return
    out.mkdir(parents=True, exist_ok=True)
    tile = dict(fg=args.fg, bg=args.bg, pad=args.padding)
    files: Dict[str, bytes] = {}
    (out / "icon.svg").write_text(
        tile_svg(vb, inner, 512, dark_fg=args.dark_fg, dark_bg=args.dark_bg,
                 radius=args.radius, **tile) + "\n", encoding="utf-8")
    try:
        with _Browser() as br:
            favs = [(n, br.markup(tile_svg(vb, inner, n, radius=args.radius, **tile), n, n))
                    for n in (16, 32)]
            files["favicon.ico"] = ico(favs)
            files["apple-touch-icon.png"] = br.markup(tile_svg(vb, inner, 180, **tile), 180, 180,
                                                      transparent=False)
            for n in (192, 512):
                files[f"icon-{n}.png"] = br.markup(
                    tile_svg(vb, inner, n, radius=args.radius, **tile), n, n)
            # Maskable: full bleed, art inside the safe circle (radius 40%) with margin.
            files["icon-mask.png"] = br.markup(
                tile_svg(vb, inner, 512, safe=512 * 0.8 * 0.94, **tile), 512, 512,
                transparent=False)
            files["avatar.png"] = br.markup(
                tile_svg(vb, inner, 400, safe=400 * 0.9, **tile), 400, 400, transparent=False)
    except RuntimeError as exc:
        rep.fail(f"cannot render the icon set: {exc}")
        return
    record = {"source": os.path.relpath(args.mark, out), "sha256": _sha256(args.mark),
              "tokens": used}
    for name, blob in files.items():
        (out / name).write_bytes(with_record(blob, record) if name.endswith(".png") else blob)

    theme = bc.to_hex(bc.parse_colour(args.bg))
    manifest = {
        "name": args.name,
        "short_name": args.short_name or args.name,
        "icons": [
            {"src": "/icon-192.png", "type": "image/png", "sizes": "192x192"},
            {"src": "/icon-512.png", "type": "image/png", "sizes": "512x512"},
            {"src": "/icon-mask.png", "type": "image/png", "sizes": "512x512",
             "purpose": "maskable"},
        ],
        "theme_color": theme,
        "background_color": theme,
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n",
                                              encoding="utf-8")
    (out / "head-snippet.html").write_text(
        "<!-- Icon and share-card tags. og:image must be an ABSOLUTE URL on the live site. -->\n"
        '<link rel="icon" href="/favicon.ico" sizes="32x32">\n'
        '<link rel="icon" href="/icon.svg" type="image/svg+xml">\n'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
        '<link rel="manifest" href="/manifest.webmanifest">\n'
        f'<meta name="theme-color" content="{theme}">\n'
        '<meta property="og:image" content="https://SITE/og-default.png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n', encoding="utf-8")
    rep.ok(f"wrote icon.svg, {', '.join(files)}, manifest.webmanifest, head-snippet.html")


# ──────────────────────────────────────────────────────────────── png ──

def cmd_png(args, rep: bc.Report) -> None:
    rep.section(f"PNG · {args.page} at {args.size}")
    try:
        w, h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        rep.fail(f"--size must be WIDTHxHEIGHT, got {args.size!r}")
        return
    if not os.path.exists(args.page):
        rep.fail(f"not found: {args.page}")
        return
    try:
        with _Browser() as br:
            blob = br.page_file(args.page, w, h)
    except RuntimeError as exc:
        rep.fail(f"cannot render: {exc}")
        return
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(with_record(blob, {"source": os.path.relpath(args.page, out.parent),
                                       "sha256": _sha256(args.page)}))
    rep.ok(f"wrote {out} ({w}x{h}, rendered offline, source recorded)")


# ────────────────────────────────────────────────────────────── sheet ──
# Mechanical checks cannot say whether the mark still reads at 16px. The
# sheet puts every asset at the sizes that matter, on both grounds, in one
# self-contained page, so a person can.

def _data_uri(path: pathlib.Path) -> str:
    mime = {".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon"}[path.suffix]
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def cmd_sheet(args, rep: bc.Report) -> None:
    d = pathlib.Path(args.dir)
    rep.section(f"SHEET · {d}")
    have = {p.name: p for p in d.iterdir() if p.suffix in (".png", ".svg", ".ico")}
    if not have:
        rep.fail(f"no assets in {d}")
        return

    def inline(name):
        p = have.get(name)
        return _STRIP.sub("", p.read_text(encoding="utf-8")) if p else ""

    def img(name, px, extra=""):
        p = have.get(name)
        return (f'<img src="{_data_uri(p)}" width="{px}" height="{px}" alt="{name} at {px}px"'
                f"{extra}>") if p else f"<em>missing {name}</em>"

    grounds = [("light ground", "#ffffff", "#111111"), ("dark ground", "#111111", "#f5f5f5")]
    rows = []
    for label, bg, fg in grounds:
        sizes = "".join(f"<figure>{img('icon.svg', n)}<figcaption>{n}px</figcaption></figure>"
                        for n in (16, 24, 32, 48))
        marks = "".join(f'<figure><span class="m" style="width:{n}px;height:{n}px">'
                        f"{inline('mark.svg')}</span><figcaption>{n}px</figcaption></figure>"
                        for n in (16, 24, 32, 48))
        words = "".join(f'<figure><span class="w" style="height:{n}px">{inline("wordmark.svg")}'
                        f"</span><figcaption>{n}px tall</figcaption></figure>"
                        for n in (12, 16, 24, 48))
        rows.append(f'<section style="background:{bg};color:{fg}"><h2>{label}</h2>'
                    f"<h3>icon.svg</h3><div class=row>{sizes}</div>"
                    f"<h3>mark.svg</h3><div class=row>{marks}</div>"
                    f"<h3>wordmark.svg</h3><div class=row>{words}</div></section>")
    crops = (f'<section><h2>Crops</h2><div class=row>'
             f'<figure class=crop>{img("icon-mask.png", 256)}<i style="width:205px;height:205px">'
             f"</i><figcaption>maskable: safe circle</figcaption></figure>"
             f'<figure class=crop>{img("avatar.png", 256)}<i style="width:256px;height:256px">'
             f"</i><figcaption>avatar: round crop</figcaption></figure>"
             f'<figure>{img("apple-touch-icon.png", 90)}<figcaption>apple-touch</figcaption>'
             f"</figure></div></section>")
    og = (f'<section><h2>Share card</h2><img src="{_data_uri(have["og-default.png"])}" '
          f'width="600" height="315" alt="og-default.png"></section>'
          if "og-default.png" in have else "<section><h2>Share card</h2><em>missing "
          "og-default.png</em></section>")
    html = ("<!doctype html><html lang=en><head><meta charset=utf-8><title>Asset sheet</title>"
            "<style>body{margin:0;font:14px/1.4 system-ui,sans-serif}section{padding:24px}"
            ".row{display:flex;gap:24px;align-items:flex-end;flex-wrap:wrap}"
            "figure{margin:0;text-align:center}figcaption{font-size:12px;opacity:.75}"
            ".m,.w{display:inline-block}.m svg,.w svg{height:100%;width:auto;display:block}"
            ".crop{position:relative}.crop i{position:absolute;left:50%;top:128px;"
            "transform:translate(-50%,-50%);border:2px dashed #e11d48;border-radius:50%;"
            "box-sizing:border-box}</style></head><body>"
            "<section><h1>Asset sheet</h1><p>Review by eye: does the mark still read at "
            "16px, on both grounds? Does the wordmark hold at its minimum size? Does any crop "
            "cut the art? icon.svg follows the viewer's OS theme, not the ground behind it, "
            "so switch the OS theme to see its dark variant. Specimen page, not a "
            "deliverable.</p></section>"
            + "".join(rows) + crops + og + "</body></html>\n")
    (d / "asset-sheet.html").write_text(html, encoding="utf-8")
    rep.ok(f"wrote {d / 'asset-sheet.html'} — open it and review every row by eye")


# ─────────────────────────────────────────────────────────────── main ──

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="brandassets", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("wordmark", help="shape and outline a wordmark from the brand font")
    w.add_argument("font", help="the brand font file (TTF/OTF; the licence permits outlining)")
    w.add_argument("--text", required=True)
    w.add_argument("-o", "--output", required=True)
    w.add_argument("--size", type=float, default=100.0, help="font size in px for width/height")
    w.add_argument("--tracking", type=float, default=0.0, help="letter-spacing in em")
    w.add_argument("--features", help="OpenType features, e.g. 'ss01,-liga'")
    w.add_argument("--variations", help="variable axes, e.g. 'wght=600'")
    w.add_argument("--fill", default="currentColor", help="default currentColor, so it themes")
    w.add_argument("--title", help="accessible name (default: the text)")
    w.set_defaults(fn=cmd_wordmark)

    i = sub.add_parser("icons", help="favicon, icon PNGs, maskable, avatar, manifest")
    i.add_argument("mark", help="the mark as SVG (paths; fill currentColor for the ink)")
    i.add_argument("--out", required=True)
    i.add_argument("--name", required=True, help="the product name for the manifest")
    i.add_argument("--short-name")
    i.add_argument("--bg", required=True,
                   help="opaque ground: a token (write --bg=--b-color-bg-page, or "
                        "--bg 'var(--b-color-bg-page)') or a colour")
    i.add_argument("--fg", required=True, help="ink for currentColor paths: a token or a colour")
    i.add_argument("--dark-bg", help="icon.svg ground under a dark OS theme (dark-theme token)")
    i.add_argument("--dark-fg", help="icon.svg ink under a dark OS theme (dark-theme token)")
    i.add_argument("--tokens", help="tokens.css for token names (default: beside --out's parent)")
    i.add_argument("--padding", type=float, default=0.125, help="padding as a fraction of size")
    i.add_argument("--radius", type=float, default=0.0,
                   help="corner radius as a fraction of size (favicon, icon.svg, 192/512)")
    i.set_defaults(fn=cmd_icons)

    g = sub.add_parser("png", help="render a self-contained page to PNG, offline")
    g.add_argument("page")
    g.add_argument("--size", required=True, help="WIDTHxHEIGHT, e.g. 1200x630")
    g.add_argument("-o", "--output", required=True)
    g.set_defaults(fn=cmd_png)

    s = sub.add_parser("sheet", help="write asset-sheet.html for review by eye")
    s.add_argument("dir")
    s.set_defaults(fn=cmd_sheet)

    p.add_argument("--version", action="version", version=f"brandassets {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rep = bc.Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
