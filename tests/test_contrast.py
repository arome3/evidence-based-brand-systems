"""Contrast is computed, never eyeballed, and never flattered."""


def test_translucent_foreground_is_composited_over_its_ground(run, write):
    # White at 40% on a near-black ground renders as a mid-grey: about 3.80:1.
    # Ignoring alpha scores it as opaque white, 19.15:1, a false pass.
    pairs = write("pairs.tsv", "meta\t#ffffff66\t#07110f\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "3.80:1" in out
    assert "19.15" not in out


def test_translucent_foreground_that_passes_reports_the_composited_ratio(run, write):
    pairs = write("pairs.tsv", "meta\t#ffffff73\t#07110f\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 0
    assert "4.53:1" in out


def test_translucent_background_is_refused(run, write):
    # What sits under a translucent ground is unknown, so no ratio is honest.
    pairs = write("pairs.tsv", "x\t#000000\t#ffffff80\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "opaque" in out


def test_css_colour_functions_are_parsed(bc):
    assert bc.parse_colour("#fff") == (255.0, 255.0, 255.0, 1.0)
    assert bc.parse_colour("rgb(255 0 0 / 50%)") == (255.0, 0.0, 0.0, 0.5)
    assert bc.parse_colour("rgba(0, 128, 255, 0.25)") == (0.0, 128.0, 255.0, 0.25)
    assert bc.parse_colour("hsl(0 100% 50%)") == (255.0, 0.0, 0.0, 1.0)
    r, g, b, a = bc.parse_colour("oklch(0.6279554 0.2576833 29.2338851)")
    assert (round(r), round(g), round(b), a) == (255, 0, 0, 1.0)


def test_ratio_is_truncated_not_rounded(bc):
    assert bc.fmt_ratio(4.4999) == "4.49"
