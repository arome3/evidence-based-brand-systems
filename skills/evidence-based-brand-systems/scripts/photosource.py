#!/usr/bin/env python3
"""photosource — free-licence stand-in photography, chosen by eye, on record.

Boards and early sites need real photographs before a shoot is commissioned.
This finds candidates on a CC0 library, puts them on numbered contact sheets
to be looked at, downloads only the ones picked, and records every file in
SOURCES.tsv so each stand-in can be traced and later replaced.

    photosource search TERM [TERM…] --source nappy --out DIR
        Each TERM is one search. New candidates are numbered after any
        already in DIR/candidates.json (numbers never change), thumbnails go
        to DIR/thumbs/, and DIR/sheet0.jpg, … show them all, numbered.
    photosource get DIR N [N…] --out HI_DIR
        Downloads candidates N… at full size into HI_DIR and appends one row
        per file to HI_DIR/SOURCES.tsv: file, source URL, page URL, source
        site, licence, date fetched, and "stand-in: replace with commissioned
        photography; never present as a customer".

Sources. Only nappy.co is built in: CC0 1.0 (https://nappy.co/license),
photographs of Black and brown people, and its search pages are plain HTML.
A search page carries its first results only (about 12 on nappy.co; more
load on scroll), so use several specific terms rather than one broad one.
Another source is one entry in SOURCES (search-URL template, image regex,
thumbnail and full-size suffixes, licence string), if its licence allows
commercial use without attribution AND it permits automated fetching.
Unsplash and Pexels do not fit: both need an API key for automated access and
block scraping, and their licences are their own, not CC0. Download from them
by hand and add the SOURCES.tsv rows yourself.

Look at every candidate before picking. Reject visible brand names or logos,
people who read as a different market, recognisable public figures, and
anything implying a real customer relationship.

`search` needs Pillow for the sheets (pip install pillow); `get` is standard
library. Exit code is 0 only if everything asked for was fetched.
"""
from __future__ import annotations

__version__ = "1.3.0"

import argparse
import datetime as _dt
import html as _html
import json
import os
import pathlib
import re
import sys
import urllib.request
from typing import Dict, List, Optional
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brandcheck as bc  # noqa: E402  (shared reporting)
import contactsheet as cs  # noqa: E402

UA = "Mozilla/5.0"
USE = "stand-in: replace with commissioned photography; never present as a customer"
TSV_HEADER = ["file", "source_url", "page_url", "source_site", "licence", "fetched", "use"]

# One entry per library. `image` must capture the photo's stable id as (?P<id>…);
# `page`, if given, finds links to each photo's own page and also captures (?P<id>…),
# so the navigation's decorative thumbnails can be told apart from the results.
SOURCES: Dict[str, Dict[str, str]] = {
    "nappy": {
        "site": "nappy.co",
        "search": "https://nappy.co/search/{q}",
        "image": r"https://images\.nappy\.co/photo/(?P<id>[A-Za-z0-9_\-]+)\.(?:jpe?g|png)",
        "page": r"""href=["'](?P<path>/photo/[^"'#?]*?(?:%2B|\+)(?P<id>[A-Za-z0-9_\-]+))["']""",
        "base": "https://nappy.co",
        # The image server reads width/quality (long edge); it ignores w/q and
        # would send the multi-megapixel original. Checked 2026-10-09.
        "thumb": "?width=400&quality=70",
        "full": "?width=1800&quality=82",
        "licence": "CC0 1.0 — nappy.co/license",
    },
}

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = r"""\b{}\s*=\s*(?:"([^"]*)"|'([^']*)')"""


def _attr(tag: str, name: str) -> Optional[str]:
    m = re.search(_ATTR.format(name), tag, re.I)
    return _html.unescape(m.group(1) if m.group(1) is not None else m.group(2)) if m else None


def search_url(source: str, term: str) -> str:
    return SOURCES[source]["search"].format(q=quote(term.strip(), safe=""))


def parse_candidates(page: str, source: str) -> List[Dict[str, Optional[str]]]:
    """Result photos on a search page, in page order, one per photo id."""
    cfg = SOURCES[source]
    image_re = re.compile(cfg["image"])
    titles: Dict[str, str] = {}
    for tag in _IMG_TAG.findall(page):
        src = _attr(tag, "src") or ""
        m = image_re.search(src)
        if m and m.group("id") not in titles:
            titles[m.group("id")] = (_attr(tag, "alt") or "").strip()
    pages: Dict[str, str] = {}
    if cfg.get("page"):
        for m in re.finditer(cfg["page"], page):
            pages.setdefault(m.group("id"), cfg.get("base", "") + _html.unescape(m.group("path")))
    found: List[Dict[str, Optional[str]]] = []
    seen = set()
    for m in image_re.finditer(page):
        pid = m.group("id")
        if pid in seen:
            continue
        seen.add(pid)
        found.append({"id": pid, "url": m.group(0), "page": pages.get(pid),
                      "title": titles.get(pid, "")})
    # Results link to their own photo page; navigation thumbnails do not.
    linked = [c for c in found if c["page"]]
    return linked if linked else found


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def image_kind(data: bytes) -> Optional[str]:
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def load_candidates(d: pathlib.Path) -> List[Dict]:
    p = d / "candidates.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{p} is not a candidates list (was it written by photosource?)")
    return data


def _err(exc: Exception) -> str:
    return str(exc).splitlines()[0][:120] if str(exc) else type(exc).__name__


def cmd_search(args, rep: bc.Report) -> None:
    out = pathlib.Path(args.out)
    rep.section(f"SEARCH · {args.source} · {', '.join(args.terms)} -> {out}")
    try:
        cands = load_candidates(out)
    except ValueError as exc:
        rep.fail(str(exc))
        return
    cfg = SOURCES[args.source]
    known = {(c["source"], c["id"]) for c in cands}
    nxt = max((c["n"] for c in cands), default=0) + 1
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    added = 0
    for term in args.terms:
        url = search_url(args.source, term)
        try:
            page = fetch(url).decode("utf-8", "replace")
        except Exception as exc:                 # noqa: BLE001 - one term, not the run
            rep.fail(f"'{term}': cannot fetch {url}: {_err(exc)}")
            continue
        found = parse_candidates(page, args.source)
        new = [c for c in found if (args.source, c["id"]) not in known]
        if args.max:
            new = new[:max(args.max - added, 0)]
        thumbs_ok = 0
        for c in new:
            rec = {"n": nxt, "source": args.source, "id": c["id"], "term": term,
                   "url": c["url"], "page": c["page"], "title": c["title"], "thumb": None}
            try:
                data = fetch(c["url"] + cfg["thumb"])
                if not image_kind(data):
                    raise ValueError("the response is not an image")
                rec["thumb"] = f"thumbs/{nxt:03d}.jpg"
                (out / rec["thumb"]).write_bytes(data)
                thumbs_ok += 1
            except Exception as exc:             # noqa: BLE001 - listed, not on the sheet
                rep.warn(f"#{nxt}: no thumbnail ({_err(exc)}); it is listed but not on a sheet")
            cands.append(rec)
            known.add((args.source, c["id"]))
            nxt += 1
            added += 1
        if found:
            rep.ok(f"'{term}': {len(found)} result(s), {len(new)} new "
                   f"({len(found) - len(new)} already listed or over --max)")
        else:
            rep.warn(f"'{term}': no results on {url} (the page layout may have changed)")
    (out / "candidates.json").write_text(json.dumps(cands, indent=1, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
    if not cands:
        rep.fail("no candidates")
        return
    shown = [c for c in cands if c.get("thumb") and (out / c["thumb"]).exists()]
    try:
        sheets, skipped = cs.build_sheets([out / c["thumb"] for c in shown], out / "sheet",
                                          cols=6, numbered=True, labels=[c["n"] for c in shown])
    except (RuntimeError, ValueError) as exc:
        rep.fail(f"contact sheets: {exc}")
        return
    for path, why in skipped:
        rep.warn(f"unreadable thumbnail {path}: {why}")
    rep.ok(f"{len(cands)} candidate(s) in candidates.json; sheets: "
           f"{', '.join(s.name for s in sheets)}")
    rep.note(f"look at every sheet, then: photosource get {out} N [N…] --out HI_DIR. "
             f"Licence: {cfg['licence']}")


def _tsv_rows(path: pathlib.Path) -> List[List[str]]:
    if not path.exists():
        return []
    return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line]


def cmd_get(args, rep: bc.Report) -> None:
    d, out = pathlib.Path(args.dir), pathlib.Path(args.out)
    rep.section(f"GET · {', '.join(map(str, args.numbers))} from {d} -> {out}")
    try:
        by_n = {c["n"]: c for c in load_candidates(d)}
    except ValueError as exc:
        rep.fail(str(exc))
        return
    if not by_n:
        rep.fail(f"no candidates.json in {d}; run photosource search first")
        return
    out.mkdir(parents=True, exist_ok=True)
    tsv = out / "SOURCES.tsv"
    rows = _tsv_rows(tsv)
    if rows and rows[0] != TSV_HEADER:
        rep.warn(f"{tsv} has a different layout; new rows use: {' | '.join(TSV_HEADER)}")
    listed = {r[0] for r in rows}
    new_rows: List[List[str]] = []
    today = _dt.date.today().isoformat()
    for n in args.numbers:
        c = by_n.get(n)
        if not c:
            rep.fail(f"#{n}: not in {d / 'candidates.json'} (numbers 1–{max(by_n)})")
            continue
        cfg = SOURCES.get(c["source"])
        if not cfg:
            rep.fail(f"#{n}: unknown source {c['source']!r}")
            continue
        try:
            data = fetch(c["url"] + cfg["full"])
        except Exception as exc:                 # noqa: BLE001 - one photo, not the run
            rep.fail(f"#{n}: cannot download {c['url']}: {_err(exc)}")
            continue
        kind = image_kind(data)
        if not kind:
            rep.fail(f"#{n}: {c['url']} did not return an image (blocked, or moved?)")
            continue
        name = f"{c['source']}-{c['id']}.{kind}"
        (out / name).write_bytes(data)
        if name in listed:
            rep.ok(f"#{n}: {name} re-downloaded ({len(data) // 1024} KB); already in SOURCES.tsv")
            continue
        new_rows.append([name, c["url"], c.get("page") or "", cfg["site"], cfg["licence"],
                         today, USE])
        listed.add(name)
        rep.ok(f"#{n}: {name} ({len(data) // 1024} KB) — {c.get('title') or 'untitled'}")
    if new_rows:
        with tsv.open("a", encoding="utf-8") as fh:
            if not rows:
                fh.write("\t".join(TSV_HEADER) + "\n")
            for r in new_rows:
                fh.write("\t".join(v.replace("\t", " ").replace("\n", " ") for v in r) + "\n")
        rep.ok(f"{len(new_rows)} row(s) appended to {tsv}")
    rep.note("stand-ins only: never attach a name, quote or business to a stock person")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="photosource", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find candidates and lay them out on numbered sheets")
    s.add_argument("terms", nargs="+", metavar="TERM", help="one search per term "
                                                            "(quote multi-word terms)")
    s.add_argument("--source", default="nappy", choices=sorted(SOURCES))
    s.add_argument("--out", required=True)
    s.add_argument("--max", type=int, default=90,
                   help="most new candidates added by this run (default 90; 0 = no limit)")
    s.set_defaults(fn=cmd_search)

    g = sub.add_parser("get", help="download picked candidates and record them in SOURCES.tsv")
    g.add_argument("dir", help="the search directory (holds candidates.json)")
    g.add_argument("numbers", nargs="+", type=int, metavar="N")
    g.add_argument("--out", required=True)
    g.set_defaults(fn=cmd_get)

    p.add_argument("--version", action="version", version=f"photosource {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rep = bc.Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
