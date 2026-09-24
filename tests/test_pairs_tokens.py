"""pairs.tsv names tokens, so a pairing can never verify a stale copy."""

TOKENS = """
:root {
  --b-core-ink: #111111; --b-core-paper: #ffffff; --b-core-night: #000000;
  --b-core-fog: #eeeeee;
  --b-color-text: var(--b-core-ink);
  --b-color-bg: var(--b-core-paper);
  --b-color-bg-surface: var(--b-core-paper);
  --b-color-text-meta: rgb(17 17 17 / 0.4);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --b-color-text: var(--b-core-fog); --b-color-bg: var(--b-core-night); }
}
:root[data-theme="dark"] { --b-color-text: var(--b-core-fog); --b-color-bg: var(--b-core-night); }
"""


def setup(write, rows, tokens=TOKENS):
    write("tokens.css", tokens)
    return write("pairs.tsv", rows)


def test_token_rows_are_checked_in_both_themes_by_default(run, write):
    pairs = setup(write, "body\t--b-color-text\t--b-color-bg\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 0, out
    assert "body (light)" in out and "body (dark)" in out


def test_var_syntax_and_an_explicit_theme_are_accepted(run, write):
    pairs = setup(write, "body\tvar(--b-color-text)\tvar(--b-color-bg)\tnormal\tdark\n")
    code, out = run("contrast", pairs)
    assert code == 0, out
    assert "body (dark)" in out and "body (light)" not in out


def test_a_token_edit_is_seen_immediately(run, write):
    pairs = setup(write, "body\t--b-color-text\t--b-color-bg\tnormal\tdark\n",
                  TOKENS.replace("--b-core-fog: #eeeeee", "--b-core-fog: #333333"))
    code, out = run("contrast", pairs)
    assert code == 1


def test_a_surface_the_dark_theme_forgot_to_remap_fails(run, write):
    # Dark text on the surface token, which the dark block never remapped:
    # light text on white. The template shipped exactly this gap.
    pairs = setup(write, "text on surface\t--b-color-text\t--b-color-bg-surface\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "text on surface (dark)" in out


def test_translucent_tokens_are_composited(run, write):
    pairs = setup(write, "meta\t--b-color-text-meta\t--b-color-bg\tnormal\tlight\n")
    code, out = run("contrast", pairs)
    assert "composited" in out


def test_an_unknown_token_fails(run, write):
    pairs = setup(write, "x\t--b-color-nope\t--b-color-bg\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "unknown token" in out


def test_a_hex_that_matches_no_token_is_a_stale_copy(run, write):
    pairs = setup(write, "x\t#121212\t#ffffff\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "matches no token" in out


def test_a_hex_that_matches_a_token_is_accepted(run, write):
    pairs = setup(write, "x\t#111111\t#ffffff\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 0, out


def test_token_rows_without_a_token_file_fail(run, write):
    pairs = write("pairs.tsv", "x\t--b-color-text\t--b-color-bg\tnormal\n")
    code, out = run("contrast", pairs)
    assert code == 1
    assert "tokens.css" in out


def test_tokens_can_live_elsewhere(run, write, tmp_path):
    write("brand/tokens.css", TOKENS)
    pairs = write("elsewhere/pairs.tsv", "body\t--b-color-text\t--b-color-bg\tnormal\n")
    code, out = run("contrast", pairs, "--tokens", tmp_path / "brand" / "tokens.css")
    assert code == 0, out
