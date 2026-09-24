"""The pairing table in 04-brand-guidelines.md is generated, never typed:
a copied ratio goes stale the moment a token moves."""

TOKENS = ":root { --b-ink: #111111; --b-paper: #ffffff; }\n"
PAIRS = "body\t--b-ink\t--b-paper\tnormal\n"
DOC = ("# Guidelines\n\n## Colour pairing\n\n<!-- brandcheck:pairs:start -->\n"
       "<!-- brandcheck:pairs:end -->\n\n## Voice\n")


def test_update_writes_the_computed_table_between_the_markers(run, write, tmp_path):
    write("tokens.css", TOKENS)
    pairs = write("pairs.tsv", PAIRS)
    doc = write("04-brand-guidelines.md", DOC)
    code, out = run("contrast", pairs, "--update", doc)
    assert code == 0, out
    text = doc.read_text()
    assert "| body (light) | `--b-ink` | `--b-paper` | #111111 | #ffffff | 18.88:1 |" in text
    assert text.endswith("## Voice\n")


def test_a_table_left_behind_by_a_token_edit_is_stale(run, write, tmp_path):
    write("tokens.css", TOKENS)
    pairs = write("pairs.tsv", PAIRS)
    doc = write("04-brand-guidelines.md", DOC)
    run("contrast", pairs, "--update", doc)
    write("tokens.css", TOKENS.replace("#111111", "#333333"))
    code, out = run("contrast", pairs, "--check-doc", doc)
    assert code == 1
    assert "stale" in out


def test_all_requires_the_generated_table(run, write, tmp_path):
    write("tokens.css", TOKENS)
    write("pairs.tsv", PAIRS)
    write("04-brand-guidelines.md", "# Guidelines\n\n| body | #111111 | #ffffff | 18.88:1 |\n")
    code, out = run("all", tmp_path, "--no-render")
    assert "brandcheck:pairs" in out
