"""Builds a tiny, licence-free TrueType font for tests.

Rectangles for glyphs, uniform digits, and a single kerning pair (A V = -120)
so that shaping can be told apart from naive advance-width layout.
"""
from __future__ import annotations

import pathlib

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

UPEM = 1000
ADVANCES = {"A": 600, "V": 600, "R": 620, "space": 250}
KERN_AV = -120


def _rect(x0, y0, x1, y1):
    pen = TTGlyphPen(None)
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return pen.glyph()


def build_font(path: pathlib.Path) -> pathlib.Path:
    digits = [f"d{i}" for i in range(10)]
    order = [".notdef", "space", "A", "V", "R", *digits]
    cmap = {0x20: "space", 0x41: "A", 0x56: "V", 0x52: "R"}
    cmap.update({0x30 + i: f"d{i}" for i in range(10)})

    glyphs = {".notdef": _rect(50, 0, 450, 700), "space": TTGlyphPen(None).glyph()}
    for name in ("A", "V", "R", *digits):
        glyphs[name] = _rect(50, 0, 550, 700)
    advances = {".notdef": 500, **ADVANCES, **{d: 560 for d in digits}}

    fb = FontBuilder(UPEM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]
    fb.setupHorizontalMetrics(
        {g: (advances[g], getattr(glyf[g], "xMin", 0)) for g in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Fixture Sans", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.addOpenTypeFeatures(f"feature kern {{ pos A V {KERN_AV}; }} kern;")
    fb.save(str(path))
    return path
