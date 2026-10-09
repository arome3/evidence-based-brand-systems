#!/usr/bin/env python3
"""refcapture — capture an owner's references so the designer can look at them.

A reference is something to look at, image by image, not something to
summarise. This captures it as images, in order, with a record of where and
when they came from.

    refcapture site URL --out DIR [--widths 1440,390]
        At each width: a full-page screenshot and viewport frames every ~900px.
        Writes DIR/<slug>-<width>-full.png and DIR/<slug>-<width>-fNN.png.
    refcapture project URL --out DIR [--max 40]
        A gallery page (Behance, Dribbble, any page): scrolls to load it,
        collects its large images in page order (Behance: the project's
        module images; elsewhere: images at least --min-width px wide),
        downloads them as DIR/01.jpg, 02.jpg, … and lays them out on contact
        sheets DIR/sheet0.jpg, … (2 columns, numbered).

Both add a record (kind, url, title, date, files) to DIR/index.json, a list
with one record per captured URL; capturing the same URL again replaces it.

Consent banners: a button is clicked only when its whole label says reject,
decline, deny, refuse or necessary/essential only. Nothing that accepts is
ever clicked; a banner without a reject button is left in place and may cover
part of the frames.

Needs Playwright with Chromium (pip install playwright && python -m
playwright install chromium); `project` also needs Pillow (pip install pillow).
Exit code is 0 only if everything was captured.
"""
from __future__ import annotations

__version__ = "1.3.0"

import argparse
import datetime as _dt
import io
import json
import os
import pathlib
import re
import sys
import urllib.request
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brandcheck as bc  # noqa: E402  (shared reporting, browser probe)
import contactsheet as cs  # noqa: E402

UA_DESKTOP = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

# The WHOLE label must say no. "Accept all", "OK", "Got it", "Agree" never match.
REJECT = re.compile(
    r"^(?:reject(?: all)?(?: cookies)?|reject (?:non-essential|optional|additional)"
    r"(?: cookies)?|decline(?: all)?(?: cookies)?|deny(?: all)?|refuse(?: all)?"
    r"|disagree|no,? thanks|(?:use |allow |accept )?(?:only )?(?:strictly )?"
    r"(?:necessary|essential)(?: cookies)?(?: only)?|continue without accepting"
    r"|disable (?:all )?cookies)$", re.I)
_BUTTONS = ("button, [role=button], a[role=button], input[type=button], input[type=submit]")


def is_reject_label(text: str) -> bool:
    flat = " ".join((text or "").split()).strip(" .!×✕")
    if not flat or len(flat) > 48:
        return False
    if re.search(r"\baccept(?! only)\b|\bagree\b|\ballow all\b", flat, re.I) and \
            not re.search(r"\b(?:only|necessary|essential)\b", flat, re.I):
        return False
    return bool(REJECT.match(flat))


def slug(url: str) -> str:
    """'https://www.example.com/work/one?x=1' -> 'example-com-work-one'."""
    parts = urlsplit(url)
    if parts.scheme == "file":
        base = pathlib.PurePosixPath(parts.path).stem
    else:
        host = re.sub(r"^www\.", "", parts.netloc.lower())
        base = host + parts.path
    s = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return s[:60].rstrip("-") or "page"


def frame_positions(page_height: int, viewport_height: int, step: int = 900,
                    max_frames: int = 12) -> List[int]:
    """Scroll offsets for viewport frames: every `step` px, the last one flush
    with the bottom; spread evenly when a long page needs more than max_frames."""
    last = max(int(page_height) - int(viewport_height), 0)
    step = max(int(step), 1)
    pos = list(range(0, last + 1, step))
    if pos[-1] < last:
        pos.append(last)
    if max_frames >= 1 and len(pos) > max_frames:
        if max_frames == 1:
            return [0]
        pos = [round(i * last / (max_frames - 1)) for i in range(max_frames)]
    return pos


def dedupe_key(url: str) -> str:
    """Two renditions of one image share a key.

    Behance serves each module at several sizes (/project_modules/1400/x.jpg,
    /project_modules/max_1200/x.jpg); elsewhere the size is usually a query.
    """
    parts = urlsplit(url)
    if "/project_modules/" in parts.path:
        return "project_modules:" + parts.path.rsplit("/", 1)[-1]
    return urlunsplit(("", parts.netloc, parts.path, "", ""))


def dedupe(found: List[Dict]) -> List[Dict]:
    """First occurrence keeps its place in page order; the largest rendition wins."""
    order: List[str] = []
    best: Dict[str, Dict] = {}
    for it in found:
        k = dedupe_key(it["src"])
        if k not in best:
            order.append(k)
            best[k] = it
        elif (it.get("w") or 0) > (best[k].get("w") or 0):
            best[k] = it
    return [best[k] for k in order]


def default_match(url: str) -> Optional[str]:
    """The substring that marks a project image on sites that have one."""
    host = urlsplit(url).netloc.lower()
    return "project_modules" if host.endswith("behance.net") else None


def fetch(url: str, referer: Optional[str] = None, timeout: int = 30) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer and referer.startswith("http"):
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                timeout=timeout) as r:
        return r.read()


# ───────────────────────────────────────────────────────────── index ──

def load_index(d: pathlib.Path) -> List[Dict]:
    p = d / "index.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return []
    return data if isinstance(data, list) else [data] if isinstance(data, dict) else []


def save_record(d: pathlib.Path, record: Dict) -> None:
    recs = [r for r in load_index(d)
            if not (r.get("kind") == record["kind"] and r.get("url") == record["url"])]
    recs.append(record)
    (d / "index.json").write_text(json.dumps(recs, indent=2, ensure_ascii=False) + "\n",
                                  encoding="utf-8")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _target(url: str) -> str:
    if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
        return url
    p = pathlib.Path(url)
    if p.exists():
        return p.resolve().as_uri()
    return "https://" + url


# ──────────────────────────────────────────────────────────── browser ──

def dismiss_consent(page) -> Optional[str]:
    """Click a reject-only consent button if there is one; return its label."""
    for frame in page.frames:
        try:
            handles = frame.query_selector_all(_BUTTONS)
        except Exception:                        # noqa: BLE001 - detached frame
            continue
        for el in handles:
            try:
                text = (el.inner_text() or el.get_attribute("value")
                        or el.get_attribute("aria-label") or "")
                if is_reject_label(text) and el.is_visible():
                    y = page.evaluate("window.scrollY")
                    el.click(timeout=2000)
                    page.wait_for_timeout(600)
                    page.evaluate("y => window.scrollTo(0, y)", y)
                    return " ".join(text.split())
            except Exception:                    # noqa: BLE001 - stale element, next
                continue
    return None


def _height(page) -> int:
    return int(page.evaluate("Math.max(document.body ? document.body.scrollHeight : 0, "
                             "document.documentElement.scrollHeight)"))


def scroll_through(page, step: int, pause: int, max_steps: int = 80) -> None:
    """Scroll to the bottom in steps so lazy images and reveal animations load."""
    y, stable = 0, 0
    for _ in range(max_steps):
        h = _height(page)
        if y >= h:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        y = min(y + step, h)
        page.evaluate("y => window.scrollTo(0, y)", y)
        page.wait_for_timeout(pause)


def _goto(page, url: str, timeout: int, rep: bc.Report, where: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception as exc:                     # noqa: BLE001 - capture what loaded
        rep.warn(f"{where}: page load did not finish ({str(exc).splitlines()[0][:100]}); "
                 f"capturing what loaded")


def _browser_or_fail(rep: bc.Report):
    why = bc.playwright_ready()
    if why:
        rep.fail(f"cannot capture: {why}")
        return None
    from playwright.sync_api import sync_playwright
    return sync_playwright


# ─────────────────────────────────────────────────────────────── site ──

def cmd_site(args, rep: bc.Report) -> None:
    url = _target(args.url)
    out = pathlib.Path(args.out)
    rep.section(f"SITE · {url} -> {out}")
    try:
        widths = [int(w) for w in str(args.widths).split(",") if w.strip()]
    except ValueError:
        rep.fail(f"--widths must be comma-separated integers, got {args.widths!r}")
        return
    if not widths:
        rep.fail("--widths is empty")
        return
    sp = _browser_or_fail(rep)
    if not sp:
        return
    out.mkdir(parents=True, exist_ok=True)
    name = args.name or slug(url)
    files: List[str] = []
    consent: Dict[str, Optional[str]] = {}
    heights: Dict[str, int] = {}
    title = ""
    with sp() as pw:
        browser = pw.chromium.launch()
        try:
            for w in widths:
                mobile = w < 800
                vh = args.height or (844 if mobile else 900)
                ctx = browser.new_context(viewport={"width": w, "height": vh},
                                          device_scale_factor=1, is_mobile=mobile,
                                          has_touch=mobile,
                                          user_agent=UA_MOBILE if mobile else UA_DESKTOP)
                page = ctx.new_page()
                _goto(page, url, args.timeout, rep, f"{w}px")
                page.wait_for_timeout(args.wait)
                clicked = dismiss_consent(page)
                scroll_through(page, vh, max(args.wait // 10, 80))
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(max(args.wait // 4, 50))
                title = title or page.title()
                h = _height(page)
                heights[str(w)] = h
                positions = frame_positions(h, vh, args.step, args.max_frames)
                for i, y in enumerate(positions, 1):
                    page.evaluate("y => window.scrollTo(0, y)", y)
                    page.wait_for_timeout(max(args.wait // 6, 50))
                    if not clicked:
                        clicked = dismiss_consent(page)
                        if clicked:
                            page.evaluate("y => window.scrollTo(0, y)", y)
                    f = f"{name}-{w}-f{i:02d}.png"
                    page.screenshot(path=str(out / f))
                    files.append(f)
                page.evaluate("window.scrollTo(0, 0)")
                full = f"{name}-{w}-full.png"
                try:
                    page.screenshot(path=str(out / full), full_page=True, timeout=60000)
                    files.append(full)
                except Exception as exc:         # noqa: BLE001 - frames still stand
                    rep.warn(f"{w}px: full-page screenshot failed "
                             f"({str(exc).splitlines()[0][:100]}); the frames cover the page")
                consent[str(w)] = clicked
                rep.ok(f"{w}px: {len(positions)} frame(s) and a full page "
                       f"({h}px tall) as {name}-{w}-*.png")
                if clicked:
                    rep.note(f"{w}px: clicked \"{clicked}\" on a consent banner")
                else:
                    rep.note(f"{w}px: no reject-only consent button; any banner was left "
                             f"in place and may cover part of the frames")
                ctx.close()
        finally:
            browser.close()
    save_record(out, {"kind": "site", "url": url, "title": title, "date": _now(),
                      "widths": widths, "pageHeights": heights, "consent": consent,
                      "files": files})
    rep.ok(f"recorded in {out / 'index.json'} — now look at every frame")


# ──────────────────────────────────────────────────────────── project ──

_COLLECT_JS = """
([match, minWidth]) => {
  const best = img => {
    // The largest candidate up to 2400w the page offers (else the smallest
    // above that), not the one this viewport happened to pick.
    const sets = [img.getAttribute('srcset') || ''];
    if (img.parentElement && img.parentElement.tagName === 'PICTURE')
      for (const s of img.parentElement.querySelectorAll('source'))
        sets.push(s.getAttribute('srcset') || '');
    let top = null, topW = 0, over = null, overW = Infinity;
    for (const set of sets)
      for (const part of set.split(/,\\s+/)) {
        const m = part.trim().match(/^(\\S+)\\s+(\\d+)w$/);
        if (!m) continue;
        const w = +m[2];
        if (w <= 2400 && w > topW) { topW = w; top = m[1]; }
        if (w > 2400 && w < overW) { overW = w; over = m[1]; }
      }
    if (!top && over) { top = over; topW = overW; }
    const u = top ? new URL(top, document.baseURI).href : (img.currentSrc || img.src);
    return [u, Math.max(topW, img.naturalWidth)];
  };
  const out = [];
  for (const img of document.querySelectorAll('img')) {
    const [src, w] = best(img);
    if (!src || src.startsWith('data:')) continue;
    if (match ? src.includes(match) : img.naturalWidth >= minWidth)
      out.push({src, w, alt: img.alt || ''});
  }
  return out;
}
"""


def _to_jpeg(data: bytes) -> bytes:
    Image, _, _, _ = cs._pil()
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            ground = Image.new("RGB", im.size, (255, 255, 255))
            ground.paste(im, mask=im.split()[-1])
            im = ground
        else:
            im = im.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def cmd_project(args, rep: bc.Report) -> None:
    url = _target(args.url)
    out = pathlib.Path(args.out)
    rep.section(f"PROJECT · {url} -> {out}")
    try:
        cs._pil()
    except RuntimeError as exc:
        rep.fail(str(exc))
        return
    sp = _browser_or_fail(rep)
    if not sp:
        return
    match = args.match if args.match is not None else default_match(url)
    with sp() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": 1400, "height": 1000},
                                      device_scale_factor=1, user_agent=UA_DESKTOP)
            page = ctx.new_page()
            _goto(page, url, args.timeout, rep, "page")
            page.wait_for_timeout(args.wait)
            clicked = dismiss_consent(page)
            scroll_through(page, 1000, max(args.wait // 8, 80), max_steps=args.max_scrolls)
            page.wait_for_timeout(max(args.wait // 4, 50))
            found = page.evaluate(_COLLECT_JS, [match, args.min_width])
            videos = page.evaluate("document.querySelectorAll('video').length")
            title = page.title()
            ctx.close()
        finally:
            browser.close()
    if clicked:
        rep.note(f"clicked \"{clicked}\" on a consent banner")
    images = dedupe(found)
    rule = f"src containing '{match}'" if match else f"at least {args.min_width}px wide"
    if not images:
        rep.fail(f"no images {rule} on the page; try --min-width or --match")
        return
    if len(images) > args.max:
        rep.warn(f"{len(images)} images found; downloading the first {args.max} (--max)")
        images = images[:args.max]
    out.mkdir(parents=True, exist_ok=True)
    files: List[str] = []
    entries: List[Dict] = []
    for it in images:
        try:
            jpg = _to_jpeg(fetch(it["src"], referer=url))
        except Exception as exc:                 # noqa: BLE001 - skip one, keep the rest
            rep.warn(f"could not download {it['src']}: {str(exc).splitlines()[0][:100]}")
            continue
        f = f"{len(files) + 1:02d}.jpg"
        (out / f).write_bytes(jpg)
        files.append(f)
        entries.append({"file": f, "src": it["src"], "alt": it.get("alt", "")})
    stale = re.compile(r"^\d{2,}\.jpg$")
    for old in out.iterdir():
        if stale.match(old.name) and old.name not in files:
            old.unlink()
    if not files:
        rep.fail("every download failed")
        return
    rep.ok(f"{len(files)} image(s) {rule}, in page order, as 01.jpg–{files[-1]}")
    if videos:
        rep.note(f"{videos} video(s) on the page were not captured; watch them in a browser")
    try:
        sheets, skipped = cs.build_sheets([out / f for f in files], out / "sheet", cols=2,
                                          numbered=True)
        rep.ok(f"contact sheets: {', '.join(s.name for s in sheets)}")
    except (RuntimeError, ValueError) as exc:
        sheets = []
        rep.fail(f"contact sheets: {exc}")
    save_record(out, {"kind": "project", "url": url, "title": title, "date": _now(),
                      "files": files, "images": entries,
                      "sheets": [s.name for s in sheets]})
    rep.ok(f"recorded in {out / 'index.json'} — now look at every sheet")


# ─────────────────────────────────────────────────────────────── main ──

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="refcapture", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("site", help="full page and scroll frames at each width")
    s.add_argument("url", help="a URL, or a local HTML file")
    s.add_argument("--out", required=True)
    s.add_argument("--widths", default="1440,390", help="viewport widths (default 1440,390)")
    s.add_argument("--height", type=int, help="viewport height (default 900, or 844 below 800px)")
    s.add_argument("--step", type=int, default=900, help="px between frames (default 900)")
    s.add_argument("--max-frames", type=int, default=12,
                   help="frames per width; a longer page is sampled evenly (default 12)")
    s.add_argument("--name", help="file name stem (default: a slug of the URL)")
    s.add_argument("--wait", type=int, default=3000, help="ms to let the page settle")
    s.add_argument("--timeout", type=int, default=45000, help="page load timeout in ms")
    s.set_defaults(fn=cmd_site)

    j = sub.add_parser("project", help="a gallery's large images in order, plus contact sheets")
    j.add_argument("url", help="a Behance/Dribbble project or any gallery page")
    j.add_argument("--out", required=True)
    j.add_argument("--max", type=int, default=40, help="most images to download (default 40)")
    j.add_argument("--min-width", type=int, default=800,
                   help="smallest natural width that counts as a project image (default 800)")
    j.add_argument("--match", help="keep only image URLs containing this (default: "
                                   "'project_modules' on Behance, else none)")
    j.add_argument("--max-scrolls", type=int, default=80, help="scroll steps to load the page")
    j.add_argument("--wait", type=int, default=4000, help="ms to let the page settle")
    j.add_argument("--timeout", type=int, default=60000, help="page load timeout in ms")
    j.set_defaults(fn=cmd_project)

    p.add_argument("--version", action="version", version=f"refcapture {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rep = bc.Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
