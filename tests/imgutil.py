"""Minimal PNG and ICO writers for fixtures (stdlib only, independent of the
code under test)."""
from __future__ import annotations

import pathlib
import struct
import zlib


def png(width: int, height: int, pixel) -> bytes:
    """pixel(x, y) -> (r, g, b, a). 8-bit RGBA, no interlace."""
    rows = []
    for y in range(height):
        rows.append(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width)))
    return _png(width, height, b"".join(rows))


def solid_png(width: int, height: int, rgba=(7, 17, 15, 255)) -> bytes:
    row = b"\x00" + bytes(rgba) * width
    return _png(width, height, row * height)


def _png(width, height, raw):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def ico(images) -> bytes:
    """images: list of (size, png bytes)."""
    head = struct.pack("<HHH", 0, 1, len(images))
    offset, dirs, data = 6 + 16 * len(images), b"", b""
    for size, blob in images:
        dirs += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(blob),
                            offset + len(data))
        data += blob
    return head + dirs + data


BG, FG = (7, 17, 15, 255), (240, 239, 233, 255)

MARK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<title>Mark</title><path fill="currentColor" d="M16 16h32v32H16z"/></svg>')


def centred(size: int, half: float):
    """Ground everywhere, a square of side 2*half in the middle."""
    c = size / 2

    def px(x, y):
        return FG if abs(x + .5 - c) <= half and abs(y + .5 - c) <= half else BG
    return png(size, size, px)


def valid_assets(root: pathlib.Path) -> pathlib.Path:
    a = root / "assets"
    a.mkdir(parents=True, exist_ok=True)
    (a / "wordmark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -700 1200 700">'
        '<title>brand</title><metadata>{"generator": "fixture", "fontSha256": "0"}</metadata>'
        '<g fill="currentColor"><path d="M0 0h500v-700H0z"/></g></svg>')
    (a / "mark.svg").write_text(MARK_SVG)
    (a / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><style>.bg{fill:#07110f}'
        '@media (prefers-color-scheme: dark){.bg{fill:#07110f}}</style>'
        '<rect class="bg" width="512" height="512"/><path fill="#f0efe9" d="M128 128h256v256H128z"/></svg>')
    (a / "favicon.ico").write_bytes(ico([(16, solid_png(16, 16)), (32, solid_png(32, 32))]))
    (a / "apple-touch-icon.png").write_bytes(centred(180, 60))
    (a / "icon-192.png").write_bytes(centred(192, 64))
    (a / "icon-512.png").write_bytes(centred(512, 170))
    (a / "icon-mask.png").write_bytes(centred(512, 140))     # well inside r = 204.8
    (a / "avatar.png").write_bytes(centred(400, 130))        # well inside r = 200
    (a / "og-default.png").write_bytes(solid_png(1200, 630))
    (a / "manifest.webmanifest").write_text(
        '{"name": "Brand", "short_name": "Brand", "theme_color": "#07110f", '
        '"background_color": "#07110f", "icons": ['
        '{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, '
        '{"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}, '
        '{"src": "/icon-mask.png", "sizes": "512x512", "type": "image/png", '
        '"purpose": "maskable"}]}')
    return a
