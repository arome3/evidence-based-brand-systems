"""Token files, theme parity and the self-contained artifact."""

BASE_CSS = ":root { --b-color-bg: #ffffff; --b-color-text: #111111; }\n"


def tile(body_style: str, extra_head: str = "", body: str = "<p>x</p>") -> str:
    return (f"<!doctype html><html><head><style>{extra_head}\n"
            f"body {{ background: var(--b-color-bg); color: var(--b-color-text); {body_style} }}"
            f"</style></head><body>{body}</body></html>")


def test_font_face_pointing_at_a_cdn_is_not_self_hosted(run, write, tmp_path):
    write("tokens.css", BASE_CSS)
    write("style-tile.html", tile(
        "font-family: Brand;",
        '@font-face { font-family: "Brand"; '
        'src: url(https://fonts.gstatic.com/s/x/abc.woff2) format("woff2"); }'))
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "self-contained (no external" not in out


def test_font_face_pointing_at_a_local_file_is_a_dependency(run, write, tmp_path):
    write("tokens.css", BASE_CSS)
    write("style-tile.html", tile(
        "font-family: Brand;",
        '@font-face { font-family: "Brand"; src: url(fonts/brand.woff2) format("woff2"); }'))
    code, out = run("tokens", tmp_path)
    assert code == 1


def test_embedded_font_face_backs_a_cdn_import(run, write, tmp_path):
    write("tokens.css", BASE_CSS)
    write("style-tile.html", tile(
        "font-family: Brand;",
        "@import url('https://fonts.googleapis.com/css2?family=Brand');\n"
        '@font-face { font-family: "Brand"; src: url(data:font/woff2;base64,AAAA) format("woff2"); }'))
    code, out = run("tokens", tmp_path)
    assert code == 0
    assert "self-contained" in out


def test_inline_style_raw_colour_is_caught(run, write, tmp_path):
    write("tokens.css", BASE_CSS)
    write("style-tile.html", tile("", body='<p style="color:#9a9a9a">x</p>'))
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "#9a9a9a" in out


def test_max_width_media_blocks_do_not_leak_into_base(run, write, tmp_path):
    write("tokens.css", ":root { --b-text-size: 1.0625rem; }\n"
                        "@media (max-width: 767px) { :root { --b-text-size: 1rem; } }\n")
    write("tokens.json", '{"b":{"text":{"size":{"$type":"dimension",'
                         '"$value":{"value":1.0625,"unit":"rem"}}}}}')
    code, out = run("tokens", tmp_path)
    assert "mismatch" not in out
    assert code == 0


def test_dark_theme_blocks_that_disagree_fail(run, write, tmp_path):
    write("tokens.css", BASE_CSS +
          '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) '
          "{ --b-color-bg: #000000; } }\n"
          ':root[data-theme="dark"] { --b-color-bg: #111111; }\n')
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "disagree" in out
