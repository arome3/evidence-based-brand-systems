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
import math
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


def cmd_contrast(args: argparse.Namespace, rep: Report) -> None:
    rep.section(f"CONTRAST · {args.pairs}")
    if not os.path.exists(args.pairs):
        rep.fail(f"pairs file not found: {args.pairs}")
        return
    tokens = getattr(args, "tokens", None)
    if not tokens:
        beside = os.path.join(os.path.dirname(args.pairs) or ".", "tokens.css")
        tokens = beside if os.path.exists(beside) else None
    elif not os.path.exists(tokens):
        rep.fail(f"tokens file not found: {tokens}")
        return
    palette = _Palette(tokens)

    rows, seen = [], set()
    for lineno, raw in enumerate(open(args.pairs, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            rep.fail(f"line {lineno}: expected 4 or 5 tab-separated fields "
                     f"(name, fg, bg, threshold[, theme]), got {len(parts)}")
            continue
        name, fg, bg, thr_raw = (p.strip() for p in parts[:4])
        theme_raw = parts[4].strip().lower() if len(parts) > 4 and parts[4].strip() else ""
        thr = THRESHOLDS.get(thr_raw.lower(), None)
        if thr is None:
            try:
                thr = float(thr_raw)
            except ValueError:
                rep.fail(f"line {lineno}: threshold {thr_raw!r} is not a number "
                         f"or one of {', '.join(THRESHOLDS)}")
                continue
        uses_tokens = _is_ref(fg) or _is_ref(bg)
        if theme_raw and theme_raw not in ("light", "dark", "both"):
            rep.fail(f"line {lineno}: theme {theme_raw!r} is not light, dark or both")
            continue
        themes = (THEMES if theme_raw in ("", "both") else (theme_raw,)) if uses_tokens \
            else ("",)
        for theme in themes:
            label = f"{name} ({theme})" if theme else name
            try:
                fv, bv = palette.resolve(fg, theme or "light"), palette.resolve(bg, theme or "light")
                for cell, value in ((fg, fv), (bg, bv)):
                    if not _is_ref(cell) and palette.tok and not palette.ships(value):
                        raise ValueError(
                            f"{cell} matches no token in {os.path.basename(tokens)}, so this "
                            f"row verifies a colour the system does not ship (a stale copy?). "
                            f"Name the token instead.")
                f, b = resolve_pair(fv, bv)
            except ValueError as exc:
                rep.fail(f"line {lineno}: {label}: {exc}")
                continue
            note = (f" composited {to_hex(f)}" if parse_colour(fv)[3] < 1.0 else "")
            key = (to_hex(f), to_hex(b), thr)
            rows.append((label, _describe(fg, fv), _describe(bg, bv), contrast_of(f, b),
                         thr, key in seen, note))
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
            rep.warn("tokens.json was not produced by `brandcheck export`, so it is a second "
                     "authored format (Iron Law 4). Generate it: "
                     "python3 scripts/brandcheck.py export BRAND_DIR")
    else:
        rep.warn(f"no {os.path.basename(json_path)} found — shipping only one token format "
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
                if quoted or RESEARCH_LABEL.search(line):
                    suppressed += 1
                    if show_all:
                        rep.note(f"{os.path.basename(path)}:{i} forbidden claim '{shown}' "
                                 f"suppressed ({'quoted' if quoted else 'labelled research'})")
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
           ".svelte")
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


# ──────────────────────────────────────────────────────────────── all ──

def cmd_all(args: argparse.Namespace, rep: Report) -> None:
    d = args.dir
    cmd_tokens(argparse.Namespace(dir=d, css=None, json=None), rep)
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
    cmd_lexicon(argparse.Namespace(dir=d, strict=args.strict, claims=args.claims,
                                   show_suppressed=args.show_suppressed), rep)


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

    a = sub.add_parser("all", help="tokens + contrast + lexicon over a brand directory")
    a.add_argument("dir")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--show-suppressed", action="store_true")
    a.add_argument("--pairs", help="pairings file, if kept outside BRAND_DIR")
    a.add_argument("--claims", help=f"forbidden-claims file (default: BRAND_DIR/{CLAIMS_FILE})")
    a.set_defaults(fn=cmd_all)

    p.add_argument("--version", action="version",
                   version=f"brandcheck {__version__}")
    args = p.parse_args(argv)
    rep = Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
