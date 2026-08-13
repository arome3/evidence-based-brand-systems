#!/usr/bin/env python3
"""brandcheck — mechanical verification for a brand system.

Everything a brand system claims that a machine can check, this checks. What it
cannot check (taste, differentiation, strategic fit) is left to the reviewer, by
design: see references/verification.md.

    brandcheck contrast  PAIRS.tsv            compute every declared pairing
    brandcheck tokens    DIR                  CSS <-> JSON agreement, themes, var() resolution
    brandcheck fonts     FONT.ttf [--glyphs …] glyph coverage, OT features, axes
    brandcheck lexicon   DIR                  banned words + fabricated-proof patterns
    brandcheck all       DIR                  everything above that applies

Exit code is 0 only if every check passed. Non-zero means do not ship.

stdlib only, except `fonts`, which needs fontTools (pip install fonttools).
Python 3.9+.
"""
from __future__ import annotations

__version__ = "1.1.0"

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────── reporting ──

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GRN, YEL, CYA = "\033[31m", "\033[32m", "\033[33m", "\033[36m"
_TTY = sys.stdout.isatty()


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}" if _TTY else text


class Report:
    """Collects results so a run can print one verdict at the end."""

    def __init__(self) -> None:
        self.passes: List[str] = []
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.notes: List[str] = []

    def ok(self, msg: str) -> None:
        self.passes.append(msg)
        print(f"  {_c('PASS', GRN)}  {msg}")

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"  {_c('FAIL', RED)}  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  {_c('WARN', YEL)}  {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        print(f"  {_c('note', DIM)}  {msg}")

    def section(self, title: str) -> None:
        print(f"\n{_c(title, BOLD + CYA)}")

    def verdict(self) -> int:
        print("\n" + "─" * 68)
        if self.failures:
            print(_c(f"FAILED — {len(self.failures)} check(s) must be fixed before shipping", RED + BOLD))
            for f in self.failures:
                print(f"  · {f}")
        else:
            print(_c(f"PASSED — {len(self.passes)} check(s)", GRN + BOLD))
        if self.warnings:
            print(_c(f"\n{len(self.warnings)} warning(s) — review, but not blocking:", YEL))
            for w in self.warnings:
                print(f"  · {w}")
        return 1 if self.failures else 0


# ─────────────────────────────────────────────────────────── contrast ──
# WCAG 2.x relative luminance and contrast ratio.
# https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
# https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio

def _srgb(channel8: int) -> float:
    c = channel8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def parse_hex(value: str) -> Tuple[int, int, int]:
    h = value.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) == 8:  # #RRGGBBAA — alpha ignored, see note in ratio()
        h = h[:6]
    if len(h) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in h):
        raise ValueError(f"not a hex colour: {value!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def luminance(value: str) -> float:
    r, g, b = parse_hex(value)
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def ratio(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def fmt_ratio(r: float) -> str:
    """Truncate, never round up.

    A pairing reported as 4.50:1 that is actually 4.4951:1 does not meet the
    requirement. Rounding up a contrast ratio is how inaccessible palettes get
    signed off.
    """
    return f"{int(r * 100) / 100:.2f}"


# Thresholds, from WCAG 2.2. `large` is >=24px, or >=18.66px when bold.
THRESHOLDS = {"normal": 4.5, "large": 3.0, "ui": 3.0, "aaa": 7.0, "aaa-large": 4.5}


def cmd_contrast(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"CONTRAST · {args.pairs}")
    if not os.path.exists(args.pairs):
        rep.fail(f"pairs file not found: {args.pairs}")
        return

    rows, seen = [], set()
    for lineno, raw in enumerate(open(args.pairs, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            rep.fail(f"line {lineno}: expected 4 tab-separated fields "
                     f"(name, fg, bg, threshold), got {len(parts)}")
            continue
        name, fg, bg, thr_raw = (p.strip() for p in parts[:4])
        thr = THRESHOLDS.get(thr_raw.lower(), None)
        if thr is None:
            try:
                thr = float(thr_raw)
            except ValueError:
                rep.fail(f"line {lineno}: threshold {thr_raw!r} is not a number "
                         f"or one of {', '.join(THRESHOLDS)}")
                continue
        try:
            r = ratio(fg, bg)
        except ValueError as exc:
            rep.fail(f"line {lineno}: {exc}")
            continue
        key = (fg.lower(), bg.lower(), thr)
        rows.append((name, fg, bg, r, thr, key in seen))
        seen.add(key)

    if not rows:
        rep.fail("no pairings found — an empty contrast file is not a passing contrast file")
        return

    width = max(len(r[0]) for r in rows)
    failures = 0
    for name, fg, bg, r, thr, dup in rows:
        mark = _c("PASS", GRN) if r >= thr else _c("FAIL", RED)
        dupe = _c("  (duplicate pair)", DIM) if dup else ""
        print(f"  {mark}  {name:<{width}}  {fg} on {bg}  "
              f"{fmt_ratio(r):>6}:1  needs {thr}:1{dupe}")
        if r < thr:
            failures += 1

    tightest = min(rows, key=lambda x: x[3] / x[4])
    if failures:
        rep.fail(f"{failures} of {len(rows)} pairing(s) below threshold")
    else:
        rep.ok(f"all {len(rows)} declared pairings meet their threshold "
               f"(tightest: {tightest[0]} at {fmt_ratio(tightest[3])}:1 "
               f"against {tightest[4]}:1)")
        headroom = tightest[3] / tightest[4]
        if headroom < 1.05:
            rep.warn(f"'{tightest[0]}' has under 5% headroom — any darkening of that "
                     f"ground will break it. Recompute before changing the token.")


# ───────────────────────────────────────────────────────────── tokens ──

CSS_VAR = re.compile(r"(--[a-zA-Z][\w-]*)\s*:\s*([^;]+);")
RAW_COLOUR = re.compile(r"(?:#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)|\boklch\([^)]*\))")


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _balanced_block(text: str, start: int) -> Tuple[str, int]:
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
    raise ValueError("unbalanced braces in CSS")


def _vars_in(text: str) -> Dict[str, str]:
    return {m.group(1): " ".join(m.group(2).split()) for m in CSS_VAR.finditer(text)}


def _scoped(css: str, pattern: str) -> Tuple[Dict[str, str], List[Tuple[int, int]]]:
    found: Dict[str, str] = {}
    spans: List[Tuple[int, int]] = []
    pos = 0
    while True:
        m = re.search(pattern, css[pos:])
        if not m:
            return found, spans
        start = pos + m.start()
        body, end = _balanced_block(css, start)
        found.update(_vars_in(body))
        spans.append((start, end))
        pos = end


def _render_value(raw):
    """Reduce a token value to a comparable string.

    DTCG 2025.10 made several types OBJECTS rather than strings:
      color     -> {colorSpace, components, alpha?, hex?}
      dimension -> {value, unit}
      duration  -> {value, unit}
    A checker that treats an object $value as a group silently skips every
    colour token in a valid 2025.10 file, and then reports the file as clean.
    """
    if isinstance(raw, dict):
        if "hex" in raw:
            return str(raw["hex"])
        if "colorSpace" in raw and "components" in raw:
            comps = " ".join(str(c) for c in raw["components"])
            alpha = f" / {raw['alpha']}" if "alpha" in raw else ""
            return f"{raw['colorSpace']}({comps}{alpha})"
        if "value" in raw and "unit" in raw:
            return f"{raw['value']}{raw['unit']}"
        return json.dumps(raw, sort_keys=True, separators=(",", ":"))
    if isinstance(raw, list):
        return json.dumps(raw, separators=(",", ":"))
    return str(raw)


def _walk_tokens(node, path, flat, dtcg):
    """Collect tokens two ways.

    `flat`  — leaves already keyed by a CSS custom property name (--foo).
    `dtcg`  — leaves keyed by their dotted group path (a.b.c), which by the
              near-universal convention maps to --a-b-c.

    Supports both {"value": …} and DTCG {"$value": …} leaves, and resolves
    DTCG aliases of the form {group.token}.
    """
    if not isinstance(node, dict):
        return
    for key, val in node.items():
        if key.startswith("$") or not isinstance(val, dict):
            continue
        has_value = "$value" in val or "value" in val
        if has_value:
            rendered = _render_value(val.get("$value", val.get("value")))
            if key.startswith("--"):
                flat[key] = rendered
            else:
                dtcg[".".join(path + [key])] = rendered
        else:
            _walk_tokens(val, path + [key], flat, dtcg)


CSS_REF = re.compile(r"var\(\s*(--[a-zA-Z][\w-]*)\s*(?:,[^()]*)?\)")
DTCG_REF = re.compile(r"\{([^}]+)\}")


def _resolve_all(by_css_name, by_dtcg_path, max_depth=12):
    """Fully resolve `var(--x)` and `{a.b.c}` references to literal values.

    Both sides of a CSS<->JSON comparison must be resolved the same way, or
    every aliased token reads as a false mismatch. Values that still contain a
    reference after resolution are returned unchanged and reported separately
    rather than counted as disagreements.
    """
    out = dict(by_css_name)
    for _ in range(max_depth):
        changed = False
        for key, val in list(out.items()):
            new_val = val

            def css_sub(m):
                name = m.group(1)
                return out[name] if name in out and out[name] != val else m.group(0)

            def dtcg_sub(m):
                path = m.group(1)
                if path in by_dtcg_path:
                    return by_dtcg_path[path]
                css_name = _dtcg_to_css_name(path)
                return out[css_name] if css_name in out else m.group(0)

            new_val = CSS_REF.sub(css_sub, new_val)
            new_val = DTCG_REF.sub(dtcg_sub, new_val)
            if new_val != val:
                out[key] = new_val
                changed = True
        if not changed:
            break
    return out


def _unresolved(value):
    return bool(CSS_REF.search(value) or DTCG_REF.search(value))


def _dtcg_to_css_name(path):
    return "--" + path.replace(".", "-")


EXTERNAL_REF = re.compile(
    r"""<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*?"""
    r"""\b(?:src|href|data)\s*=\s*["'](?!#|data:)([^"']+)["']""", re.I | re.S)
FONT_HOST = re.compile(r"fonts\.(?:googleapis|gstatic|bunny)\.(?:com|net)", re.I)


def _check_self_contained(name, text, rep):
    """The artifact must open from disk with no build step and no fetches.

    A style tile that silently depends on a CDN looks fine on the machine that
    made it and breaks on the client's laptop, in a locked-down enterprise
    network, or in an air-gapped review. The permitted exception is a webfont
    import, because the system is required to work without it anyway.
    """
    external, fonts = [], []
    for m in EXTERNAL_REF.finditer(text):
        url = m.group(1).strip()
        if url.startswith(("http://", "https://", "//")):
            (fonts if FONT_HOST.search(url) else external).append(url)
        elif not url.startswith(("#", "data:", "mailto:", "tel:")):
            external.append(url)          # a local file is still a dependency
    for u in re.findall(r"@import\s+url\(\s*['\"]?([^'\")]+)", text):
        (fonts if FONT_HOST.search(u) else external).append(u)
    if external:
        rep.fail(f"{name}: not self-contained — {len(external)} external or local "
                 f"dependency(ies): {sorted(set(external))[:4]}. The artifact must open "
                 f"from disk with no build step and no fetches.")

    # A webfont import is only convenience if the fonts are ALSO self-hosted.
    # With no @font-face, the CDN *is* the typography, and the artifact silently
    # loses its typefaces on a locked-down network or in an offline review.
    face_blocks = len(re.findall(r"@font-face\s*\{", text, re.I))
    if fonts and face_blocks == 0:
        rep.fail(f"{name}: depends on a webfont CDN for its typography — "
                 f"{len(fonts)} remote import and zero @font-face blocks. Self-host the "
                 f"faces (or embed them) so the import is genuinely optional; the system "
                 f"is required to work without it.")
    elif not external:
        detail = (f"; {len(fonts)} webfont import backed by {face_blocks} self-hosted "
                  f"@font-face block(s)" if fonts else "")
        rep.ok(f"{name}: self-contained (no external dependencies{detail})")
    if re.search(r"<img\b", text, re.I):
        rep.warn(f"{name}: contains <img>. Version one should require no image assets — "
                 f"they are the first thing to rot and the first thing a licence dispute touches.")


def cmd_tokens(args: argparse.Namespace, rep: Report) -> None:
    d = args.dir
    css_path = args.css or os.path.join(d, "tokens.css")
    json_path = args.json or os.path.join(d, "tokens.json")
    rep.section(f"TOKENS · {os.path.relpath(css_path)} <-> {os.path.relpath(json_path)}")

    if not os.path.exists(css_path):
        rep.fail(f"missing {css_path}")
        return
    css = open(css_path, encoding="utf-8").read()
    clean = _strip_comments(css)

    dark_media, s1 = _scoped(clean, r"@media\s*\(prefers-color-scheme:\s*dark\)")
    dark_attr, s2 = _scoped(clean, r'\[data-theme=["\']dark["\']\]\s*\{')
    responsive, s3 = _scoped(clean, r"@media\s*\(min-width:")
    reduced, s4 = _scoped(clean, r"@media\s*\(prefers-reduced-motion:")

    base_src = clean
    for a, b in sorted(s1 + s2 + s3 + s4, reverse=True):
        base_src = base_src[:a] + base_src[b:]
    base = _vars_in(base_src)

    if not base:
        rep.fail("no custom properties found in the CSS — is this a token file?")
        return
    rep.ok(f"{len(base)} base tokens parsed")

    # 1. Theme parity: a page must not disagree with itself about what dark means.
    if dark_media or dark_attr:
        mismatch = {k: (dark_media.get(k), dark_attr.get(k))
                    for k in set(dark_media) | set(dark_attr)
                    if dark_media.get(k) != dark_attr.get(k)}
        if not dark_media or not dark_attr:
            rep.warn("only one dark-theme mechanism found. Ship both a "
                     "prefers-color-scheme block and a [data-theme] block, or an explicit "
                     "user choice cannot override the system preference.")
        elif mismatch:
            rep.fail(f"dark-theme blocks disagree on {len(mismatch)} token(s): "
                     f"{list(mismatch)[:4]}")
        else:
            rep.ok("prefers-color-scheme dark and [data-theme=dark] define identical values")

        guard = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*"
                          r":root:not\(\[data-theme=[\"']light[\"']\]\)", clean)
        if dark_media and not guard:
            rep.warn("the prefers-color-scheme dark block is not guarded with "
                     ":root:not([data-theme=\"light\"]) — an explicit light choice will not "
                     "win over a dark system preference.")

    # 2. CSS <-> JSON agreement.
    if os.path.exists(json_path):
        try:
            data = json.load(open(json_path, encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rep.fail(f"tokens.json is not valid JSON: {exc}")
            return
        rep.ok("tokens.json parses as valid JSON")
        flat, dtcg = {}, {}
        _walk_tokens(data.get("tokens", data), [], flat, dtcg)
        jtok = dict(flat)
        derived = {_dtcg_to_css_name(k): v for k, v in dtcg.items()}
        # Prefer explicit --names; fall back to the path convention.
        for k, v in derived.items():
            jtok.setdefault(k, v)

        if not jtok:
            rep.warn("no tokens recognised in the JSON — expected {\"value\": …} or DTCG "
                     "{\"$value\": …} leaves. Skipping the agreement check.")
        else:
            overlap = len(set(base) & set(jtok))
            coverage = overlap / max(len(base), 1)
            if coverage < 0.5:
                rep.fail(
                    f"the two token files have no verifiable correspondence — only "
                    f"{overlap} of {len(base)} CSS tokens could be matched to a JSON token "
                    f"({coverage:.0%}). Either name JSON leaves with their CSS custom "
                    f"property, or use the DTCG path convention where a.b.c maps to --a-b-c, "
                    f"and state the contract in $description. Two formats that cannot be "
                    f"diffed will drift, and nobody will notice.")
                if dtcg:
                    sample = list(dtcg)[:3]
                    rep.note(f"JSON paths look like: {sample} -> "
                             f"{[_dtcg_to_css_name(x) for x in sample]}")
                    rep.note(f"CSS names look like: {list(base)[:3]}")
            else:
                base_r = _resolve_all(base, dtcg)
                jtok_r = _resolve_all(jtok, dtcg)
                missing = [k for k in base if k not in jtok]
                extra = [k for k in jtok if k not in base]

                def _same(a, b):
                    a, b = " ".join(a.split()), " ".join(b.split())
                    # A DTCG colour object renders to its hex fallback; a CSS
                    # token holds the same hex. Those agree.
                    if a.lower() == b.lower():
                        return True
                    try:
                        return parse_hex(a) == parse_hex(b)
                    except ValueError:
                        return False

                comparable, unresolved = [], []
                for k in base:
                    if k not in jtok:
                        continue
                    a, b = base_r[k], jtok_r[k]
                    (unresolved if (_unresolved(a) or _unresolved(b)) and not _same(a, b)
                     else comparable).append((k, a, b))
                diff = [(k, a, b) for k, a, b in comparable if not _same(a, b)]
                if unresolved:
                    rep.warn(f"{len(unresolved)} composite token(s) could not be fully "
                             f"resolved for comparison (e.g. {unresolved[0][0]}) — verify "
                             f"these by hand or emit resolved literals in the generated file")
                if missing:
                    rep.fail(f"{len(missing)} token(s) in CSS but absent from JSON: {missing[:5]}")
                if extra:
                    rep.warn(f"{len(extra)} token(s) in JSON with no CSS counterpart: {extra[:5]}")
                if diff:
                    rep.fail(f"{len(diff)} value mismatch(es), e.g. "
                             + "; ".join(f"{k}: css={a!r} json={b!r}" for k, a, b in diff[:3]))
                if not (missing or diff):
                    rep.ok(f"all {len(comparable)} comparable tokens agree between CSS and JSON "
                           f"({coverage:.0%} of the CSS set matched)")
    else:
        rep.warn(f"no {os.path.basename(json_path)} found — shipping only one token format "
                 f"means downstream tools cannot consume the system")

    # 3. var() references resolve, across CSS and any HTML in the directory.
    defined = set(base) | set(dark_media) | set(dark_attr) | set(responsive) | set(reduced)
    sources = [(os.path.basename(css_path), css)]
    for name in sorted(os.listdir(d)):
        if name.endswith((".html", ".htm")):
            sources.append((name, open(os.path.join(d, name), encoding="utf-8").read()))
    for name, text in sources:
        local = set(CSS_VAR.findall(text) and [m.group(1) for m in CSS_VAR.finditer(text)])
        used = set(re.findall(r"var\(\s*(--[a-zA-Z][\w-]*)", text))
        unresolved = sorted(used - defined - local)
        if unresolved:
            rep.fail(f"{name}: {len(unresolved)} unresolved var() reference(s): {unresolved[:5]}")
        elif used:
            rep.ok(f"{name}: all {len(used)} var() references resolve")

    # 4. Colour discipline in markup: raw values outside token declarations.
    for name, text in sources[1:]:
        styles = "".join(re.findall(r"<style[^>]*>(.*?)</style>", text, flags=re.S))
        without_decls = CSS_VAR.sub("", styles)
        raws = [r for r in RAW_COLOUR.findall(without_decls)
                if r.lower() not in ("#fff", "#ffffff", "#000", "#000000")]
        if raws:
            rep.fail(f"{name}: {len(raws)} raw colour value(s) outside token declarations "
                     f"({sorted(set(raws))[:5]}) — component CSS must reference tokens")
        else:
            rep.ok(f"{name}: no raw colour outside token declarations")
        _check_self_contained(name, text, rep)


# ────────────────────────────────────────────────────────────── fonts ──

DEFAULT_GLYPHS = "=≠?→✓·—–…"


def cmd_fonts(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"FONTS · {os.path.basename(args.font)}")
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        rep.warn("fontTools not installed — cannot verify the font binary. "
                 "Install it (pip install fonttools) and re-run; a specimen page is "
                 "not evidence that a glyph exists.")
        return
    if not os.path.exists(args.font):
        rep.fail(f"font not found: {args.font}")
        return

    f = TTFont(args.font, fontNumber=0, lazy=True)
    cmap = f.getBestCmap()
    rep.ok(f"{len(cmap)} mapped codepoints")

    feats = set()
    for tag in ("GSUB", "GPOS"):
        if tag in f:
            table = f[tag].table
            if table.FeatureList:
                feats |= {r.FeatureTag for r in table.FeatureList.FeatureRecord}

    # Glyph coverage — the check that catches "the font does not have a tick".
    missing = [ch for ch in (args.glyphs or DEFAULT_GLYPHS) if ord(ch) not in cmap]
    if missing:
        rep.fail("missing glyph(s): " + " ".join(
            f"{ch!r} (U+{ord(ch):04X})" for ch in missing) +
            " — any UI relying on these will render tofu in this family")
    else:
        rep.ok(f"all {len(args.glyphs or DEFAULT_GLYPHS)} required glyphs present")

    # Tabular figures — measured, not assumed.
    upem = f["head"].unitsPerEm
    hmtx = f["hmtx"]
    digits = [cmap.get(ord(d)) for d in "0123456789"]
    widths = [hmtx[g][0] for g in digits if g and g in hmtx.metrics]
    if len(widths) == 10:
        uniform = len(set(widths)) == 1
        if uniform:
            rep.ok(f"digits are uniform by default ({widths[0]}/{upem}) — tabular without a feature")
        elif "tnum" in feats:
            rep.ok("digits are proportional by default, but a 'tnum' feature is present — "
                   "you MUST set font-variant-numeric: tabular-nums for numeric columns")
        else:
            rep.fail("digits are NOT uniform and there is NO 'tnum' feature — this family "
                     "cannot produce aligned numeric columns, and "
                     "font-variant-numeric: tabular-nums will silently do nothing")
    if "zero" not in feats:
        rep.note("no slashed-zero ('zero') feature — fine unless identifiers are set in this face")

    if "fvar" in f:
        axes = ", ".join(f"{a.axisTag} {a.minValue:g}–{a.maxValue:g}" for a in f["fvar"].axes)
        rep.ok(f"variable font: {axes}")
        rep.note("declare exactly this range in @font-face; a wider declared range makes "
                 "browsers synthesise smeared fake weights")
    else:
        rep.note("static font — one file per weight/style")

    # Reserved Font Name status CANNOT be read from the binary. IBM Plex Sans is
    # the counterexample: its OFL.txt declares Reserved Font Name "Plex" while the
    # shipped binary's name table contains no RFN string at all. A pipeline that
    # greps binaries would clear it for rename-free modification, incorrectly.
    # The accompanying licence file is the source of truth.
    if args.licence:
        if os.path.exists(args.licence):
            text = open(args.licence, encoding="utf-8", errors="replace").read()
            rep.ok(f"licence file present ({os.path.basename(args.licence)})")
            m = re.search(r'Reserved Font Name[\s:]*["\u201c\u2018]?([^"\u201d\u2019\n)]+)', text)
            if m:
                rep.warn(f'declares Reserved Font Name "{m.group(1).strip()}" — subset freely, '
                         f'but any modification to the outlines (or to the name table) requires '
                         f'renaming the derivative')
            else:
                rep.ok("no Reserved Font Name declared in the licence")
            if "SIL OPEN FONT LICENSE" not in text.upper() and "Apache" not in text:
                rep.warn("licence text is neither OFL nor Apache — confirm it permits "
                         "commercial use, embedding and self-hosting before shipping")
        else:
            rep.fail(f"licence file not found: {args.licence} — the OFL requires the copyright "
                     f"and licence notice to travel with the font files you ship")
    else:
        rep.warn("no --licence given. Reserved Font Name status CANNOT be determined from the "
                 "binary (IBM Plex declares an RFN in its OFL.txt but carries none in the font's "
                 "name table). Pass --licence to check it, and ship that file with the fonts.")


# ──────────────────────────────────────────────────────────── lexicon ──
# Precision over recall, deliberately. A linter that flags quoted competitor
# copy and its own prohibition lists gets switched off, and then it protects
# nothing. Every suppression rule below exists because it fired on real,
# correct brand documentation.

BANNED_WORDS = [
    "revolutionary", "cutting-edge", "seamless", "game-changing", "unleash",
    "supercharge", "next-gen", "empower", "world-class", "holistic",
    "best-in-class", "bleeding-edge", "paradigm shift", "synergy",
]
# Patterns that assert proof. Each needs a real, dated referent or it is fabricated.
PROOF_PATTERNS = [
    (r"\btrusted by\b", "'trusted by' claim"),
    (r"\bSOC\s?2\b", "SOC 2 reference"),
    (r"\bISO\s?27001\b", "ISO 27001 reference"),
    (r"\b(?:HIPAA|GDPR|PCI[- ]DSS)\s+compliant\b", "compliance claim"),
    (r"\b\d[\d,]*\+\s*(?:customers|companies|teams|users|brands|clients)\b", "customer-count claim"),
    (r"\b(?:magic quadrant|forrester wave|gartner peer insights)\b", "analyst-recognition claim"),
    (r"\b\d\.\d\s*/\s*5\b", "rating claim"),
    (r"\b(?:award[- ]winning|industry[- ]leading|#1\b)", "superlative proof claim"),
]

# A line that forbids, negates, restricts or conditions a term is not asserting it.
NEGATION = re.compile(
    r"\b(?:ban|banned|banning|forbid|forbidden|prohibit|prohibited|never|avoid|avoided|"
    r"reject|rejected|don'?t|do not|does not|did not|cannot|can'?t|must not|may not|"
    r"no longer|none of|not currently|not yet|villain|anti-pattern|antipattern|"
    r"instead of|rather than|not a |without |absent|refuse|refused|deleted|removed|"
    r"omit|omitted|unavailable|unearned|fabricat|borrowed authority|misuse|"
    r"prohibited usage|permitted only|only to|only when|restricted|withheld|held pending|"
    r"pending|conditions|requires prior|subject to|unless|expires?|lapses?)\b", re.I)

# The check's own bar is "needs a real, dated, verifiable referent". A line that
# carries a date, an as-of, or an explicit attribution has met that bar; flagging
# it is noise. Confirmed against real governance documentation where every such
# line was correct.
HAS_REFERENT = re.compile(
    r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\bdated\b|\bas of\b|\bclient-asserted\b|"
    r"\bper\s+\w+\s+\d{4}\b|\breport\s+dated\b", re.I)

# An explicitly withheld or unfilled value is the opposite of a fabrication.
WITHHELD = re.compile(
    r"\[[^\]]*(?:withheld|not supplied|not yet|tbd|pending|placeholder|open|unknown|"
    r"to be confirmed|redacted)[^\]]*\]", re.I)

# A question about a claim is not the claim.
INTERROGATIVE = re.compile(
    r"(?:^|\|)\s*(?:\*\*)?\s*(?:what|which|who|when|where|how|is|are|does|do)\b"
    r"|\?\s*(?:\*\*)?\s*\|?\s*$", re.I)

# A line carrying a research/evidence label is describing someone else's material.
RESEARCH_LABEL = re.compile(
    r"\[(?:VERIFIED|OBSERVED|INTERPRETATION|VISUAL OBSERVATION|VERIFIED IMPLEMENTATION|"
    r"Verified fact|Internal product claim|Projection|Strategic recommendation|"
    r"Copywriting judgment|Assumption)[^\]]*\]", re.I)

# Straight and curly quote pairs, plus code spans.
QUOTED = re.compile(r"[\"\u201c\u2018\u00ab][^\"\u201d\u2019\u00bb]{0,400}?[\"\u201d\u2019\u00bb]|`[^`]{0,200}`")


def _suppressed(line: str, span: Tuple[int, int],
                context: str = "") -> Optional[str]:
    """Return why this hit is not a violation, or None if it is one.

    `context` is the surrounding lines. A claim's date or attribution often sits
    on an adjacent line -- HTML wraps, and a markdown table keeps the date in a
    different cell -- so a strictly line-based test reports correct governance
    documentation as suspect. Checked against real regulated-industry brand
    docs, where every such flag was a false positive.
    """
    window = context or line
    if WITHHELD.search(window):
        return "explicitly withheld or unfilled"
    if HAS_REFERENT.search(window):
        return "carries a date or attribution"
    if INTERROGATIVE.search(line):
        return "an open question, not a claim"
    if NEGATION.search(line):
        return "prohibition, restriction or condition"
    if RESEARCH_LABEL.search(line):
        return "labelled research observation"
    for q in QUOTED.finditer(line):
        if q.start() <= span[0] and span[1] <= q.end():
            return "inside quoted material"
    return None


def _scan_text(path: str, text: str, rep: Report, strict: bool,
               show_all: bool) -> Tuple[int, int, int]:
    words = proofs = suppressed = 0
    in_fence = False
    all_lines = text.splitlines()
    for i, line in enumerate(all_lines, 1):
        # A referent usually FOLLOWS its claim -- a definition list, a table row,
        # a footnote -- so the forward window is wider than the backward one.
        window = "\n".join(all_lines[max(0, i - 3):i + 8])
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        checks = [(re.compile(rf"\b{re.escape(w)}\b", re.I), f"banned term '{w}'", True)
                  for w in BANNED_WORDS]
        checks += [(re.compile(pat, re.I), label, False) for pat, label in PROOF_PATTERNS]
        for rx, label, is_word in checks:
            for m in rx.finditer(line):
                why = _suppressed(line, m.span(), window)
                if why:
                    suppressed += 1
                    if show_all:
                        rep.note(f"{os.path.basename(path)}:{i} {label} suppressed ({why})")
                    continue
                msg = f"{os.path.basename(path)}:{i} {label} — {line.strip()[:88]}"
                if is_word:
                    words += 1
                    rep.fail(msg)
                else:
                    proofs += 1
                    (rep.fail if strict else rep.warn)(
                        msg + "  [needs a real, dated, verifiable referent]")
    return words, proofs, suppressed


def cmd_lexicon(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"LEXICON & PROOF · {args.dir}")
    targets = []
    for root, _dirs, files in os.walk(args.dir):
        if any(p in root for p in (".git", "node_modules", "__pycache__")):
            continue
        for name in sorted(files):
            if name.endswith((".md", ".html", ".htm", ".txt")):
                targets.append(os.path.join(root, name))
    if not targets:
        rep.warn("no .md/.html files found to scan")
        return

    tw = tp = ts = 0
    for path in targets:
        w, p, sup = _scan_text(path, open(path, encoding="utf-8", errors="replace").read(),
                               rep, args.strict, args.show_suppressed)
        tw += w; tp += p; ts += sup
    if tw == 0:
        rep.ok(f"no banned marketing terms in the brand's own voice ({len(targets)} file(s))")
    if tp == 0:
        rep.ok("no unreferenced proof or compliance claims")
    else:
        rep.note("proof hits are not automatically wrong — each must trace to something "
                 "real, dated and checkable. Confirm every one by hand.")
    if ts:
        rep.note(f"{ts} match(es) suppressed as quoted material, labelled research, or "
                 f"prohibitions. Re-run with --show-suppressed to audit them.")


# ──────────────────────────────────────────────────────────────── all ──

def cmd_all(args: argparse.Namespace, rep: Report) -> None:
    d = args.dir
    cmd_tokens(argparse.Namespace(dir=d, css=None, json=None), rep)
    pairs = getattr(args, "pairs", None) or os.path.join(d, "pairs.tsv")
    if os.path.exists(pairs):
        cmd_contrast(argparse.Namespace(pairs=pairs), rep)
    else:
        rep.section("CONTRAST")
        rep.fail(f"no pairings file at {pairs}. Every foreground/background pairing the "
                 f"system ships must be declared and computed — an undeclared pairing is an "
                 f"unverified pairing. If it lives outside the brand directory, pass "
                 f"--pairs PATH.")
    cmd_lexicon(argparse.Namespace(dir=d, strict=args.strict,
                                   show_suppressed=args.show_suppressed), rep)


def main() -> int:
    p = argparse.ArgumentParser(
        prog="brandcheck",
        description="Mechanical verification for a brand system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("contrast", help="compute every declared foreground/background pairing")
    c.add_argument("pairs", help="TSV: name<TAB>fg<TAB>bg<TAB>threshold "
                                 "(4.5 | 3.0 | normal | large | ui | aaa)")
    c.set_defaults(fn=cmd_contrast)

    t = sub.add_parser("tokens", help="CSS<->JSON agreement, theme parity, var() resolution")
    t.add_argument("dir")
    t.add_argument("--css")
    t.add_argument("--json")
    t.set_defaults(fn=cmd_tokens)

    f = sub.add_parser("fonts", help="glyph coverage, OpenType features, axes, licence")
    f.add_argument("font")
    f.add_argument("--glyphs", help=f"characters the system relies on (default {DEFAULT_GLYPHS})")
    f.add_argument("--licence", help="path to the licence file shipped alongside the font")
    f.set_defaults(fn=cmd_fonts)

    l = sub.add_parser("lexicon", help="banned marketing terms and unreferenced proof claims")
    l.add_argument("dir")
    l.add_argument("--strict", action="store_true",
                   help="treat proof-pattern hits as failures, not warnings")
    l.add_argument("--show-suppressed", action="store_true",
                   help="list matches suppressed as quotes/research/prohibitions")
    l.set_defaults(fn=cmd_lexicon)

    a = sub.add_parser("all", help="tokens + contrast + lexicon over a brand directory")
    a.add_argument("dir")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--show-suppressed", action="store_true")
    a.add_argument("--pairs", help="pairings file, if kept outside BRAND_DIR")
    a.set_defaults(fn=cmd_all)

    p.add_argument("--version", action="version",
                   version=f"brandcheck {__version__}")
    args = p.parse_args()
    rep = Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
