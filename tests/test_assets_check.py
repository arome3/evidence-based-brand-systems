"""`brandcheck assets`: the logo and icon files the guidelines specify exist,
and are built correctly. Iron Law 3: build what you specify."""
import json

from imgutil import centred, ico, solid_png, valid_assets


def test_a_complete_asset_set_passes(run, tmp_path):
    valid_assets(tmp_path)
    code, out = run("assets", tmp_path)
    assert code == 0, out


def test_a_missing_asset_directory_fails(run, tmp_path):
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "assets" in out


def test_a_logo_with_live_text_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "wordmark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                    '<text x="0" y="9">brand</text></svg>')
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "live text" in out


def test_a_logo_that_embeds_or_links_an_image_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" '
                                'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10">'
                                '<image xlink:href="mark.png" width="10" height="10"/></svg>')
    code, out = run("assets", tmp_path)
    assert code == 1


def test_a_logo_without_a_viewbox_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                                '<path d="M0 0h10v10H0z"/></svg>')
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "viewBox" in out


def test_a_wordmark_without_construction_metadata_is_warned(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "wordmark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                    '<path d="M0 0h10v10H0z"/></svg>')
    code, out = run("assets", tmp_path)
    assert "construction" in out


def test_a_wrongly_sized_icon_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "icon-192.png").write_bytes(solid_png(190, 190))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "192" in out


def test_a_translucent_apple_touch_icon_fails(run, tmp_path):
    # iOS paints transparency black, so the icon must carry its own ground.
    a = valid_assets(tmp_path)
    (a / "apple-touch-icon.png").write_bytes(solid_png(180, 180, (7, 17, 15, 0)))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "opaque" in out


def test_a_maskable_icon_that_leaves_the_safe_zone_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "icon-mask.png").write_bytes(centred(512, 200))  # corners of the square leave r=204.8
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "safe zone" in out


def test_an_avatar_that_the_circle_crop_would_cut_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "avatar.png").write_bytes(centred(400, 190))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "avatar" in out


def test_a_favicon_without_a_32px_image_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "favicon.ico").write_bytes(ico([(16, solid_png(16, 16))]))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "32" in out


def test_a_manifest_without_a_maskable_icon_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    m = json.loads((a / "manifest.webmanifest").read_text())
    m["icons"] = [i for i in m["icons"] if i.get("purpose") != "maskable"]
    (a / "manifest.webmanifest").write_text(json.dumps(m))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "maskable" in out


def test_a_manifest_pointing_at_a_missing_file_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "icon-192.png").unlink()
    code, out = run("assets", tmp_path)
    assert code == 1


def test_an_og_image_of_the_wrong_size_fails(run, tmp_path):
    a = valid_assets(tmp_path)
    (a / "og-default.png").write_bytes(solid_png(1200, 600))
    code, out = run("assets", tmp_path)
    assert code == 1
    assert "1200" in out


def test_all_requires_the_asset_set(run, write, tmp_path):
    write("tokens.css", ":root { --b-ink: #111111; --b-paper: #ffffff; }\n")
    write("pairs.tsv", "body\t--b-ink\t--b-paper\tnormal\n")
    code, out = run("all", tmp_path)
    assert code == 1
    assert "ASSETS" in out
