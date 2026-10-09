#!/usr/bin/env python3
"""contactsheet — lay images out on a few sheets, so all of them get looked at.

A reference project of forty images, or ninety photo candidates, is too many
to open one by one, and a summary of them is not looking at them. A contact
sheet puts them on a handful of images that can each be read in one go.

    contactsheet DIR_OR_FILES… --out PREFIX [--cols 2|6] [--numbered]

Writes PREFIX0.jpg, PREFIX1.jpg, … (stale higher-numbered sheets from an
earlier run are removed). A directory contributes its images in natural
filename order (2.jpg before 10.jpg); files are taken in the order given.

  --cols 2 (and any N up to 3) keeps every image's aspect ratio: each cell is
      1400/N px wide, as tall as the image needs, cut at the sheet's height.
      For design references, where the composition matters.
  --cols 6 (any N above 3) fits each image inside a 300px square.
      For choosing among many candidates.
  --numbered puts each image's position (1-based, in the order above) in its
      top-left corner, so "use 7 and 23" means the same thing to everyone.

Each sheet is at most --max-height px tall (default 2000).

Needs Pillow (pip install pillow). Exit code is 0 only if a sheet was written.
"""
from __future__ import annotations

__version__ = "1.3.0"

import argparse
import os
import pathlib
import re
import sys
from typing import List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brandcheck as bc  # noqa: E402  (shared reporting)

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
ASPECT_WIDTH = 1400          # total image width of an aspect-keeping sheet
THUMB = 300                  # cell size of a thumbnail sheet
GAP = 10
GROUND = (242, 242, 242)


def _pil():
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        raise RuntimeError("Pillow is not installed (pip install pillow)") from None
    return Image, ImageDraw, ImageFont, ImageOps


def natural_key(name: str):
    """'f2.jpg' sorts before 'f10.jpg'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def sheet_name_pattern(prefix) -> "re.Pattern[str]":
    """The files a run with this prefix writes: PREFIX0.jpg, PREFIX1.jpg, …"""
    return re.compile(re.escape(pathlib.Path(prefix).name) + r"\d+\.jpg$")


def collect(inputs: Sequence, exclude: Optional["re.Pattern[str]"] = None) -> List[pathlib.Path]:
    """Images from files and directories, in the order a person would expect."""
    out: List[pathlib.Path] = []
    for raw in inputs:
        p = pathlib.Path(raw)
        if p.is_dir():
            found = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXT
                     and not (exclude and exclude.match(f.name))]
            out.extend(sorted(found, key=lambda f: natural_key(f.name)))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f"not found: {p}")
    return out


def _upright_size(im) -> Tuple[int, int]:
    """Size after EXIF rotation, read without decoding the pixels."""
    w, h = im.size
    try:
        orientation = im.getexif().get(274, 1)
    except Exception:                            # noqa: BLE001 - no EXIF is fine
        orientation = 1
    return (h, w) if orientation in (5, 6, 7, 8) else (w, h)


def _load(path, box: Tuple[int, int]):
    """Decoded, upright, RGB, scaled so it fits `box` (aspect kept)."""
    Image, _, _, ImageOps = _pil()
    with Image.open(path) as im:
        im.draft("RGB", (box[0] * 2, box[1] * 2))   # JPEG: decode at a smaller scale
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            ground = Image.new("RGB", im.size, (255, 255, 255))
            ground.paste(im, mask=im.split()[-1])
            im = ground
        else:
            im = im.convert("RGB")
    if im.width > box[0] or im.height > box[1]:
        im.thumbnail(box, Image.LANCZOS)
    return im


def _font(size: int):
    _, _, ImageFont, _ = _pil()
    try:
        return ImageFont.load_default(size=size)    # Pillow >= 10.1 with FreeType
    except Exception:                            # noqa: BLE001 - small bitmap font instead
        return ImageFont.load_default()


def _label(draw, xy: Tuple[int, int], text: str, font) -> None:
    x, y = xy
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pad = 6
    draw.rectangle((x, y, x + (right - left) + 2 * pad, y + (bottom - top) + 2 * pad),
                   fill=(0, 0, 0))
    draw.text((x + pad - left, y + pad - top), text, fill=(255, 255, 255), font=font)


def build_sheets(images: Sequence, prefix, cols: int = 2, numbered: bool = False,
                 labels: Optional[Sequence] = None, max_height: int = 2000,
                 rows: Optional[int] = None, cell: Optional[int] = None,
                 quality: int = 82) -> Tuple[List[pathlib.Path], List[Tuple[str, str]]]:
    """Write PREFIX0.jpg, PREFIX1.jpg, …; return (sheets, [(skipped file, why)]).

    `labels` overrides the numbers drawn with --numbered (default 1, 2, 3, …
    by position, so a skipped file keeps its number free).
    """
    Image, ImageDraw, _, _ = _pil()
    if cols < 1:
        raise ValueError("--cols must be at least 1")
    if max_height < 200:
        raise ValueError("--max-height must be at least 200")
    images = [pathlib.Path(p) for p in images]
    labels = [str(v) for v in labels] if labels is not None else \
        [str(i + 1) for i in range(len(images))]
    if len(labels) != len(images):
        raise ValueError("one label per image")

    # Measure first (header only), decode later, one sheet at a time.
    items, skipped = [], []
    for path, label in zip(images, labels):
        try:
            with Image.open(path) as im:
                items.append((path, label, _upright_size(im)))
        except Exception as exc:                 # noqa: BLE001 - skip, report, continue
            skipped.append((str(path), str(exc).splitlines()[0][:120] if str(exc) else
                            type(exc).__name__))
    if not items:
        return [], skipped

    aspect = cols <= 3
    if aspect:
        cw = cell or ASPECT_WIDTH // cols
        max_ch = min(1400, max_height - 2 * GAP)
        heights = [min(max_ch, max(1, round(h * cw / w))) for _, _, (w, h) in items]
        row_list = [list(range(i, min(i + cols, len(items)))) for i in range(0, len(items), cols)]
        row_h = [max(heights[k] for k in r) for r in row_list]
        pages: List[List[int]] = [[]]
        used = GAP
        for ri, h in enumerate(row_h):
            if pages[-1] and used + h + GAP > max_height:
                pages.append([])
                used = GAP
            pages[-1].append(ri)
            used += h + GAP
    else:
        cw = cell or THUMB
        per_sheet = rows or max(1, (max_height - GAP) // (cw + GAP))
        row_list = [list(range(i, min(i + cols, len(items)))) for i in range(0, len(items), cols)]
        row_h = [cw] * len(row_list)
        pages = [list(range(i, min(i + per_sheet, len(row_list))))
                 for i in range(0, len(row_list), per_sheet)]

    prefix = pathlib.Path(prefix)
    if prefix.suffix.lower() in (".jpg", ".jpeg"):
        prefix = prefix.with_suffix("")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    font = _font(28 if aspect else 24)
    width = cols * cw + (cols + 1) * GAP
    written: List[pathlib.Path] = []
    for si, page in enumerate(pages):
        height = GAP + sum(row_h[r] + GAP for r in page)
        sheet = Image.new("RGB", (width, height), GROUND)
        draw = ImageDraw.Draw(sheet)
        y = GAP
        for r in page:
            for c, k in enumerate(row_list[r]):
                path, label, (w, h) = items[k]
                x = GAP + c * (cw + GAP)
                try:
                    if aspect:
                        im = _load(path, (cw, 10 ** 6))
                        if im.width != cw:
                            im = im.resize((cw, max(1, round(im.height * cw / im.width))),
                                           Image.LANCZOS)
                        im = im.crop((0, 0, cw, min(im.height, heights[k])))
                        sheet.paste(im, (x, y))
                    else:
                        im = _load(path, (cw, cw))
                        sheet.paste(im, (x + (cw - im.width) // 2, y + (cw - im.height) // 2))
                except Exception as exc:         # noqa: BLE001 - header read, pixels did not
                    skipped.append((str(path), str(exc).splitlines()[0][:120] or
                                    type(exc).__name__))
                    draw.rectangle((x, y, x + cw - 1, y + row_h[r] - 1), outline=(200, 0, 0),
                                   width=3)
                if numbered:
                    _label(draw, (x, y), label, font)
            y += row_h[r] + GAP
        out = prefix.parent / f"{prefix.name}{si}.jpg"
        sheet.save(out, "JPEG", quality=quality)
        written.append(out)

    # A shorter run must not leave an earlier run's sheet 5 looking current.
    pattern = sheet_name_pattern(prefix)
    for old in prefix.parent.iterdir():
        if pattern.match(old.name) and old not in written:
            old.unlink()
    return written, skipped


def cmd_sheets(args, rep: bc.Report) -> None:
    rep.section(f"CONTACT SHEET · {', '.join(map(str, args.inputs))} -> {args.out}N.jpg")
    try:
        images = collect(args.inputs, exclude=sheet_name_pattern(args.out))
    except FileNotFoundError as exc:
        rep.fail(str(exc))
        return
    if not images:
        rep.fail("no images found")
        return
    try:
        sheets, skipped = build_sheets(images, args.out, cols=args.cols, numbered=args.numbered,
                                       max_height=args.max_height, rows=args.rows,
                                       cell=args.cell)
    except (RuntimeError, ValueError) as exc:
        rep.fail(str(exc))
        return
    for path, why in skipped:
        rep.warn(f"skipped {path}: {why}")
    if not sheets:
        rep.fail("none of the images could be read")
        return
    rep.ok(f"{len(images) - len(skipped)} image(s) on {len(sheets)} sheet(s): "
           f"{', '.join(str(s) for s in sheets)}")
    rep.note("open every sheet and look at every image before writing about them")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="contactsheet", description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("inputs", nargs="+", help="directories and/or image files")
    p.add_argument("--out", required=True, help="output prefix: PREFIX0.jpg, PREFIX1.jpg, …")
    p.add_argument("--cols", type=int, default=2,
                   help="2 keeps aspect ratios (references); 6 makes 300px thumbnails "
                        "(candidates). Default 2")
    p.add_argument("--numbered", action="store_true", help="label each image with its number")
    p.add_argument("--max-height", type=int, default=2000, help="sheet height cap in px")
    p.add_argument("--rows", type=int, help="thumbnail rows per sheet (default: fill the height)")
    p.add_argument("--cell", type=int, help="cell width in px (default 1400/cols, or 300)")
    p.add_argument("--version", action="version", version=f"contactsheet {__version__}")
    p.set_defaults(fn=cmd_sheets)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rep = bc.Report()
    args.fn(args, rep)
    return rep.verdict()


if __name__ == "__main__":
    sys.exit(main())
