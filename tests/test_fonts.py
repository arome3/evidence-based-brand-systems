"""Reserved Font Name status comes from the licence's copyright lines only.

Every OFL licence also DEFINES the term "Reserved Font Name" in its body text.
Matching that definition reports a reserved name for fonts that have none.
"""
import pytest

from conftest import FIXTURES

LIC = FIXTURES / "licences"


@pytest.mark.parametrize("licence", ["inter-LICENSE.txt", "dm-sans-OFL.txt"])
def test_fonts_without_a_reserved_name_are_not_flagged(run, fixture_font, licence):
    code, out = run("fonts", fixture_font, "--glyphs", "AV", "--licence", LIC / licence)
    assert "no Reserved Font Name declared" in out
    assert "refers to any names" not in out


@pytest.mark.parametrize("licence,name", [
    ("ibm-plex-LICENSE.txt", "Plex"),
    ("lato-OFL.txt", "Lato"),
    ("source-sans-LICENSE.md", "Source"),
])
def test_reserved_names_are_read_from_copyright_lines(run, fixture_font, licence, name):
    code, out = run("fonts", fixture_font, "--glyphs", "AV", "--licence", LIC / licence)
    assert f'Reserved Font Name "{name}"' in out
