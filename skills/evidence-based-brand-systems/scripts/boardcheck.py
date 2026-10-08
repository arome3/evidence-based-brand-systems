#!/usr/bin/env python3
"""boardcheck — text that runs out of its box on a rendered board or deck.

The failures a reviewer sees first and a designer misses after the tenth
render: a headline running past its poster's edge, a caption card pushed off
the slide, a label sitting under another one. This renders the page in
Chromium and measures every line of text.

    boardcheck FILE.html [FILE.html…] [--slide-selector "section.slide"]

For each slide, every visible text run is measured line by line
(Range.getClientRects) and must sit inside:
  · the slide;                                                       FAIL
  · its nearest ancestor that clips (overflow hidden/clip/auto/scroll),
    which would cut it off;                                          FAIL
  · its nearest ancestor that paints a box (a background colour or
    image, or a border), such as a poster on the slide — text past its
    edge reads as a spill even where nothing clips it;               FAIL
and every element carrying text must sit inside the slide.          FAIL
Text whose lines overlap another element's by more than 30% of the
smaller (comparing the middle 60% of each line's height, where the glyphs
are, so tight display leading does not count), or that another element
covers, is reported.                                                 WARN

Tolerance 1px. Opt-outs, for a deliberate effect, on the element or an
ancestor: data-overflow-ok (a sticker that overhangs its card on purpose),
data-overlap-ok (type set over type on purpose).

The page is opened at its natural size: the viewport is set to the slides'
own size (start size --viewport, default 1600x900, which also decides what
vw/vh-sized slides measure). Web fonts load as the page asks (--offline
blocks everything but file: and data:). Animations and transitions are
switched off, so the page is measured in its static styles.

Needs Playwright with Chromium (pip install playwright && python -m
playwright install chromium). Exit code is 0 only if no slide fails.
"""
from __future__ import annotations

__version__ = "1.3.0"

import argparse
import math
import os
import pathlib
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brandcheck as bc  # noqa: E402  (shared reporting, browser probe)

TOLERANCE = 1.0
OVERLAP = 0.30

_MEASURE_JS = """
(sel) => {
  const slides = Array.from(document.querySelectorAll(sel));
  if (!slides.length) return null;
  let w = 0, h = 0;
  for (const s of slides) {
    const r = s.getBoundingClientRect();
    w = Math.max(w, r.width); h = Math.max(h, r.height);
  }
  return {count: slides.length, w, h};
}
"""

_CHECK_JS = r"""
([sel, index, tol, overlapMin]) => {
  const slide = document.querySelectorAll(sel)[index];
  // Bring the slide to the viewport's origin so elementFromPoint can see it.
  const r0 = slide.getBoundingClientRect();
  window.scrollTo({left: r0.left + window.scrollX, top: r0.top + window.scrollY,
                   behavior: 'instant'});
  const S = slide.getBoundingClientRect();
  const rel = r => ({x: Math.round(r.left - S.left), y: Math.round(r.top - S.top),
                     w: Math.round(r.width), h: Math.round(r.height)});
  const where = el => {
    if (el === slide) return 'the slide';
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const c = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (c.length) s += '.' + c.join('.');
    return s;
  };
  const clear = c => {              // a fully transparent colour, in any syntax
    if (!c || c === 'transparent') return true;
    let m = c.match(/^rgba\(([^)]*)\)$/);
    if (m) { const p = m[1].split(','); return p.length === 4 && parseFloat(p[3]) === 0; }
    m = c.match(/\/\s*([\d.]+)%?\s*\)$/);
    return !!m && parseFloat(m[1]) === 0;
  };
  const paintsBox = cs => {
    if (!clear(cs.backgroundColor) || cs.backgroundImage !== 'none') return true;
    for (const side of ['Top', 'Right', 'Bottom', 'Left'])
      if (parseFloat(cs['border' + side + 'Width']) > 0 && cs['border' + side + 'Style'] !== 'none'
          && !clear(cs['border' + side + 'Color'])) return true;
    return false;
  };
  const clipsX = cs => cs.overflowX !== 'visible';
  const clipsY = cs => cs.overflowY !== 'visible';
  // Spill of rect r past box b, per side; >0 means outside.
  const spill = (r, b, x = true, y = true) => Math.max(
    x ? b.left - r.left : 0, x ? r.right - b.right : 0,
    y ? b.top - r.top : 0, y ? r.bottom - b.bottom : 0);
  const paddingBox = el => {
    const r = el.getBoundingClientRect();
    const left = r.left + el.clientLeft, top = r.top + el.clientTop;
    return {left, top, right: left + el.clientWidth, bottom: top + el.clientHeight,
            width: el.clientWidth, height: el.clientHeight};
  };
  const hidden = el => {
    for (let a = el; a && a !== slide.parentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.display === 'none' || parseFloat(cs.opacity) === 0) return true;
    }
    return getComputedStyle(el).visibility !== 'visible';
  };
  // The nearest ancestor whose overflow would clip el's box. An absolutely
  // positioned box escapes static ancestors until its containing block.
  const clipperOf = el => {
    let escaping = null;              // 'abs' | 'fixed' | null
    const own = getComputedStyle(el).position;
    if (own === 'absolute') escaping = 'abs';
    if (own === 'fixed') escaping = 'fixed';
    for (let a = el.parentElement; a && a !== slide; a = a.parentElement) {
      const cs = getComputedStyle(a);
      const contains = escaping === 'abs' ? cs.position !== 'static'
                     : escaping === 'fixed' ? (cs.transform !== 'none' || cs.filter !== 'none')
                     : true;
      if (contains) {
        if (clipsX(cs) || clipsY(cs)) return [a, cs];
        escaping = cs.position === 'absolute' ? 'abs'
                 : cs.position === 'fixed' ? 'fixed' : null;
      }
    }
    return [null, null];
  };
  const panelOf = el => {
    for (let a = el; a && a !== slide; a = a.parentElement)
      if (paintsBox(getComputedStyle(a))) return a;
    return null;
  };

  const runs = [];                    // {el, rects}
  const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
  const skipTags = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'TITLE', 'DESC']);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement;
    if (!el || skipTags.has(el.tagName.toUpperCase()) || hidden(el)) continue;
    const range = document.createRange();
    range.selectNodeContents(n);
    const rects = Array.from(range.getClientRects()).filter(r => r.width > 0.5 && r.height > 0.5);
    if (rects.length) runs.push({el, rects, text: n.nodeValue});
  }

  const ids = new Map();
  const idOf = el => { if (!ids.has(el)) ids.set(el, ids.size); return ids.get(el); };
  const issues = {};                  // key -> issue, keeping the worst spill
  const add = (kind, el, box, amount, extra) => {
    const key = kind + '|' + idOf(el);
    if (!issues[key] || issues[key].spill < amount)
      issues[key] = Object.assign({kind, where: where(el), box: rel(box),
                                   spill: Math.round(amount * 10) / 10}, extra || {});
  };
  const texts = new Map();            // el -> snippet
  for (const run of runs) {
    const t = (texts.get(run.el) || '') + ' ' + run.text;
    texts.set(run.el, t.replace(/\s+/g, ' ').trim());
  }
  const snippet = el => {
    const t = texts.get(el) || el.textContent.replace(/\s+/g, ' ').trim();
    return t.length > 48 ? t.slice(0, 47) + '…' : t;
  };

  for (const run of runs) {
    const el = run.el;
    if (el.closest('[data-overflow-ok]')) continue;
    const [clipper, ccs] = clipperOf(el);
    const panel = panelOf(el);
    for (const r of run.rects) {
      const s = spill(r, S);
      if (s > tol) add('slide', el, r, s, {text: snippet(el)});
      if (clipper) {
        const c = spill(r, paddingBox(clipper), clipsX(ccs), clipsY(ccs));
        if (c > tol) add('clip', el, r, c, {text: snippet(el), container: where(clipper),
                                            cbox: rel(paddingBox(clipper))});
      }
      if (panel && panel !== clipper) {
        const pb = panel.getBoundingClientRect();
        const p = spill(r, pb);
        if (p > tol) add('panel', el, r, p, {text: snippet(el), container: where(panel),
                                             cbox: rel(pb)});
      }
    }
    const eb = el.getBoundingClientRect();
    const es = spill(eb, S);
    if (es > tol && !issues['slide|' + idOf(el)])
      add('element', el, eb, es, {text: snippet(el)});
  }

  // Collisions: lines of different elements on top of each other, or text
  // under another element.
  const warnings = [];
  const seenPair = new Set();
  const ok = el => el.closest('[data-overlap-ok]');
  const area = r => r.width * r.height;
  // A line's rect is the font's whole content area, taller than the line box
  // under tight display leading; the glyphs sit in its middle. Compare those.
  const core = r => ({left: r.left, right: r.right, top: r.top + r.height * 0.2,
                      bottom: r.bottom - r.height * 0.2, width: r.width, height: r.height * 0.6});
  for (let i = 0; i < runs.length; i++) {
    for (let j = i + 1; j < runs.length; j++) {
      const a = runs[i], b = runs[j];
      if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (ok(a.el) || ok(b.el)) continue;
      const key = idOf(a.el) + ':' + idOf(b.el);
      if (seenPair.has(key)) continue;
      let worst = 0, box = null;
      for (const ra of a.rects) for (const rb of b.rects) {
        const ca = core(ra), cb = core(rb);
        const w = Math.min(ca.right, cb.right) - Math.max(ca.left, cb.left);
        const h = Math.min(ca.bottom, cb.bottom) - Math.max(ca.top, cb.top);
        if (w <= 0 || h <= 0) continue;
        const f = (w * h) / Math.min(area(ca), area(cb));
        if (f > worst) { worst = f; box = ra; }
      }
      if (worst > overlapMin) {
        seenPair.add(key);
        warnings.push({kind: 'overlap', where: where(a.el), text: snippet(a.el),
                       other: where(b.el), otherText: snippet(b.el), box: rel(box),
                       share: Math.round(worst * 100)});
      }
    }
  }
  const textEls = new Set(runs.map(r => r.el));
  const covered = new Set();
  for (const run of runs) {
    const el = run.el;
    if (ok(el) || covered.has(el) || getComputedStyle(el).pointerEvents === 'none') continue;
    for (const r of run.rects) {
      const x = r.left + r.width / 2, y = r.top + r.height / 2;
      if (x < 0 || y < 0 || x >= window.innerWidth || y >= window.innerHeight) continue;
      if (spill(r, S) > tol) continue;
      const top = document.elementFromPoint(x, y);
      if (!top || top === el || el.contains(top) || top.contains(el)) continue;
      if (ok(top)) continue;
      let t = top;                     // text over text is the overlap check's
      while (t && t !== slide && !textEls.has(t)) t = t.parentElement;
      if (t && t !== slide) continue;
      if (!slide.contains(top)) continue;
      covered.add(el);
      warnings.push({kind: 'covered', where: where(el), text: snippet(el), other: where(top),
                     box: rel(r)});
      break;
    }
  }
  return {size: rel(S), runs: runs.length, issues: Object.values(issues), warnings};
}
"""


def _box(b: Dict) -> str:
    return f"{b['w']}x{b['h']} at {b['x']},{b['y']}"


def describe(slide_no: int, it: Dict, size: Dict) -> str:
    head = f"slide {slide_no}: \"{it['text']}\" ({it['where']})"
    if it["kind"] == "slide":
        return (f"{head} runs {it['spill']:g}px off the {size['w']}x{size['h']} slide; "
                f"its line is {_box(it['box'])}")
    if it["kind"] == "clip":
        return (f"{head} is cut off by {it['container']} (it clips its overflow): the line "
                f"{_box(it['box'])} runs {it['spill']:g}px past {_box(it['cbox'])}")
    if it["kind"] == "panel":
        return (f"{head} spills {it['spill']:g}px past {it['container']}, the box it sits on: "
                f"line {_box(it['box'])}, box {_box(it['cbox'])}")
    if it["kind"] == "element":
        return (f"{head} is placed {it['spill']:g}px off the {size['w']}x{size['h']} slide: "
                f"its box is {_box(it['box'])}")
    if it["kind"] == "overlap":
        return (f"slide {slide_no}: \"{it['text']}\" ({it['where']}) and \"{it['otherText']}\" "
                f"({it['other']}) overlap by {it['share']}% at {_box(it['box'])}")
    return (f"slide {slide_no}: \"{it['text']}\" ({it['where']}) is covered by {it['other']} "
            f"at {_box(it['box'])}")


def _viewport(spec: str):
    w, h = (int(v) for v in spec.lower().split("x"))
    if w < 1 or h < 1:
        raise ValueError
    return w, h


def check_board(path: str, rep: bc.Report, selector: str, viewport, offline: bool,
                browser) -> None:
    rep.section(f"BOARD · {path}")
    if not os.path.exists(path):
        rep.fail(f"not found: {path}")
        return
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              device_scale_factor=1, reduced_motion="reduce")
    try:
        if offline:
            ctx.route("**/*", lambda r: r.continue_()
                      if r.request.url.startswith(("file:", "data:", "about:")) else r.abort())
        page = ctx.new_page()
        page.goto(pathlib.Path(path).resolve().as_uri(), wait_until="load")
        page.add_style_tag(content=bc._STILL)
        page.evaluate("document.fonts.ready.then(() => true)")
        size = page.evaluate(_MEASURE_JS, selector)
        if not size:
            rep.fail(f"no element matches --slide-selector {selector!r}; pass the selector "
                     f"for one slide (use 'body' for a single poster or card)")
            return
        w, h = math.ceil(size["w"]), math.ceil(size["h"])
        if w >= 1 and h >= 1 and (w, h) != tuple(viewport):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("document.fonts.ready.then(() => true)")
        fails = 0
        for i in range(size["count"]):
            res = page.evaluate(_CHECK_JS, [selector, i, TOLERANCE, OVERLAP])
            for it in sorted(res["issues"], key=lambda it: (-it["spill"], it["where"])):
                rep.fail(describe(i + 1, it, res["size"]))
                fails += 1
            for it in res["warnings"]:
                rep.warn(describe(i + 1, it, res["size"]))
            if not res["issues"]:
                rep.ok(f"slide {i + 1}: {res['runs']} text run(s) inside the slide and their "
                       f"boxes ({res['size']['w']}x{res['size']['h']})")
        if fails:
            rep.note("fix the layout, or mark a deliberate overhang data-overflow-ok; then "
                     "render again and look at the slide")
    finally:
        ctx.close()


def cmd_check(args, rep: bc.Report) -> None:
    try:
        viewport = _viewport(args.viewport)
    except ValueError:
        rep.fail(f"--viewport must be WIDTHxHEIGHT, got {args.viewport!r}")
        return
    why = bc.playwright_ready()
    if why:
        rep.fail(f"cannot render the board: {why}")
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for path in args.files:
                check_board(path, rep, args.slide_selector, viewport, args.offline, browser)
        finally:
            browser.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="boardcheck", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("files", nargs="+", metavar="FILE.html")
    p.add_argument("--slide-selector", default="section.slide",
                   help="CSS selector for one slide (default 'section.slide')")
    p.add_argument("--viewport", default="1600x900",
                   help="starting viewport; the page is then sized to its slides (default "
                        "1600x900)")
    p.add_argument("--offline", action="store_true",
                   help="block network requests (a board should be self-contained)")
    p.add_argument("--version", action="version", version=f"boardcheck {__version__}")
    p.set_defaults(fn=cmd_check)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rep = bc.Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
