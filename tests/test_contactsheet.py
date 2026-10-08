"""contactsheet: many images on a few sheets, numbered, within a height cap."""
import pytest

PIL = pytest.importorskip("PIL", reason="contactsheet needs Pillow")
from PIL import Image  # noqa: E402


def make(d, name, size=(300, 300), colour=(200, 30, 30)):
    d.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(d / name)
    return d / name


def sheets(d, prefix="sheet"):
    return sorted(p.name for p in d.glob(f"{prefix}[0-9]*.jpg"))


def test_thumbnail_sheets_fill_rows_to_the_height_cap(cs, cli, tmp_path):
    src = tmp_path / "in"
    for i in range(1, 41):
        make(src, f"img{i}.png", (300 + i * 7, 200 + i * 5))
    code, out = cli(cs, src, "--out", tmp_path / "out" / "sheet", "--cols", "6", "--numbered")
    assert code == 0, out
    names = sheets(tmp_path / "out")
    # 6 rows of 6 fit in 2000px (10 + 6 * 310 = 1870), so 40 images make two sheets.
    assert names == ["sheet0.jpg", "sheet1.jpg"]
    with Image.open(tmp_path / "out" / "sheet0.jpg") as im:
        assert im.size == (6 * 300 + 7 * 10, 10 + 6 * 310)
    with Image.open(tmp_path / "out" / "sheet1.jpg") as im:
        assert im.height == 10 + 310 and im.height <= 2000
    assert "40 image(s) on 2 sheet(s)" in out


def test_numbered_cells_carry_a_label_and_plain_ones_do_not(cs, tmp_path):
    src = tmp_path / "in"
    paths = [make(src, f"{i}.png") for i in range(1, 4)]
    numbered, _ = cs.build_sheets(paths, tmp_path / "n", cols=6, numbered=True)
    plain, _ = cs.build_sheets(paths, tmp_path / "p", cols=6, numbered=False)
    with Image.open(numbered[0]) as a, Image.open(plain[0]) as b:
        corner = (10 + 3, 10 + 3)                   # inside the first cell's label box
        assert max(a.convert("RGB").getpixel(corner)) < 60
        r, g, _ = b.convert("RGB").getpixel(corner)
        assert r > 150 and g < 90


def test_labels_follow_natural_filename_order(cs, tmp_path):
    src = tmp_path / "in"
    for name in ("10.png", "2.png", "1.png"):
        make(src, name)
    assert [p.name for p in cs.collect([src])] == ["1.png", "2.png", "10.png"]


def test_explicit_labels_are_used(cs, tmp_path, monkeypatch):
    drawn = []
    monkeypatch.setattr(cs, "_label", lambda draw, xy, text, font: drawn.append(text))
    paths = [make(tmp_path / "in", f"{i}.png") for i in range(3)]
    cs.build_sheets(paths, tmp_path / "s", cols=6, numbered=True, labels=[7, 23, 41])
    assert drawn == ["7", "23", "41"]


def test_two_columns_keep_aspect_and_cap_the_sheet_height(cs, cli, tmp_path):
    src = tmp_path / "in"
    for i in range(4):
        make(src, f"tall{i}.png", (700, 3000))       # each cut at 1400px in its cell
    make(src, "wide.png", (1400, 700))               # 700x350 in its cell
    code, out = cli(cs, src, "--out", tmp_path / "s", "--numbered")
    assert code == 0, out
    names = sheets(tmp_path, "s")
    # Rows of 1400, 1400 and 350: the second tall row and the wide one share a sheet.
    assert names == ["s0.jpg", "s1.jpg"]
    for n in names:
        with Image.open(tmp_path / n) as im:
            assert im.width == 2 * 700 + 3 * 10
            assert im.height <= 2000
    with Image.open(tmp_path / "s1.jpg") as im:
        assert im.height == 10 + 1400 + 10 + 350 + 10


def test_a_shorter_run_removes_stale_sheets(cs, cli, tmp_path):
    src = tmp_path / "in"
    for i in range(40):
        make(src, f"{i}.png")
    cli(cs, src, "--out", tmp_path / "sheet", "--cols", "6")
    assert sheets(tmp_path) == ["sheet0.jpg", "sheet1.jpg"]
    for i in range(5, 40):
        (src / f"{i}.png").unlink()
    cli(cs, src, "--out", tmp_path / "sheet", "--cols", "6")
    assert sheets(tmp_path) == ["sheet0.jpg"]


def test_sheets_in_the_input_directory_are_not_fed_back_in(cs, cli, tmp_path):
    for i in range(3):
        make(tmp_path, f"{i:02d}.jpg")
    cli(cs, tmp_path, "--out", tmp_path / "sheet")
    code, out = cli(cs, tmp_path, "--out", tmp_path / "sheet")
    assert code == 0 and "3 image(s) on 1 sheet(s)" in out


def test_an_unreadable_file_is_skipped_with_a_warning(cs, cli, tmp_path):
    make(tmp_path / "in", "a.png")
    (tmp_path / "in" / "b.jpg").write_text("not an image")
    code, out = cli(cs, tmp_path / "in", "--out", tmp_path / "s")
    assert code == 0
    assert "WARN" in out and "b.jpg" in out
    assert "1 image(s) on 1 sheet(s)" in out


def test_no_images_fails(cs, cli, tmp_path):
    (tmp_path / "in").mkdir()
    code, out = cli(cs, tmp_path / "in", "--out", tmp_path / "s")
    assert code == 1 and "no images" in out


def test_transparent_and_rotated_images_are_handled(cs, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    Image.new("RGBA", (300, 300), (0, 0, 0, 0)).save(src / "clear.png")
    im = Image.new("RGB", (400, 200), (0, 0, 255))
    exif = Image.Exif()
    exif[274] = 6                                    # rotate 90 on display
    im.save(src / "rot.jpg", exif=exif)
    out, skipped = cs.build_sheets(cs.collect([src]), tmp_path / "s", cols=2)
    assert not skipped and len(out) == 1
    with Image.open(out[0]) as sheet:
        # rot.jpg displays 200x400, so at 700px wide its cell is 1400 tall.
        assert sheet.height == 10 + 1400 + 10
