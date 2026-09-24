#!/usr/bin/env python3
"""brandcheck — mechanical verification for a brand system.

Everything a brand system claims that a machine can check, this checks. What it
cannot check (taste, differentiation, strategic fit) is left to the reviewer, by
design: see references/verification.md.

    brandcheck contrast  PAIRS.tsv            compute every declared pairing
    brandcheck tokens    DIR                  CSS <-> JSON agreement, themes, var() resolution
    brandcheck fonts     FONT.ttf [--glyphs …] glyph coverage, OT features, axes
    brandcheck lexicon   DIR                  banned words + fabricated-proof patterns
    brandcheck export    DIR                  generate tokens.json from tokens.css
    brandcheck render    PAGE.html            painted pairings, overflow, focus, motion
    brandcheck assets    DIR                  logo SVGs, icon set, avatar, share cards
    brandcheck all       DIR                  everything above that applies

Exit code is 0 only if every check passed. Non-zero means do not ship.

stdlib only, except `fonts`, which needs fontTools (pip install fonttools).
Python 3.9+.
"""
from __future__ import annotations

__version__ = "1.2.0"

import argparse
import json
import math
import os
import pathlib
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

RGBA = Tuple[float, float, float, float]   # channels 0-255, alpha 0-1

_HEX = set("0123456789abcdefABCDEF")
_NAMED = {"white": (255.0, 255.0, 255.0, 1.0), "black": (0.0, 0.0, 0.0, 1.0),
          "transparent": (0.0, 0.0, 0.0, 0.0)}
_COLOUR_FN = re.compile(r"^(rgba?|hsla?|oklch)\(\s*(.*?)\s*\)$", re.I | re.S)


def _pct_or_num(tok: str, scale: float) -> float:
    """'50%' -> 0.5 * scale; '0.5' -> 0.5 (already in the target unit)."""
    tok = tok.strip().lower()
    if tok == "none":
        return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100.0 * scale
    return float(tok)


def _hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
    # CSS Color 4, sec. 7.1: s and l in 0-1, h in degrees.
    def f(n: float) -> float:
        k = (n + h / 30.0) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1.0, min(k - 3, 9 - k, 1.0))
    return f(0) * 255.0, f(8) * 255.0, f(4) * 255.0


def _oklch_to_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    # Ottosson's OKLab -> linear sRGB matrices, then the sRGB transfer curve.
    # Out-of-gamut values are clamped, which is what a browser displays.
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    enc = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in lin]
    r, g, b2 = (max(0.0, min(1.0, v)) * 255.0 for v in enc)
    return r, g, b2


def parse_colour(value: str) -> RGBA:
    """Parse a CSS colour: hex (3/4/6/8 digits), rgb[a](), hsl[a](), oklch(),
    white, black or transparent. Alpha is KEPT: a translucent colour is not the
    colour its hex digits name, and scoring it as opaque is a false pass."""
    v = value.strip()
    if v.lower() in _NAMED:
        return _NAMED[v.lower()]
    if v.startswith("#"):
        h = v[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) not in (6, 8) or any(ch not in _HEX for ch in h):
            raise ValueError(f"not a colour: {value!r}")
        r, g, b = (float(int(h[i:i + 2], 16)) for i in (0, 2, 4))
        return r, g, b, (int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0)
    m = _COLOUR_FN.match(v)
    if not m:
        raise ValueError(f"not a colour: {value!r} (supported: hex, rgb(), hsl(), "
                         f"oklch(), white, black, transparent)")
    fn, body = m.group(1).lower(), m.group(2)
    alpha_tok = None
    if "/" in body:
        body, alpha_tok = body.split("/", 1)
    parts = [p for p in re.split(r"[\s,]+", body.strip()) if p]
    if alpha_tok is None and len(parts) == 4:
        parts, alpha_tok = parts[:3], parts[3]
    if len(parts) != 3:
        raise ValueError(f"not a colour: {value!r}")
    try:
        alpha = _pct_or_num(alpha_tok, 1.0) if alpha_tok is not None else 1.0
        if fn.startswith("rgb"):
            r, g, b = (_pct_or_num(p, 255.0) for p in parts)
        elif fn.startswith("hsl"):
            hue = float(parts[0].lower().replace("deg", ""))
            r, g, b = _hsl_to_rgb(hue, _pct_or_num(parts[1], 1.0),
                                  _pct_or_num(parts[2], 1.0))
        else:
            r, g, b = _oklch_to_rgb(_pct_or_num(parts[0], 1.0),
                                    _pct_or_num(parts[1], 0.4),
                                    float(parts[2].lower().replace("deg", "")))
    except ValueError:
        raise ValueError(f"not a colour: {value!r}") from None
    return float(r), float(g), float(b), max(0.0, min(1.0, float(alpha)))


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    """Source-over compositing in sRGB space, as browsers render it."""
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a),
            fg[2] * a + bg[2] * (1 - a), 1.0)


def to_hex(c: RGBA) -> str:
    return "#" + "".join(f"{int(round(max(0.0, min(255.0, x)))):02x}" for x in c[:3])


def _srgb(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(value) -> float:
    r, g, b, _ = parse_colour(value) if isinstance(value, str) else value
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def resolve_pair(fg: str, bg: str) -> Tuple[RGBA, RGBA]:
    """Parse a pairing and composite a translucent foreground over its ground.

    A translucent GROUND is refused: whatever shows through it is unknown here,
    so any ratio would be invented. Declare the composited ground instead.
    """
    f, b = parse_colour(fg), parse_colour(bg)
    if b[3] < 1.0:
        raise ValueError(f"background {bg!r} is translucent; a contrast ratio needs the "
                         f"opaque ground it sits on. Declare the composited colour.")
    return composite(f, b), b


def contrast_of(f: RGBA, b: RGBA) -> float:
    l1, l2 = luminance(f), luminance(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def ratio(fg: str, bg: str) -> float:
    return contrast_of(*resolve_pair(fg, bg))


def fmt_ratio(r: float) -> str:
    """Truncate, never round up.

    A pairing reported as 4.50:1 that is actually 4.4951:1 does not meet the
    requirement. Rounding up a contrast ratio is how inaccessible palettes get
    signed off.
    """
    return f"{int(r * 100) / 100:.2f}"


# Thresholds, from WCAG 2.2. `large` is >=24px, or >=18.66px when bold.
THRESHOLDS = {"normal": 4.5, "large": 3.0, "ui": 3.0, "aaa": 7.0, "aaa-large": 4.5}


THEMES = ("light", "dark")


def _is_ref(v: str) -> bool:
    return v.startswith("--") or v.lower().startswith("var(")


class _Palette:
    """Resolves pairs.tsv cells against tokens.css, one theme at a time.

    Iron Law 4 applies to pairings too: a row holding a hex copied out of the
    token file verifies the copy, and keeps passing after the token changes.
    A row that NAMES tokens is resolved fresh on every run.
    """

    def __init__(self, path: Optional[str]):
        self.path = path
        self.tok = parse_token_css(open(path, encoding="utf-8").read()) if path else None
        self.shipped: List[RGBA] = []
        if self.tok:
            for theme in THEMES:
                table = self.tok.theme(theme)
                for name in table:
                    try:
                        self.shipped.append(parse_colour(resolve_var(table[name], table)))
                    except ValueError:
                        pass

    def resolve(self, cell: str, theme: str) -> str:
        if not _is_ref(cell):
            return cell
        if not self.tok:
            raise ValueError(f"{cell} names a token, but there is no tokens.css to resolve "
                             f"it against (pass --tokens PATH)")
        expr = f"var({cell})" if cell.startswith("--") else cell
        value = resolve_var(expr, self.tok.theme(theme))
        if "var(" in value:
            raise ValueError(f"unknown token {cell} in the {theme} theme")
        return value

    def ships(self, literal: str) -> bool:
        c = parse_colour(literal)
        return any(all(abs(x - y) <= 0.5 for x, y in zip(c[:3], t[:3]))
                   and abs(c[3] - t[3]) <= 0.005 for t in self.shipped)


def _describe(cell: str, value: str) -> str:
    return f"{cell} ({value})" if _is_ref(cell) else cell


class PairRow:
    __slots__ = ("label", "theme", "fg", "bg", "fv", "bv", "f", "b", "thr")

    def __init__(self, label, theme, fg, bg, fv, bv, f, b, thr):
        self.label, self.theme, self.fg, self.bg = label, theme, fg, bg
        self.fv, self.bv, self.f, self.b, self.thr = fv, bv, f, b, thr


def read_pairs(pairs_path: str, palette: "_Palette",
               rep: Optional[Report] = None) -> List[PairRow]:
    """Every declared pairing, resolved and composited, one row per theme.

    A literal row (no token names) applies to both themes and has theme "".
    Problems are reported to `rep` when given, and the row is skipped.
    """
    def fail(msg):
        if rep:
            rep.fail(msg)
    rows: List[PairRow] = []
    for lineno, raw in enumerate(open(pairs_path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            fail(f"line {lineno}: expected 4 or 5 tab-separated fields "
                 f"(name, fg, bg, threshold[, theme]), got {len(parts)}")
            continue
        name, fg, bg, thr_raw = (p.strip() for p in parts[:4])
        theme_raw = parts[4].strip().lower() if len(parts) > 4 and parts[4].strip() else ""
        thr = THRESHOLDS.get(thr_raw.lower(), None)
        if thr is None:
            try:
                thr = float(thr_raw)
            except ValueError:
                fail(f"line {lineno}: threshold {thr_raw!r} is not a number "
                     f"or one of {', '.join(THRESHOLDS)}")
                continue
        if theme_raw and theme_raw not in ("light", "dark", "both"):
            fail(f"line {lineno}: theme {theme_raw!r} is not light, dark or both")
            continue
        uses_tokens = _is_ref(fg) or _is_ref(bg)
        if uses_tokens:
            themes = THEMES if theme_raw in ("", "both") else (theme_raw,)
        else:
            themes = (theme_raw,) if theme_raw in THEMES else ("",)
        for theme in themes:
            label = f"{name} ({theme})" if theme else name
            try:
                fv, bv = palette.resolve(fg, theme or "light"), palette.resolve(bg, theme or "light")
                for cell, value in ((fg, fv), (bg, bv)):
                    if not _is_ref(cell) and palette.tok and not palette.ships(value):
                        raise ValueError(
                            f"{cell} matches no token in {os.path.basename(palette.path)}, so "
                            f"this row verifies a colour the system does not ship (a stale "
                            f"copy?). Name the token instead.")
                f, b = resolve_pair(fv, bv)
            except ValueError as exc:
                fail(f"line {lineno}: {label}: {exc}")
                continue
            rows.append(PairRow(label, theme, fg, bg, fv, bv, f, b, thr))
    return rows


def _tokens_for(pairs_path: str, explicit: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """(tokens path or None, error or None): explicit wins, else beside the pairs."""
    if explicit:
        return (explicit, None) if os.path.exists(explicit) else \
            (None, f"tokens file not found: {explicit}")
    beside = os.path.join(os.path.dirname(pairs_path) or ".", "tokens.css")
    return (beside if os.path.exists(beside) else None), None


def cmd_contrast(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"CONTRAST · {args.pairs}")
    if not os.path.exists(args.pairs):
        rep.fail(f"pairs file not found: {args.pairs}")
        return
    tokens, err = _tokens_for(args.pairs, getattr(args, "tokens", None))
    if err:
        rep.fail(err)
        return
    palette = _Palette(tokens)
    seen = set()
    rows = []
    for row in read_pairs(args.pairs, palette, rep):
        note = f" composited {to_hex(row.f)}" if parse_colour(row.fv)[3] < 1.0 else ""
        key = (to_hex(row.f), to_hex(row.b), row.thr)
        rows.append((row.label, _describe(row.fg, row.fv), _describe(row.bg, row.bv),
                     contrast_of(row.f, row.b), row.thr, key in seen, note))
        seen.add(key)

    if not rows:
        if not rep.failures:
            rep.fail("no pairings found — an empty contrast file is not a passing contrast file")
        return

    width = max(len(r[0]) for r in rows)
    failures = 0
    for name, fg, bg, r, thr, dup, note in rows:
        mark = _c("PASS", GRN) if r >= thr else _c("FAIL", RED)
        dupe = _c("  (duplicate pair)", DIM) if dup else ""
        print(f"  {mark}  {name:<{width}}  {fg} on {bg}{note}  "
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


_AT_BLOCK = r"@(?:media|supports|container)\b"
_DARK_QUERY = re.compile(r"prefers-color-scheme\s*:\s*dark", re.I)
_DARK_ATTR = r'\[data-theme=["\']dark["\']\]\s*\{'


class TokenCSS:
    """A token file split by where each declaration applies.

    base        declarations outside every at-rule and theme block
    dark_media  the prefers-color-scheme: dark block
    dark_attr   the [data-theme="dark"] block
    media       every other @media/@supports/@container block, with its query

    Everything conditional is kept OUT of base. Only min-width blocks used to
    be excluded, so a desktop-first file's max-width override silently
    replaced the base value and reported a false mismatch.
    """

    def __init__(self, base, dark_media, dark_attr, media):
        self.base: Dict[str, str] = base
        self.dark_media: Dict[str, str] = dark_media
        self.dark_attr: Dict[str, str] = dark_attr
        self.media: List[Tuple[str, Dict[str, str]]] = media

    @property
    def dark(self) -> Dict[str, str]:
        return self.dark_media or self.dark_attr

    def theme(self, name: str) -> Dict[str, str]:
        """Every token as declared in one theme, before var() resolution."""
        return dict(self.base) if name == "light" else {**self.base, **self.dark}

    def defined(self) -> set:
        names = set(self.base) | set(self.dark_media) | set(self.dark_attr)
        for _, v in self.media:
            names |= set(v)
        return names


def parse_token_css(css: str) -> TokenCSS:
    clean = _strip_comments(css)
    spans: List[Tuple[int, int]] = []
    dark_media: Dict[str, str] = {}
    media: List[Tuple[str, Dict[str, str]]] = []
    pos = 0
    while True:
        m = re.search(_AT_BLOCK, clean[pos:])
        if not m:
            break
        start = pos + m.start()
        query = clean[start:clean.index("{", start)].strip()
        body, end = _balanced_block(clean, start)
        found = _vars_in(body)
        if _DARK_QUERY.search(query):
            dark_media.update(found)
        elif found:
            media.append((" ".join(query.split()), found))
        spans.append((start, end))
        pos = end
    dark_attr, s2 = _scoped(clean, _DARK_ATTR)
    base_src = clean
    for a, b in sorted(spans + s2, reverse=True):
        base_src = base_src[:a] + base_src[b:]
    return TokenCSS(_vars_in(base_src), dark_media, dark_attr, media)


def resolve_var(value: str, table: Dict[str, str], depth: int = 0) -> str:
    """Resolve var(--x[, fallback]) against one theme's declarations."""
    if depth > 12:
        return value

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in table:
            return resolve_var(table[name], table, depth + 1)
        return resolve_var(fallback.strip(), table, depth + 1) if fallback else m.group(0)
    return re.sub(r"var\(\s*(--[a-zA-Z][\w-]*)\s*(?:,\s*([^()]*))?\)", sub, value)


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
            # The hex fallback is 6 digits by spec; carry alpha alongside it.
            a = raw.get("alpha", 1)
            return str(raw["hex"]) + (f"{int(round(float(a) * 255)):02x}" if a < 1 else "")
        if "colorSpace" in raw and "components" in raw:
            comps = " ".join(str(c) for c in raw["components"])
            alpha = f" / {raw['alpha']}" if "alpha" in raw else ""
            return f"{raw['colorSpace']}({comps}{alpha})"
        if "value" in raw and "unit" in raw:
            return f"{raw['value']}{raw['unit']}"
        return json.dumps(raw, sort_keys=True, separators=(",", ":"))
    if isinstance(raw, list):
        if len(raw) == 4 and all(isinstance(x, (int, float)) for x in raw):
            return "cubic-bezier(" + ", ".join(str(x) for x in raw) + ")"
        if all(isinstance(x, str) for x in raw):          # fontFamily
            return ", ".join(f'"{x}"' if " " in x else x for x in raw)
        return json.dumps(raw, separators=(",", ":"))
    return str(raw)


_NUM_UNIT = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))([a-z%]*)$", re.I)


def same_value(a: str, b: str) -> bool:
    """Do a CSS value and a rendered JSON value mean the same thing?

    Compared as values, not strings: .5rem is 0.5rem, #f0efe999 is
    rgb(240 239 233 / 0.6), and a font stack's quoting is not a difference.
    """
    a, b = " ".join(a.split()), " ".join(b.split())
    if a.lower() == b.lower():
        return True
    try:
        ca, cb = parse_colour(a), parse_colour(b)
        return all(abs(x - y) <= 0.5 for x, y in zip(ca[:3], cb[:3])) \
            and abs(ca[3] - cb[3]) <= 0.005
    except ValueError:
        pass
    ma, mb = _NUM_UNIT.match(a), _NUM_UNIT.match(b)
    if ma and mb:
        return abs(float(ma.group(1)) - float(mb.group(1))) < 1e-9 and \
            ma.group(2).lower() == mb.group(2).lower()
    if a.lower().startswith("cubic-bezier(") and b.lower().startswith("cubic-bezier("):
        na = [float(x) for x in re.findall(r"-?(?:\d+\.?\d*|\.\d+)", a)]
        nb = [float(x) for x in re.findall(r"-?(?:\d+\.?\d*|\.\d+)", b)]
        return len(na) == len(nb) and all(abs(x - y) < 1e-9 for x, y in zip(na, nb))

    def norm(v):
        return re.sub(r"\s*,\s*", ",", v.replace('"', "").replace("'", "")).lower()
    return norm(a) == norm(b)


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
        if not isinstance(val, dict) or (key.startswith("$") and key != "$root"):
            continue
        has_value = "$value" in val or "value" in val
        if has_value:
            rendered = _render_value(val.get("$value", val.get("value")))
            if key.startswith("--"):
                flat[key] = rendered
            else:
                # A $root token is its group's own value: a.b.$root is --a-b.
                dtcg[".".join(path if key == "$root" else path + [key])] = rendered
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
                path = m.group(1).replace(".$root", "")
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
    return "--" + path.replace(".$root", "").replace(".", "-")


EXTERNAL_REF = re.compile(
    r"""<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*?"""
    r"""\b(?:src|href|data)\s*=\s*["'](?!#|data:)([^"']+)["']""", re.I | re.S)
FONT_HOST = re.compile(r"fonts\.(?:googleapis|gstatic|bunny)\.(?:com|net)", re.I)


def _css_urls(css: str) -> List[Tuple[int, str]]:
    """Every url(...) in a stylesheet, with its offset.

    A quoted value runs to its matching quote, so a data: URI that itself
    contains url(#id) (an SVG filter reference inside an embedded image) is
    read as one value, not two.
    """
    out, pos = [], 0
    while True:
        i = css.find("url(", pos)
        if i < 0:
            return out
        j = i + 4
        while j < len(css) and css[j] in " \t\n":
            j += 1
        if j < len(css) and css[j] in "\"'":
            q = css[j]
            k = css.find(q, j + 1)
            k = len(css) if k < 0 else k
            out.append((i, css[j + 1:k]))
            pos = k + 1
        else:
            k = css.find(")", j)
            k = len(css) if k < 0 else k
            out.append((i, css[j:k].strip()))
            pos = k + 1


def _classify(url: str) -> str:
    u = url.strip()
    if u.startswith(("data:", "#", "%23", "mailto:", "tel:")) or not u:
        return "embedded"
    if u.startswith(("http://", "https://", "//")):
        return "font-cdn" if FONT_HOST.search(u) else "remote"
    return "local"


def _check_self_contained(name, text, rep):
    """The artifact must open from disk with no build step and no fetches.

    A style tile that silently depends on a CDN looks fine on the machine that
    made it and breaks on the client's laptop, in a locked-down enterprise
    network, or in an air-gapped review. The one tolerated fetch is a webfont
    CSS @import, and only when every face is ALSO embedded in an @font-face
    block, because then the import is genuinely optional.

    An @font-face whose src is a URL is not self-hosted, whichever host it
    names: fonts.gstatic.com is a CDN, and fonts/brand.woff2 is a second file
    the artifact cannot open without. Embedded means a data: URI.
    """
    external, fonts = [], []
    for m in EXTERNAL_REF.finditer(text):
        url = m.group(1).strip()
        kind = _classify(url)
        if kind == "font-cdn":
            fonts.append(url)
        elif kind in ("remote", "local"):
            external.append(url)          # a local file is still a dependency
    styles = "".join(re.findall(r"<style[^>]*>(.*?)</style>", text, flags=re.S | re.I))
    for u in re.findall(r"@import\s+(?:url\(\s*)?['\"]?([^'\")\s;]+)", styles):
        (fonts if _classify(u) == "font-cdn" else external).append(u)

    embedded_faces = 0
    face_iter = list(re.finditer(r"@font-face\s*\{", styles, re.I))
    face_spans = []
    for fm in face_iter:
        body, end = _balanced_block(styles, fm.start())
        face_spans.append((fm.start(), end))
        srcs = [u for _, u in _css_urls(body)]
        kinds = {_classify(u) for u in srcs}
        if srcs and kinds == {"embedded"}:
            embedded_faces += 1
        else:
            external += [u for u in srcs if _classify(u) != "embedded"]
    for off, u in _css_urls(styles):
        if any(a <= off < b for a, b in face_spans) or \
                styles[max(0, off - 12):off].rstrip().endswith("@import"):
            continue
        if _classify(u) != "embedded":
            external.append(u)

    if external:
        rep.fail(f"{name}: not self-contained — {len(external)} external or local "
                 f"dependency(ies): {sorted(set(external))[:4]}. The artifact must open "
                 f"from disk with no build step and no fetches; embed fonts as data: URIs.")
    if fonts and embedded_faces == 0:
        rep.fail(f"{name}: depends on a webfont CDN for its typography — "
                 f"{len(fonts)} remote import and zero embedded @font-face blocks. Embed the "
                 f"faces so the import is genuinely optional; the system is required to "
                 f"work without it.")
    elif not external:
        detail = (f"; {len(fonts)} webfont import backed by {embedded_faces} embedded "
                  f"@font-face block(s)" if fonts else "")
        rep.ok(f"{name}: self-contained (no external dependencies{detail})")
    if re.search(r"<img\b", text, re.I):
        rep.warn(f"{name}: contains <img>. Version one should require no image assets — "
                 f"they are the first thing to rot and the first thing a licence dispute touches.")


# ───────────────────────────────────────────────────────────── export ──
# Iron Law 4: tokens live in exactly one authored format and every other
# format is GENERATED. tokens.css is authored; this writes tokens.json in DTCG
# 2025.10 (https://www.designtokens.org/TR/2025.10/format/). The `tokens`
# check regenerates the export and compares, so a hand edit is caught.

NS = "org.evidence-based-brand-systems"
_ALIAS = re.compile(r"^var\(\s*(--[a-zA-Z][\w-]*)\s*\)$")
_NUMBER = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")
_DIMENSION = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))(px|rem)$")
_DURATION = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))(ms|s)$")
_BEZIER = re.compile(r"^cubic-bezier\(\s*([^)]*)\)$", re.I)
_FAMILY_PART = re.compile(r"""^(?:"[^"]+"|'[^']+'|[A-Za-z][\w -]*)$""")


def _num(text: str):
    f = float(text)
    return int(f) if f.is_integer() else f


def _colour_value(raw: str) -> Optional[dict]:
    try:
        r, g, b, a = parse_colour(raw)
    except ValueError:
        return None
    m = _COLOUR_FN.match(raw.strip())
    if m and m.group(1).lower() == "oklch":
        body = m.group(2).split("/")[0]
        L, C, H = [p for p in re.split(r"[\s,]+", body.strip()) if p][:3]
        comps = [_num(str(_pct_or_num(L, 1.0))), _num(str(_pct_or_num(C, 0.4))),
                 _num(H.lower().replace("deg", ""))]
        value = {"colorSpace": "oklch", "components": comps}
    else:
        value = {"colorSpace": "srgb",
                 "components": [round(c / 255.0, 6) for c in (r, g, b)]}
    if a < 1.0:
        value["alpha"] = round(a, 4)
    value["hex"] = to_hex((r, g, b, 1.0))
    return value


def _dtcg_token(name: str, raw: str, paths: Dict[str, List[str]]) -> Optional[dict]:
    """One CSS declaration as a DTCG token, or None when no DTCG type fits."""
    v = raw.strip()
    m = _ALIAS.match(v)
    if m:
        target = paths.get(m.group(1))
        return {"$value": "{" + ".".join(target) + "}"} if target else None
    colour = _colour_value(v)
    if colour is not None:
        return {"$type": "color", "$value": colour}
    m = _DIMENSION.match(v)
    if m:
        return {"$type": "dimension", "$value": {"value": _num(m.group(1)), "unit": m.group(2)}}
    m = _DURATION.match(v)
    if m:
        return {"$type": "duration", "$value": {"value": _num(m.group(1)), "unit": m.group(2)}}
    m = _BEZIER.match(v)
    if m:
        pts = [p.strip() for p in m.group(1).split(",")]
        if len(pts) == 4 and all(_NUMBER.match(p) for p in pts):
            return {"$type": "cubicBezier", "$value": [_num(p) for p in pts]}
        return None
    if _NUMBER.match(v):
        n = _num(v)
        if "weight" in name and 1 <= n <= 1000:
            return {"$type": "fontWeight", "$value": n}
        return {"$type": "number", "$value": n}
    parts = [p.strip() for p in v.split(",")]
    if (len(parts) > 1 or v[:1] in "\"'") and all(_FAMILY_PART.match(p) for p in parts):
        return {"$type": "fontFamily", "$value": [p.strip("\"'") for p in parts]}
    return None


def _token_digest(tok: TokenCSS) -> str:
    import hashlib
    canon = json.dumps({"base": tok.base, "dark_media": tok.dark_media,
                        "dark_attr": tok.dark_attr, "media": tok.media},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def export_tokens(css: str, source: str) -> Tuple[dict, List[str]]:
    """Return (DTCG document, names that have no DTCG type)."""
    tok = parse_token_css(css)
    raw_paths = {n: n[2:].split("-") for n in tok.base}
    groups = {tuple(p[:i]) for p in raw_paths.values() for i in range(1, len(p))}
    # A token whose path is also a group is that group's $root token.
    paths = {n: p + (["$root"] if tuple(p) in groups else []) for n, p in raw_paths.items()}

    doc: dict = {"$description": (
        f"Generated by `brandcheck export` from {source}. Do not edit: edit {source} "
        f"and re-run. Naming contract: JSON path a.b.c is CSS custom property --a-b-c; "
        f"a.b.$root is --a-b.")}
    css_only: Dict[str, str] = {}
    for name, raw in tok.base.items():
        token = _dtcg_token(name, raw, paths)
        if token is None:
            css_only[name] = raw
            continue
        node = doc
        for seg in paths[name][:-1]:
            node = node.setdefault(seg, {})
        node[paths[name][-1]] = token
    doc["$extensions"] = {NS: {
        "generator": f"brandcheck {__version__}",
        "source": source,
        "sourceDigest": _token_digest(tok),
        "cssOnly": css_only,
        "themes": {"dark": dict(tok.dark)},
        "media": {q: v for q, v in tok.media},
    }}
    return doc, list(css_only)


def _dump(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def cmd_export(args: argparse.Namespace, rep: Report) -> None:
    css_path = os.path.join(args.src, "tokens.css") if os.path.isdir(args.src) else args.src
    out_path = args.output or os.path.join(os.path.dirname(css_path) or ".", "tokens.json")
    rep.section(f"EXPORT · {os.path.relpath(css_path)} -> {os.path.relpath(out_path)}")
    if not os.path.exists(css_path):
        rep.fail(f"missing {css_path}")
        return
    doc, css_only = export_tokens(open(css_path, encoding="utf-8").read(),
                                  os.path.basename(css_path))
    count = len(parse_token_css(open(css_path, encoding="utf-8").read()).base)
    if not count:
        rep.fail("no custom properties found in the CSS — is this a token file?")
        return
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(_dump(doc))
    rep.ok(f"wrote {count - len(css_only)} DTCG 2025.10 token(s) to {os.path.relpath(out_path)}")
    if css_only:
        rep.note(f"{len(css_only)} token(s) have no DTCG type and travel as CSS in "
                 f"$extensions.{NS}.cssOnly: {css_only[:6]}")


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
    tok = parse_token_css(css)
    base, dark_media, dark_attr = tok.base, tok.dark_media, tok.dark_attr
    strict_gen = getattr(args, "require_generated", False)

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
        ext = (data.get("$extensions") or {}).get(NS, {}) if isinstance(data, dict) else {}
        if ext.get("generator"):
            _check_generated(data, css, os.path.basename(css_path), args.dir, rep)
        else:
            _check_agreement(data, base, rep)
            (rep.fail if strict_gen else rep.warn)(
                "tokens.json was not produced by `brandcheck export`, so it is a second "
                "authored format (Iron Law 4). Generate it: "
                "python3 scripts/brandcheck.py export BRAND_DIR")
    else:
        (rep.fail if strict_gen else rep.warn)(
            f"no {os.path.basename(json_path)} found — shipping only one token format "
            f"means downstream tools cannot consume the system. Generate it: "
            f"python3 scripts/brandcheck.py export BRAND_DIR")

    _check_markup(args.dir, css_path, css, tok, rep)


def _check_generated(data: dict, css: str, source: str, d: str, rep: Report) -> None:
    expected, _ = export_tokens(css, source)

    def strip(doc):
        doc = json.loads(json.dumps(doc))
        doc.get("$extensions", {}).get(NS, {}).pop("generator", None)
        return doc
    if strip(expected) == strip(data):
        rep.ok("tokens.json is the current export of tokens.css (generated, not hand-edited)")
        return
    if data["$extensions"][NS].get("sourceDigest") != expected["$extensions"][NS]["sourceDigest"]:
        rep.fail("tokens.json is stale: tokens.css changed after the last export. "
                 f"Regenerate: python3 scripts/brandcheck.py export {d}")
    else:
        rep.fail("tokens.json differs from the export of an unchanged tokens.css, so it was "
                 "edited by hand. Edit tokens.css and regenerate: "
                 f"python3 scripts/brandcheck.py export {d}")


def _check_agreement(data: dict, base: Dict[str, str], rep: Report) -> None:
    flat, dtcg = {}, {}
    _walk_tokens(data.get("tokens", data), [], flat, dtcg)
    jtok = dict(flat)
    ext = (data.get("$extensions") or {}).get(NS, {})
    jtok.update(ext.get("cssOnly", {}))
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

            _same = same_value

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


def _root_tokens(css: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """(base, dark) custom properties declared on :root in a page's styles.

    Only :root blocks count: a component that sets a variable locally is not a
    pasted token block.
    """
    clean = _strip_comments(css)
    media, pos = [], 0
    while True:
        m = re.search(_AT_BLOCK, clean[pos:])
        if not m:
            break
        start = pos + m.start()
        _, end = _balanced_block(clean, start)
        media.append((start, end, bool(_DARK_QUERY.search(clean[start:clean.index("{", start)]))))
        pos = end
    base: Dict[str, str] = {}
    dark: Dict[str, str] = {}
    for m in re.finditer(r"(?::root\b|\[data-theme)[^{};]*\{", clean):
        body, _ = _balanced_block(clean, m.start())
        found = _vars_in(body)
        inside = next((mm for mm in media if mm[0] < m.start() < mm[1]), None)
        if re.search(r"data-theme=[\"']?dark", m.group(0)) or (inside and inside[2]):
            dark.update(found)
        elif not inside:
            base.update(found)
    return base, dark


def _check_pasted_tokens(name: str, text: str, tok: TokenCSS, rep: Report) -> None:
    """A page that pastes the token block must paste what tokens.css says.

    The style tile and the share card carry their own copy of the tokens so
    they open with no build step. A copy that drifts renders a palette the
    system does not ship. A base value may match either theme (a dark share
    card pastes the dark values at :root); a dark-block value must match dark.
    """
    styles = "".join(re.findall(r"<style[^>]*>(.*?)</style>", text, flags=re.S | re.I))
    base, dark = _root_tokens(styles)
    light_t, dark_t = tok.theme("light"), tok.theme("dark")
    page_light, page_dark = dict(base), {**base, **dark}
    drift = []
    for k in base:
        if k not in light_t:
            continue
        mine = resolve_var(page_light[k], page_light)
        if not any(same_value(mine, resolve_var(t[k], t)) for t in (light_t, dark_t)):
            drift.append(f"{k}: page={mine!r} tokens.css={resolve_var(light_t[k], light_t)!r}")
    for k in dark:
        if k not in dark_t:
            continue
        mine = resolve_var(page_dark[k], page_dark)
        theirs = resolve_var(dark_t[k], dark_t)
        if not same_value(mine, theirs):
            drift.append(f"{k} (dark): page={mine!r} tokens.css={theirs!r}")
    if drift:
        rep.fail(f"{name}: its pasted token block has drifted from tokens.css on "
                 f"{len(drift)} token(s), e.g. " + "; ".join(drift[:3]) +
                 ". Paste the current tokens.css.")
    elif set(base) & set(light_t):
        rep.ok(f"{name}: its pasted tokens agree with tokens.css "
               f"({len(set(base) & set(light_t))} checked)")


def _check_markup(d: str, css_path: str, css: str, tok: TokenCSS, rep: Report) -> None:
    # 3. var() references resolve, across CSS and any HTML in the directory.
    defined = tok.defined()
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
        # Inline style="" and SVG paint attributes bypass the token layer just
        # as surely as a stylesheet rule does. In SVG, colour with a CSS class.
        markup = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
        inline = " ".join(a or b for a, b in re.findall(
            r"""\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", markup, flags=re.I))
        paint = " ".join(a or b for a, b in re.findall(
            r"""\s(?:fill|stroke|stop-color|color|flood-color)\s*=\s*(?:"([^"]*)"|'([^']*)')""",
            markup, flags=re.I))
        without_decls = CSS_VAR.sub("", styles) + " " + inline + " " + paint
        raws = [r for r in RAW_COLOUR.findall(without_decls)
                if r.lower() not in ("#fff", "#ffffff", "#000", "#000000")]
        if raws:
            rep.fail(f"{name}: {len(raws)} raw colour value(s) outside token declarations "
                     f"({sorted(set(raws))[:5]}) — component CSS must reference tokens")
        else:
            rep.ok(f"{name}: no raw colour outside token declarations")
        _check_self_contained(name, text, rep)
        _check_pasted_tokens(name, text, tok, rep)


# ────────────────────────────────────────────────────────────── fonts ──

DEFAULT_GLYPHS = "=≠?→✓·—–…"


# A reserved name is declared in a COPYRIGHT line: `... with Reserved Font Name
# "Plex"`. Every OFL licence also DEFINES the term in its body ('"Reserved Font
# Name" refers to any names specified as such after the copyright
# statement(s)'), so matching the bare phrase reports a reserved name for
# fonts that have none. Only the text before the licence body is searched, and
# only in the "with Reserved Font Name" form.
_LICENCE_BODY = re.compile(r"This Font Software is licensed under|^\s*PREAMBLE\s*$", re.M | re.I)
_RFN_CLAUSE = re.compile(r"with\s+Reserved\s+Font\s+Names?\s+(.+)", re.I)
_QUOTED_NAME = re.compile(r"[\"\u201c'\u2018]([^\"\u201d'\u2019\n]+)[\"\u201d'\u2019]")


def reserved_font_names(licence_text: str) -> List[str]:
    body = _LICENCE_BODY.search(licence_text)
    head = licence_text[:body.start()] if body else licence_text
    names: List[str] = []
    for line in head.splitlines():
        m = _RFN_CLAUSE.search(line)
        if m:
            names += [n.strip() for n in _QUOTED_NAME.findall(m.group(1)) if n.strip()]
    return list(dict.fromkeys(names))


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

    try:
        f = TTFont(args.font, fontNumber=0, lazy=True)
        cmap = f.getBestCmap()
    except Exception as exc:                     # noqa: BLE001 - report, never crash
        rep.fail(f"cannot read {args.font}: {exc} (WOFF2 needs brotli: "
                 f"pip install 'fonttools[woff]')")
        return
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
            names = reserved_font_names(text)
            if names:
                shown = ", ".join(f'"{n}"' for n in names)
                rep.warn(f'declares Reserved Font Name {shown} — subset freely, '
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
_COUNT_NOUNS = (r"(?:customers|clients|companies|teams|users|brands|banks|institutions|"
                r"fintechs|organi[sz]ations|enterprises|businesses|merchants|partners|"
                r"lenders|insurers|agencies|developers|members|countries|downloads|installs)")
_OUTCOMES = (r"(?:accura(?:cy|te)|precision|recall|detection|uptime|availability|"
             r"reduction|faster|fewer|less|lower|fraud|losses|savings|false[- ]positives?|"
             r"conversion|roi)")
PROOF_PATTERNS = [
    (r"\btrusted by\b", "'trusted by' claim"),
    (r"\bSOC\s?2\b", "SOC 2 reference"),
    (r"\bISO\s?27001\b", "ISO 27001 reference"),
    (r"\b(?:[A-Z][A-Z0-9-]*\s+|fully\s+)compliant\b|\bcompliant with\b", "compliance claim"),
    (r"(?:\b\d[\d,.]*\s*[kKmM]?\+|\b(?:over|more than|upwards of)\s+\d[\d,.]*\s*[kKmM]?|"
     r"\b(?:hundreds|thousands|millions) of)\s*" + _COUNT_NOUNS + r"\b", "customer-count claim"),
    (r"\b\d+(?:\.\d+)?\s?%\s+(?:\w+\s+){0,2}?" + _OUTCOMES + r"\b|\b" + _OUTCOMES +
     r"(?:\s+\w+){0,4}?\s+(?:by|of|to|at)\s+(?:up to\s+)?\d+(?:\.\d+)?\s?%|"
     r"\b\d+(?:\.\d+)?x\s+(?:faster|more|fewer|less|cheaper|better)\b",
     "performance-metric claim"),
    (r"\b(?:approved|certified|accredited|endorsed|licensed|audited|backed)\s+by\b|"
     r"\b[\w]+-(?:approved|certified|accredited|endorsed)\b", "third-party endorsement claim"),
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

    `context` is the claim's own unit (see `_units`) plus any footnote it cites.
    A referent counts only when it is attached to the claim: the same
    paragraph, list item or table row, or a footnote the claim points at. A
    date two paragraphs away is not evidence for this sentence, and treating it
    as evidence let any dated document launder every claim near a date.
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


# Units: the smallest block a referent can belong to.
_MD_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s")
_MD_SINGLE = re.compile(r"^\s{0,3}(?:\||#{1,6}\s|\[\^[^\]]+\]:)")
_HTML_BLOCK = (r"(?:p|li|h[1-6]|tr|div|section|header|footer|blockquote|figcaption|dd|dt|"
               r"article|aside|main|nav|table|ul|ol|pre|figure)\b")
_HTML_OPEN = re.compile(r"<" + _HTML_BLOCK, re.I)
_HTML_CLOSE = re.compile(r"</" + _HTML_BLOCK + r"|<br\b|<hr\b", re.I)
_FOOTNOTE_DEF = re.compile(r"^\s{0,3}\[\^([^\]]+)\]:\s*(.*)$")
_FOOTNOTE_REF = re.compile(r"\[\^([^\]]+)\](?!:)")


def _units(lines: List[str], html: bool) -> List[int]:
    """Give each line a unit id; -1 for blank and fenced lines.

    Markdown: a paragraph (blank-line bounded), one list item with its
    continuation lines, one table row, one heading, one footnote definition.
    HTML: from an opening block tag to its closing tag, so a wrapped <p> is one
    unit and each <li> or <tr> is its own. Table cells share their row.
    """
    ids: List[int] = []
    uid, open_, in_fence = 0, False, False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            ids.append(-1)
            open_ = False
            continue
        if in_fence or not line.strip():
            ids.append(-1)
            open_ = False
            continue
        if html:
            starts, single = bool(_HTML_OPEN.search(line)), False
        else:
            single = bool(_MD_SINGLE.match(line))
            starts = single or bool(_MD_ITEM.match(line))
        if starts or not open_:
            uid += 1
        ids.append(uid)
        open_ = not single and not (html and _HTML_CLOSE.search(line))
    return ids


# Forbidden claims: stage 1 records what this company may not claim at its
# stage. forbidden-claims.txt turns that list into a gate. One claim per line,
# "#" comments, an optional TAB and the reason. A plain phrase matches however
# it is spaced or hyphenated; "re:" introduces a regular expression.
#
# Only quotation and research labels suppress a forbidden claim. Negation
# words and dates do not: "Bank-grade controls, audit pending" is still the
# claim. Wherever a guideline lists a forbidden phrase, it quotes it.
CLAIMS_FILE = "forbidden-claims.txt"
# Quotation clears a forbidden claim only when the line forbids it. Our
# "bank-grade" controls is still the claim, in quotation marks.
# Research labels that mark someone else's material. [Assumption] and the
# like are the brand's own voice, so they do not clear a forbidden claim.
EVIDENCE_LABEL = re.compile(
    r"\[(?:VERIFIED|OBSERVED|INTERPRETATION|VISUAL OBSERVATION)[^\]]*\]", re.I)
# A denial directly before the phrase: "is not yet regulator-approved" is the
# stage honesty the skill asks for, not the claim.
DENIAL = re.compile(r"\b(?:not(?:\s+yet)?|never(?:\s+been)?|no\s+longer|isn'?t|aren'?t|"
                    r"wasn'?t|weren'?t)\s+(?:[\w-]+\s+){0,2}$", re.I)
PROHIBITION = re.compile(
    r"\b(?:never|don'?t|do not|must not|may not|avoid|ban|banned|forbid|forbidden|"
    r"prohibit|prohibited|not permitted|no longer|stop saying|instead of|rather than)\b", re.I)
_SEP = r"[\s\-‐-―]*"


def load_claims(path: str) -> List[Tuple["re.Pattern[str]", str, str]]:
    claims = []
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        phrase, _, reason = line.partition("\t")
        phrase = phrase.strip()
        if phrase.startswith("re:"):
            rx = re.compile(phrase[3:], re.I)
            shown = phrase[3:]
        else:
            words = [re.escape(w) for w in re.split(r"[\s\-‐-―]+", phrase) if w]
            rx = re.compile(r"(?<!\w)" + _SEP.join(words) + r"(?!\w)", re.I)
            shown = phrase
        claims.append((rx, shown, reason.strip()))
    return claims


def _scan_text(path: str, text: str, rep: Report, strict: bool,
               show_all: bool, claims=()) -> Tuple[int, int, int, int]:
    words = proofs = suppressed = forbidden = 0
    all_lines = text.splitlines()
    ids = _units(all_lines, html=path.endswith((".html", ".htm")))
    unit_text: Dict[int, str] = {}
    for line, uid in zip(all_lines, ids):
        if uid >= 0:
            unit_text[uid] = unit_text.get(uid, "") + line + "\n"
    notes = {m.group(1): m.group(2) for m in map(_FOOTNOTE_DEF.match, all_lines) if m}

    checks = [(re.compile(rf"\b{re.escape(w)}\b", re.I), f"banned term '{w}'", True)
              for w in BANNED_WORDS]
    checks += [(re.compile(pat, re.I), label, False) for pat, label in PROOF_PATTERNS]
    for i, (line, uid) in enumerate(zip(all_lines, ids), 1):
        if uid < 0:
            continue
        unit = unit_text[uid]
        window = unit + "".join(notes.get(ref, "") + "\n"
                                for ref in _FOOTNOTE_REF.findall(unit))
        for rx, shown, reason in claims:
            for m in list(rx.finditer(line))[:1]:
                quoted = any(q.start() <= m.start() and m.end() <= q.end()
                             for q in QUOTED.finditer(line))
                why = ("quoted prohibition" if quoted and PROHIBITION.search(line) else
                       "labelled research" if EVIDENCE_LABEL.search(line) else
                       "denied, not claimed" if DENIAL.search(line[:m.start()]) else None)
                if why:
                    suppressed += 1
                    if show_all:
                        rep.note(f"{os.path.basename(path)}:{i} forbidden claim '{shown}' "
                                 f"suppressed ({why})")
                    continue
                forbidden += 1
                rep.fail(f"{os.path.basename(path)}:{i} forbidden claim '{shown}' — "
                         f"{line.strip()[:88]}" + (f"  [{reason}]" if reason else ""))
        for rx, label, is_word in checks:
            for m in list(rx.finditer(line))[:1]:      # one report per line and label
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
    return words, proofs, suppressed, forbidden


SCANNED = (".md", ".mdx", ".html", ".htm", ".txt", ".astro", ".tsx", ".jsx", ".vue",
           ".svelte", ".ts", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml")
SKIPPED_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".next", ".astro",
                ".vercel", ".svelte-kit", "coverage"}


def cmd_lexicon(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"LEXICON & PROOF · {args.dir}")
    claims_path = getattr(args, "claims", None)
    if not claims_path:
        beside = os.path.join(args.dir, CLAIMS_FILE)
        claims_path = beside if os.path.exists(beside) else None
    elif not os.path.exists(claims_path):
        rep.fail(f"claims file not found: {claims_path}")
        return
    claims = load_claims(claims_path) if claims_path else []

    targets = []
    for root, dirs, files in os.walk(args.dir):
        dirs[:] = [x for x in dirs if x not in SKIPPED_DIRS]
        for name in sorted(files):
            path = os.path.join(root, name)
            if name.endswith(SCANNED) and not (
                    claims_path and os.path.abspath(path) == os.path.abspath(claims_path)):
                targets.append(path)
    if not targets:
        rep.warn("no .md/.html (or page source) files found to scan")
        return

    tw = tp = ts = tf = 0
    for path in targets:
        w, p, sup, fb = _scan_text(path, open(path, encoding="utf-8", errors="replace").read(),
                                   rep, args.strict, args.show_suppressed, claims)
        tw += w; tp += p; ts += sup; tf += fb
    if tw == 0:
        rep.ok(f"no banned marketing terms in the brand's own voice ({len(targets)} file(s))")
    if tp == 0:
        rep.ok("no unreferenced proof or compliance claims")
    else:
        rep.note("proof hits are not automatically wrong — each must trace to something "
                 "real, dated and checkable. Confirm every one by hand.")
    if claims and tf == 0:
        rep.ok(f"none of the {len(claims)} forbidden claim(s) in "
               f"{os.path.basename(claims_path)} appear")
    elif not claims:
        rep.note(f"no {CLAIMS_FILE}: stage 1's forbidden claims are not being enforced")
    if ts:
        rep.note(f"{ts} match(es) suppressed as quoted material, labelled research, or "
                 f"prohibitions. Re-run with --show-suppressed to audit them.")


# ───────────────────────────────────────────────────────────── render ──
# The rendered layer. Iron Law 1 says an undeclared pairing is an unverified
# pairing, and only a browser knows which pairings a page actually paints.
# Needs Playwright and a Chromium build: pip install playwright &&
# python -m playwright install chromium.
#
# Backgrounds are composited up the ancestor chain to the first opaque ground
# (the canvas is white). Text painted over an absolutely positioned sibling,
# or over a background image, is outside that model: images are reported as
# unverifiable rather than guessed at.

_RENDER_JS = r"""
(() => {
  const cvs = document.createElement('canvas'); cvs.width = cvs.height = 1;
  const ctx = cvs.getContext('2d', {willReadFrequently: true});
  const parse = (css) => {
    const m = /^rgba?\(([^)]*)\)$/.exec((css || '').trim());
    if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
             return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    if (!css || css === 'transparent') return [0, 0, 0, 0];
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255];
  };
  const over = (t, u) => {
    const a = t[3] + u[3] * (1 - t[3]); if (a === 0) return [0, 0, 0, 0];
    return [0, 1, 2].map(i => (t[i] * t[3] + u[i] * u[3] * (1 - t[3])) / a).concat([a]);
  };
  const describe = (el) => {
    let d = el.tagName.toLowerCase();
    if (el.id) d += '#' + el.id;
    const c = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (c.length) d += '.' + c.join('.');
    return d;
  };
  const ground = (el) => {
    const layers = []; let image = null;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none' && !image) image = describe(n);
      const c = parse(cs.backgroundColor);
      if (c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let acc = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return {bg: acc, image};
  };
  const opacity = (el) => { let o = 1;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) o *= parseFloat(getComputedStyle(n).opacity);
    return o; };
  const visible = (el) => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const item = (el, kind, fgCss, text, groundEl) => {
    const cs = getComputedStyle(el), g = ground(groundEl || el), ex = el.closest('[data-contrast-exempt]');
    const fg = parse(fgCss); fg[3] *= opacity(el);
    const lk = el.closest('[data-theme]');
    const lock = (lk && lk !== document.documentElement) ? lk.getAttribute('data-theme') : null;
    return {kind, where: describe(el), lock, text: (text || '').trim().replace(/\s+/g, ' ').slice(0, 40),
            fg, bg: g.bg, image: g.image, size: parseFloat(cs.fontSize),
            weight: parseInt(cs.fontWeight, 10) || 400,
            exempt: ex ? (ex.getAttribute('data-contrast-exempt') || '') : null,
            disabled: !!el.closest(':disabled,[aria-disabled="true"]')};
  };
  window.__bc = {
    describe, ground, parse,
    pairs() {
      const out = [], seen = new Set();
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) {
        const t = w.currentNode, el = t.parentElement;
        if (!t.nodeValue.trim() || !el || seen.has(el)) continue;
        seen.add(el);
        if (el.closest('script,style,noscript,template') || !visible(el) || opacity(el) === 0) continue;
        out.push(item(el, 'text', getComputedStyle(el).color, t.nodeValue));
      }
      const fields = 'input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=color]):not([type=submit]):not([type=button]),select,textarea';
      document.querySelectorAll(fields).forEach(el => {
        if (!visible(el)) return;
        const cs = getComputedStyle(el);
        if (el.value) out.push(item(el, 'text', cs.color, el.value));
        else if (el.placeholder) out.push(item(el, 'text', getComputedStyle(el, '::placeholder').color, el.placeholder));
        if (cs.borderTopStyle !== 'none' && parseFloat(cs.borderTopWidth) > 0)
          out.push(item(el, 'ui', cs.borderTopColor, '(control border)', el.parentElement));
      });
      return out;
    },
    focused() {
      const el = document.activeElement;
      if (!el || el === document.body || el === document.documentElement) return null;
      const cs = getComputedStyle(el);
      const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
      const lk = el.closest('[data-theme]');
      return {where: describe(el), text: (el.innerText || el.value || '').trim().slice(0, 30),
              lock: (lk && lk !== document.documentElement) ? lk.getAttribute('data-theme') : null,
              outline: outline ? parse(cs.outlineColor) : null, shadow: cs.boxShadow !== 'none',
              bg: ground(el.parentElement || el).bg, key: describe(el) + '|' + (el.innerText || el.value || '').slice(0, 30)};
    },
    overflow() { return document.documentElement.scrollWidth - document.documentElement.clientWidth; },
    motion() {
      const out = [];
      for (const el of document.querySelectorAll('*')) {
        const cs = getComputedStyle(el);
        if (cs.animationName === 'none') continue;
        const secs = cs.animationDuration.split(',').map(v => v.trim().endsWith('ms') ? parseFloat(v) / 1000 : parseFloat(v));
        if (Math.max(...secs) > 0.01) out.push(describe(el));
      }
      return out;
    },
  };
})();
"""

_STILL = "*,*::before,*::after{transition:none!important;animation:none!important}"


def _near(a: RGBA, b: RGBA, tol: float = 2.5) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a[:3], b[:3]))


def playwright_ready() -> Optional[str]:
    """None when a browser can launch, else the reason it cannot."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Playwright is not installed (pip install playwright)"
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
    except Exception as exc:                     # noqa: BLE001 - report, never crash
        return f"no launchable Chromium ({str(exc).splitlines()[0][:120]}); run: " \
               f"python -m playwright install chromium"
    return None


def cmd_render(args: argparse.Namespace, rep: Report) -> None:
    html = args.html
    rep.section(f"RENDER · {html}")
    is_url = html.startswith(("http://", "https://"))
    if is_url and not args.pairs:
        rep.fail("rendering a URL needs --pairs PATH (the brand's pairs.tsv)")
        return
    if not is_url and not os.path.exists(html):
        rep.fail(f"not found: {html}")
        return
    why = playwright_ready()
    if why:
        rep.fail(f"cannot run the rendered layer: {why}")
        return
    from playwright.sync_api import sync_playwright

    pairs_path = args.pairs or os.path.join(os.path.dirname(html) or ".", "pairs.tsv")
    tokens, err = _tokens_for(pairs_path, getattr(args, "tokens", None))
    declared: Dict[str, List[Tuple[RGBA, RGBA]]] = {t: [] for t in THEMES}
    if os.path.exists(pairs_path) and not err:
        for row in read_pairs(pairs_path, _Palette(tokens)):
            for t in ((row.theme,) if row.theme else THEMES):
                declared[t].append((row.f, row.b))
    else:
        rep.warn(f"no pairs file at {pairs_path}: every rendered pairing will read as undeclared")
    widths = [int(w) for w in str(args.widths).split(",") if w.strip()]
    if is_url:
        from urllib.parse import urlsplit
        parts = urlsplit(html)
        url, same_origin = html, f"{parts.scheme}://{parts.netloc}/"
    else:
        url, same_origin = pathlib.Path(html).resolve().as_uri(), None
    # --as-is: a page with one theme of its own (a share card) is rendered once,
    # untouched, and may match a declared pairing from either theme.
    themes = ("as-is",) if getattr(args, "as_is", False) else THEMES
    union = declared["light"] + declared["dark"]

    def declared_for(theme):
        return union if theme == "as-is" else declared[theme]

    undeclared: Dict[tuple, list] = {}
    low: Dict[tuple, list] = {}
    exempt, images, counts = set(), set(), {t: 0 for t in themes}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def open_page(theme, width, reduce="no-preference", still=True):
            ctx = browser.new_context(viewport={"width": width, "height": 900},
                                      color_scheme="light" if theme == "as-is" else theme,
                                      reduced_motion=reduce)
            # Offline, as a reviewer on a locked-down network sees it. A served
            # page may also load from its own origin, and nothing else.
            allowed = ("file:", "data:") + ((same_origin,) if same_origin else ())
            ctx.route("**/*", lambda r: r.continue_()
                      if r.request.url.startswith(allowed) else r.abort())
            page = ctx.new_page()
            page.goto(url)
            if still:
                page.add_style_tag(content=_STILL)
            if theme != "as-is":
                page.evaluate("t => document.documentElement.setAttribute('data-theme', t)",
                              theme)
            page.evaluate(_RENDER_JS)
            return ctx, page

        for theme in themes:
            for width in widths:
                ctx, page = open_page(theme, width)
                spill = page.evaluate("() => window.__bc.overflow()")
                if spill > 0:
                    rep.fail(f"{theme} {width}px: horizontal overflow, the page is {spill}px "
                             f"wider than the viewport")
                for it in page.evaluate("() => window.__bc.pairs()"):
                    if it["disabled"]:
                        continue
                    if it["exempt"] is not None:
                        exempt.add((it["where"], it["exempt"] or "(no reason given)"))
                        continue
                    if it["image"]:
                        images.add((theme, it["where"], it["image"]))
                    f = composite(tuple(it["fg"]), tuple(it["bg"]))
                    b = tuple(it["bg"])
                    counts[theme] += 1
                    # A theme-locked panel (the tile shows both themes at once) is
                    # judged against its own theme's pairings.
                    eff = it["lock"] if it.get("lock") in THEMES else theme
                    label = theme if eff == theme else f"{theme}, {eff} panel"
                    r = contrast_of(f, b)
                    if it["kind"] == "ui":
                        thr = 3.0
                    else:
                        large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
                        thr = 3.0 if large else 4.5
                    key = (label, to_hex(f), to_hex(b))
                    if r < thr:
                        low.setdefault(key + (thr,), []).append(it)
                    if not any(_near(f, df) and _near(b, db) for df, db in declared_for(eff)):
                        undeclared.setdefault(key, []).append(it)
                ctx.close()

            # Focus: walk the tab order once per theme at the widest width.
            ctx, page = open_page(theme, max(widths))
            first = None
            for _ in range(60):
                page.keyboard.press("Tab")
                fx = page.evaluate("() => window.__bc.focused()")
                if not fx or fx["key"] == first:
                    break
                first = first or fx["key"]
                if not fx["outline"] and not fx["shadow"]:
                    rep.fail(f"{theme}: no visible focus indicator on {fx['where']} "
                             f"\"{fx['text']}\" (outline none, no box-shadow)")
                    continue
                if fx["outline"]:
                    ring, g = composite(tuple(fx["outline"]), tuple(fx["bg"])), tuple(fx["bg"])
                    r = contrast_of(ring, g)
                    if r < 3.0:
                        rep.fail(f"{theme}: focus ring on {fx['where']} is {fmt_ratio(r)}:1 "
                                 f"against its ground, needs 3.0:1")
                    eff = fx["lock"] if fx.get("lock") in THEMES else theme
                    if not any(_near(ring, df) and _near(g, db)
                               for df, db in declared_for(eff)):
                        undeclared.setdefault((theme, to_hex(ring), to_hex(g)), []).append(
                            {"where": fx["where"], "text": "(focus ring)", "kind": "ui"})
            ctx.close()

        ctx, page = open_page(themes[0] if themes[0] == "as-is" else "light", max(widths),
                              reduce="reduce", still=False)
        moving = page.evaluate("() => window.__bc.motion()")
        if moving:
            rep.fail(f"animation survives reduced motion on {len(moving)} element(s): "
                     f"{sorted(set(moving))[:4]}. The reduced state must be the finished state.")
        else:
            rep.ok("reduced motion: no animation survives prefers-reduced-motion: reduce")
        ctx.close()
        browser.close()

    def unique(items):
        return list({(i["where"], i["text"]): i for i in items}.values())

    for (theme, fh, bh, thr), items in sorted(low.items()):
        items = unique(items)
        it = items[0]
        r = contrast_of(parse_colour(fh), parse_colour(bh))
        more = f" ({len(items)} elements)" if len(items) > 1 else ""
        rep.fail(f"{theme}: {it['where']} \"{it['text']}\" renders {fh} on {bh} at "
                 f"{fmt_ratio(r)}:1, needs {thr}:1{more}")
    for (theme, fh, bh), items in sorted(undeclared.items()):
        items = unique(items)
        it = items[0]
        r = contrast_of(parse_colour(fh), parse_colour(bh))
        rep.fail(f"{theme}: undeclared pairing {fh} on {bh} ({fmt_ratio(r)}:1), "
                 f"{len(items)} element(s), e.g. {it['where']} \"{it['text']}\". "
                 f"Declare it in pairs.tsv by token name, or change the element.")
    for theme, where, img in sorted(images):
        rep.warn(f"{theme}: {where} sits on a background image ({img}); its contrast "
                 f"cannot be computed from colours. Check it by eye and document how.")
    for where, reason in sorted(exempt):
        rep.note(f"exempt from contrast: {where} ({reason})")
    for theme in themes:
        if not any(k[0].split(",")[0] == theme for k in list(low) + list(undeclared)):
            rep.ok(f"{theme}: {counts[theme]} rendered pairing(s) at {widths}px, "
                   f"all declared and meeting their threshold")


# ───────────────────────────────────────────────────────────── assets ──
# Iron Law 3: build what you specify. The guidelines specify a wordmark, a
# mark, an icon set, an avatar and a share image; these checks read the files
# themselves. Icon sizes and roles follow the 2026 minimal set (Evil Martians,
# "How to Favicon", updated 2026-01-21) and the W3C maskable safe zone (a
# centred circle of radius 40%).

ASSET_PNGS = {
    "apple-touch-icon.png": (180, "opaque"),
    "icon-192.png": (192, None),
    "icon-512.png": (512, None),
    "icon-mask.png": (512, "mask"),
    "avatar.png": (400, "avatar"),
}
LOGO_SVGS = ("wordmark.svg", "mark.svg", "icon.svg")
OG_SIZE = (1200, 630)
_SVG_BANNED = {"text": "live text", "tspan": "live text", "textPath": "live text",
               "image": "an embedded or linked image", "foreignObject": "foreign HTML content",
               "script": "a script", "iframe": "an iframe"}


class PNGImage:
    def __init__(self, width, height, ctype, depth, interlace):
        self.width, self.height, self.ctype = width, height, ctype
        self.depth, self.interlace = depth, interlace
        self.data: Optional[bytearray] = None
        self.ch = {0: 1, 2: 3, 4: 2, 6: 4}.get(ctype, 0)
        self.text: Dict[str, str] = {}

    def px(self, x: int, y: int) -> Tuple[int, int, int, int]:
        i = (y * self.width + x) * self.ch
        d = self.data
        if self.ctype == 6:
            return d[i], d[i + 1], d[i + 2], d[i + 3]
        if self.ctype == 2:
            return d[i], d[i + 1], d[i + 2], 255
        if self.ctype == 4:
            return d[i], d[i], d[i], d[i + 1]
        return d[i], d[i], d[i], 255


def read_png(path: str, decode: bool = True) -> PNGImage:
    """Size always; pixels for 8-bit, non-interlaced grey/RGB/RGBA (stdlib only)."""
    import struct
    import zlib
    blob = open(path, "rb").read()
    if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG file")
    pos, idat, img = 8, [], None
    while pos + 8 <= len(blob):
        n, tag = struct.unpack(">I4s", blob[pos:pos + 8])
        data = blob[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", data)
            img = PNGImage(w, h, ctype, depth, interlace)
        elif tag == b"IDAT":
            idat.append(data)
        elif tag == b"tEXt" and img is not None and b"\x00" in data:
            key, _, value = data.partition(b"\x00")
            img.text[key.decode("latin-1")] = value.decode("latin-1")
        elif tag == b"IEND":
            break
    if img is None:
        raise ValueError("PNG has no IHDR")
    if not decode or img.depth != 8 or img.interlace or not img.ch:
        return img
    raw, bpp = zlib.decompress(b"".join(idat)), img.ch
    stride = img.width * bpp
    out, prev = bytearray(), bytearray(stride)
    for y in range(img.height):
        base = y * (stride + 1)
        f, line = raw[base], bytearray(raw[base + 1:base + 1 + stride])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif f == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b, c = prev[i], (prev[i - bpp] if i >= bpp else 0)
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += line
        prev = line
    img.data = out
    return img


def _outside_circle_is_ground(img: PNGImage, radius: float, tol: int = 3) -> bool:
    """True when every pixel outside a centred circle matches the corner pixel."""
    ground = img.px(0, 0)
    cx, cy = img.width / 2, img.height / 2
    r2 = radius * radius
    for y in range(img.height):
        dy2 = (y + 0.5 - cy) ** 2
        for x in range(img.width):
            if (x + 0.5 - cx) ** 2 + dy2 > r2:
                p = img.px(x, y)
                if any(abs(p[k] - ground[k]) > tol for k in range(4)):
                    return False
    return True


def _check_logo_svg(path: str, rep: Report) -> None:
    import xml.etree.ElementTree as ET
    name = os.path.basename(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        rep.fail(f"{name}: not well-formed SVG ({exc})")
        return
    local = lambda t: t.rsplit("}", 1)[-1]          # noqa: E731
    if local(root.tag) != "svg":
        rep.fail(f"{name}: root element is <{local(root.tag)}>, not <svg>")
        return
    problems = []
    try:
        vb = [float(v) for v in re.split(r"[\s,]+", (root.get("viewBox") or "").strip())]
        if len(vb) != 4 or vb[2] <= 0 or vb[3] <= 0:
            raise ValueError
    except ValueError:
        problems.append("no usable viewBox, so it cannot scale")
    for el in root.iter():
        t = local(el.tag)
        if t in _SVG_BANNED:
            problems.append(f"contains <{t}> ({_SVG_BANNED[t]})")
        for k, v in el.attrib.items():
            if local(k) == "href" and not v.strip().startswith("#"):
                problems.append(f"references {v!r} outside the file")
        if t == "style" and el.text and (
                "@import" in el.text or re.search(r"url\(\s*['\"]?(?!#|data:)", el.text)):
            problems.append("its <style> fetches something outside the file")
    if problems:
        rep.fail(f"{name}: " + "; ".join(sorted(set(problems))) + ". A logo file is outlined "
                 "paths in one self-contained SVG: live text renders in whatever font the "
                 "viewer has.")
        return
    rep.ok(f"{name}: outlined, self-contained vector (viewBox {root.get('viewBox')})")
    if name == "wordmark.svg":
        meta = next((el.text for el in root.iter() if local(el.tag) == "metadata"), None)
        try:
            record = json.loads(meta or "")
        except ValueError:
            record = {}
        if not record.get("fontSha256"):
            rep.warn("wordmark.svg carries no construction record. Build it with "
                     "`brandassets.py wordmark` so the font file, size, tracking and features "
                     "that reproduce it travel with it.")


def _check_freshness(d: str, brand_dir: str, rep: Report) -> None:
    """A rendered PNG must still match what it was rendered from.

    brandassets records the source file (and any colour tokens) in a tEXt
    chunk. If the source changed, or a token now resolves differently, the
    PNG is stale. A PNG without the record cannot be proven current.
    """
    import hashlib
    tokens_path = os.path.join(brand_dir, "tokens.css")
    tok = parse_token_css(open(tokens_path, encoding="utf-8").read()) \
        if os.path.exists(tokens_path) else None
    unproven = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".png"):
            continue
        try:
            record = json.loads(read_png(os.path.join(d, name), decode=False).text["brandassets"])
        except (KeyError, ValueError, OSError):
            unproven.append(name)
            continue
        src = os.path.normpath(os.path.join(d, record.get("source", "")))
        if not os.path.exists(src):
            rep.warn(f"{name}: its source {record.get('source')} is gone; cannot prove it current")
            continue
        digest = hashlib.sha256(open(src, "rb").read()).hexdigest()
        if digest != record.get("sha256"):
            rep.fail(f"{name} is stale: {os.path.basename(src)} changed after it was rendered. "
                     f"Re-run brandassets.")
            continue
        for token, theme, value in (record.get("tokens") or []):
            if tok is None:
                break
            table = tok.theme(theme)
            now = resolve_var(f"var({token})", table)
            if "var(" in now or not same_value(now, value):
                rep.fail(f"{name} is stale: {token} ({theme}) is now {now}, but it was rendered "
                         f"with {value}. Re-run brandassets.")
                break
    if unproven:
        rep.warn(f"{len(unproven)} PNG(s) carry no brandassets record, so nothing proves they "
                 f"match their source: {unproven[:4]}")


def cmd_assets(args: argparse.Namespace, rep: Report) -> None:
    import struct
    d = args.assets or os.path.join(args.dir, "assets")
    rep.section(f"ASSETS · {d}")
    if not os.path.isdir(d):
        rep.fail(f"no {d} directory. The guidelines specify a wordmark, a mark, an icon set, an "
                 f"avatar and a share image, and Iron Law 3 requires them built. Generate "
                 f"them with scripts/brandassets.py (see references/assets.md), or pass "
                 f"--assets PATH.")
        return

    def need(name):
        path = os.path.join(d, name)
        if not os.path.exists(path):
            rep.fail(f"missing {name}")
            return None
        return path

    for name in LOGO_SVGS:
        path = need(name)
        if path:
            _check_logo_svg(path, rep)

    for name, (size, rule) in ASSET_PNGS.items():
        path = need(name)
        if not path:
            continue
        try:
            img = read_png(path, decode=rule is not None)
        except (ValueError, OSError) as exc:
            rep.fail(f"{name}: {exc}")
            continue
        if (img.width, img.height) != (size, size):
            rep.fail(f"{name} is {img.width}x{img.height}; it must be {size}x{size}")
            continue
        if rule and img.data is None:
            rep.warn(f"{name}: cannot decode this PNG variant to check its pixels; check by eye")
            continue
        if rule == "opaque":
            alpha = img.data[img.ch - 1::img.ch] if img.ch in (2, 4) else b"\xff"
            if min(alpha) < 255:
                rep.fail(f"{name} is not fully opaque. iOS paints transparency black; "
                         f"flatten it onto the brand ground.")
                continue
        elif rule == "mask" and not _outside_circle_is_ground(img, size * 0.4):
            rep.fail(f"{name}: artwork leaves the maskable safe zone (a centred circle of "
                     f"radius 40%), so launchers that mask to a circle will cut it.")
            continue
        elif rule == "avatar" and not _outside_circle_is_ground(img, size / 2):
            rep.fail(f"{name}: artwork reaches outside the inscribed circle, so a round avatar "
                     f"crop will cut it.")
            continue
        rep.ok(f"{name}: {size}x{size}" + {"opaque": ", opaque", "mask": ", inside the "
                                           "maskable safe zone", "avatar": ", survives a "
                                           "circular crop"}.get(rule or "", ""))

    path = need("favicon.ico")
    if path:
        blob = open(path, "rb").read()
        try:
            reserved, kind, count = struct.unpack("<HHH", blob[:6])
            if reserved != 0 or kind != 1:
                raise ValueError
            sizes = sorted({(blob[6 + 16 * i] or 256) for i in range(count)})
        except (ValueError, struct.error, IndexError):
            rep.fail("favicon.ico is not a valid ICO file")
            sizes = None
        if sizes is not None:
            if 32 in sizes:
                rep.ok(f"favicon.ico: {', '.join(str(x) for x in sizes)}px")
            else:
                rep.fail(f"favicon.ico holds {sizes}px but no 32px image, the size tabs use")

    ogs = sorted(f for f in os.listdir(d) if f.startswith("og") and f.endswith(".png"))
    if "og-default.png" not in ogs:
        rep.fail("missing og-default.png, the share card used when a page has none of its own")
    for name in ogs:
        img = read_png(os.path.join(d, name), decode=False)
        if (img.width, img.height) != OG_SIZE:
            rep.fail(f"{name} is {img.width}x{img.height}; share cards are 1200x630")
        else:
            rep.ok(f"{name}: 1200x630")

    _check_freshness(d, args.dir, rep)

    path = need("manifest.webmanifest")
    if path:
        try:
            m = json.load(open(path, encoding="utf-8"))
        except ValueError as exc:
            rep.fail(f"manifest.webmanifest is not valid JSON: {exc}")
            return
        bad = []
        for key in ("name", "short_name"):
            v = str(m.get(key, "")).strip()
            if not v or re.match(r"^\[.*\]$", v) or "TODO" in v.upper():
                bad.append(f"{key} is empty or a placeholder")
        icons = m.get("icons") or []
        declared = {i.get("sizes") for i in icons}
        for want in ("192x192", "512x512"):
            if want not in declared:
                bad.append(f"no {want} icon")
        if not any("maskable" in str(i.get("purpose", "")) for i in icons):
            bad.append("no maskable icon")
        for i in icons:
            src = os.path.join(d, str(i.get("src", "")).lstrip("/").split("/")[-1])
            if not os.path.exists(src):
                bad.append(f"icon {i.get('src')!r} does not exist")
                continue
            try:
                img = read_png(src, decode=False)
                if i.get("sizes") and i["sizes"] != f"{img.width}x{img.height}":
                    bad.append(f"{i.get('src')} is {img.width}x{img.height}, "
                               f"declared {i['sizes']}")
            except ValueError:
                pass
        if bad:
            rep.fail("manifest.webmanifest: " + "; ".join(bad))
        else:
            rep.ok(f"manifest.webmanifest: {len(icons)} icon(s) exist at their declared "
                   f"sizes, including a maskable one")


# ──────────────────────────────────────────────────────────────── all ──

def cmd_all(args: argparse.Namespace, rep: Report) -> None:
    d = args.dir
    cmd_tokens(argparse.Namespace(dir=d, css=None, json=None, require_generated=True), rep)
    pairs = getattr(args, "pairs", None) or os.path.join(d, "pairs.tsv")
    if os.path.exists(pairs):
        css = os.path.join(d, "tokens.css")
        cmd_contrast(argparse.Namespace(pairs=pairs,
                                        tokens=css if os.path.exists(css) else None), rep)
    else:
        rep.section("CONTRAST")
        rep.fail(f"no pairings file at {pairs}. Every foreground/background pairing the "
                 f"system ships must be declared and computed — an undeclared pairing is an "
                 f"unverified pairing. If it lives outside the brand directory, pass "
                 f"--pairs PATH.")
    if not args.claims and not os.path.exists(os.path.join(d, CLAIMS_FILE)):
        rep.section("CLAIMS")
        rep.fail(f"no {CLAIMS_FILE}: the claims stage 1 ruled out are not written down, so "
                 f"nothing enforces them. Start from templates/{CLAIMS_FILE}.")
    cmd_lexicon(argparse.Namespace(dir=d, strict=args.strict, claims=args.claims,
                                   show_suppressed=args.show_suppressed), rep)

    # Fonts the system ships are checked against the licence that ships with them.
    fonts_dir = os.path.join(d, "fonts")
    if os.path.isdir(fonts_dir):
        faces = sorted(f for f in os.listdir(fonts_dir)
                       if f.lower().endswith((".ttf", ".otf", ".woff", ".woff2")))
        licence = next((os.path.join(fonts_dir, n) for n in
                        ("OFL.txt", "LICENSE.txt", "LICENSE", "OFL.md", "LICENSE.md")
                        if os.path.exists(os.path.join(fonts_dir, n))),
                       os.path.join(fonts_dir, "OFL.txt"))
        for face in faces:
            cmd_fonts(argparse.Namespace(font=os.path.join(fonts_dir, face),
                                         glyphs=args.glyphs, licence=licence), rep)

    cmd_assets(argparse.Namespace(dir=d, assets=args.assets), rep)

    tile = os.path.join(d, "style-tile.html")
    css = os.path.join(d, "tokens.css")
    common = dict(pairs=pairs if os.path.exists(pairs) else None,
                  tokens=css if os.path.exists(css) else None)
    if not os.path.exists(tile):
        rep.section("RENDER")
        rep.fail("missing style-tile.html, the working artifact the system is verified against")
    elif args.no_render:
        rep.section("RENDER")
        rep.warn("the rendered layer was skipped by request (--no-render): no check in this "
                 "run proves every painted pairing is declared (Iron Law 1).")
    else:
        why = playwright_ready()
        if why:
            rep.section("RENDER")
            rep.fail(f"the rendered layer did not run: {why}. Without it, no check proves every "
                     f"painted pairing is declared (Iron Law 1). Install Chromium, or pass "
                     f"--no-render to skip it knowingly.")
        else:
            cmd_render(argparse.Namespace(html=tile, widths=args.widths, as_is=False, **common),
                       rep)
            card = os.path.join(d, "og-card.html")
            if os.path.exists(card):
                cmd_render(argparse.Namespace(html=card, widths="1200", as_is=True, **common),
                           rep)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="brandcheck",
        description="Mechanical verification for a brand system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("contrast", help="compute every declared foreground/background pairing")
    c.add_argument("pairs", help="TSV: name<TAB>fg<TAB>bg<TAB>threshold[<TAB>theme]; fg and "
                                 "bg are colours or token names (--x or var(--x))")
    c.add_argument("--tokens", help="tokens.css to resolve token names against "
                                    "(default: tokens.css beside the pairs file)")
    c.set_defaults(fn=cmd_contrast)

    t = sub.add_parser("tokens", help="CSS<->JSON agreement, theme parity, var() resolution")
    t.add_argument("dir")
    t.add_argument("--css")
    t.add_argument("--json")
    t.set_defaults(fn=cmd_tokens)

    e = sub.add_parser("export", help="generate tokens.json (DTCG 2025.10) from tokens.css")
    e.add_argument("src", help="brand directory or path to tokens.css")
    e.add_argument("-o", "--output", help="output path (default: tokens.json beside the CSS)")
    e.set_defaults(fn=cmd_export)

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
    l.add_argument("--claims", help=f"forbidden-claims file (default: DIR/{CLAIMS_FILE}); "
                                    f"point it at the brand's file to scan a site elsewhere")
    l.set_defaults(fn=cmd_lexicon)

    r = sub.add_parser("render", help="render the style tile in a browser: every painted "
                                      "pairing declared and passing, overflow, focus, motion")
    r.add_argument("html", help="the style tile, any self-contained page, or a served URL "
                                "(http://localhost:3000/) with --pairs")
    r.add_argument("--pairs", help="pairings file (default: pairs.tsv beside the page)")
    r.add_argument("--tokens", help="tokens.css (default: beside the pairs file)")
    r.add_argument("--widths", default="320,1440",
                   help="viewport widths in CSS px (default 320,1440; 320 is WCAG reflow)")
    r.add_argument("--as-is", action="store_true",
                   help="render once without switching themes, matching pairings declared "
                        "for either theme (for a single-theme page such as the share card)")
    r.set_defaults(fn=cmd_render)

    s_ = sub.add_parser("assets", help="logo SVGs, icon set, avatar, share cards, manifest")
    s_.add_argument("dir", help="brand directory (assets are read from DIR/assets)")
    s_.add_argument("--assets", help="asset directory, if not DIR/assets")
    s_.set_defaults(fn=cmd_assets)

    a = sub.add_parser("all", help="every check that applies to a brand directory",
                       description="Runs tokens, contrast, lexicon, fonts, assets and render over "
                                   "a brand directory: every token, pairing, document, font, "
                                   "asset and rendered page the system ships. Requires "
                                   "forbidden-claims.txt and style-tile.html.")
    a.add_argument("dir")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--show-suppressed", action="store_true")
    a.add_argument("--pairs", help="pairings file, if kept outside BRAND_DIR")
    a.add_argument("--claims", help=f"forbidden-claims file (default: BRAND_DIR/{CLAIMS_FILE})")
    a.add_argument("--glyphs", help="characters the system relies on, checked in every font "
                                    f"under BRAND_DIR/fonts (default {DEFAULT_GLYPHS})")
    a.add_argument("--widths", default="320,1440", help="render widths (default 320,1440)")
    a.add_argument("--assets", help="asset directory, if not BRAND_DIR/assets")
    a.add_argument("--no-render", action="store_true",
                   help="skip the rendered layer knowingly; the run then proves less")
    a.set_defaults(fn=cmd_all)

    p.add_argument("--version", action="version",
                   version=f"brandcheck {__version__}")
    args = p.parse_args(argv)
    rep = Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
