"""A referent must be attached to its claim. A date elsewhere launders nothing."""


def lex(run, tmp_path, *extra):
    return run("lexicon", tmp_path, *extra)


def test_a_date_in_another_paragraph_does_not_clear_a_claim(run, write, tmp_path):
    write("01.md", "# Identity\n\nResearched 2026-08-13.\n\nTrusted by leading teams.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 1
    assert "'trusted by' claim" in out


def test_a_date_in_a_later_paragraph_does_not_clear_a_claim(run, write, tmp_path):
    write("01.md", "Trusted by leading teams.\n\nLast reviewed 2026-08-13.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 1


def test_a_dated_list_item_does_not_clear_its_neighbour(run, write, tmp_path):
    write("01.md", "- Trusted by leading teams\n- Founded 2026-01-04\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 1


def test_a_date_in_the_same_table_row_clears_the_claim(run, write, tmp_path):
    write("01.md", "| Claim | Source |\n|---|---|\n| Trusted by Acme | contract dated 2026-03-02 |\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 0


def test_a_date_in_the_same_wrapped_paragraph_clears_the_claim(run, write, tmp_path):
    write("01.md", "Trusted by Acme Ltd, whose pilot\nagreement is dated 2026-03-02.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 0


def test_a_dated_footnote_clears_the_claim(run, write, tmp_path):
    write("01.md", "Trusted by Acme Ltd.[^1]\n\n[^1]: Pilot agreement dated 2026-03-02.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 0


def test_institution_counts_are_customer_count_claims(run, write, tmp_path):
    write("01.md", "Used by 50+ banks.\n\nChosen by over 200 institutions.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert "01.md:1 customer-count claim" in out
    assert "01.md:3 customer-count claim" in out


def test_performance_percentages_are_metric_claims(run, write, tmp_path):
    write("01.md", "Cuts fraud losses by 40%.\n\n99.2% detection accuracy.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert "01.md:1 performance-metric claim" in out
    assert "01.md:3 performance-metric claim" in out


def test_third_party_endorsement_is_a_claim(run, write, tmp_path):
    write("01.md", "Approved by the central bank.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert "endorsement claim" in out


def test_quoted_and_prohibited_mentions_stay_suppressed(run, write, tmp_path):
    write("04.md", 'Never write "trusted by" or "award-winning".\n\n'
                   "We avoid seamless as a word.\n")
    code, out = lex(run, tmp_path, "--strict")
    assert code == 0
