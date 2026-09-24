"""Stage 1's forbidden claims become a mechanical gate, not a list in a doc."""

CLAIMS = ("# Claims this company may not make at its stage\n"
          "bank-grade\tno independent security assessment exists\n"
          "re:\\bregulator[- ]approved\\b\tno regulator has approved anything\n")


def test_a_forbidden_claim_fails_without_strict(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("01.md", "Bank-grade reconciliation for finance teams.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1
    assert "forbidden claim" in out
    assert "no independent security assessment exists" in out


def test_spacing_and_hyphenation_variants_match(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("01.md", "Bank grade controls.\n\nBank‑grade controls.\n")
    code, out = run("lexicon", tmp_path)
    assert "01.md:1 forbidden claim" in out
    assert "01.md:3 forbidden claim" in out


def test_negation_words_and_dates_do_not_clear_a_forbidden_claim(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("01.md", "Bank-grade controls, audit pending as of 2026-09-01.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_quoting_a_forbidden_claim_in_a_prohibition_is_allowed(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("04.md", 'Never describe the product as "bank-grade" or "regulator-approved".\n')
    code, out = run("lexicon", tmp_path)
    assert code == 0, out


def test_regex_entries_match(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("01.md", "Regulator approved from day one.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_brand_claims_apply_to_a_landing_page_elsewhere(run, write, tmp_path):
    write("brand/forbidden-claims.txt", CLAIMS)
    write("site/src/pages/index.tsx", "export default () => <h1>Bank-grade by default</h1>;\n")
    code, out = run("lexicon", tmp_path / "site", "--claims",
                    tmp_path / "brand" / "forbidden-claims.txt")
    assert code == 1
    assert "index.tsx:1 forbidden claim" in out


def test_the_claims_file_itself_is_not_scanned(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("01.md", "Reconciliation for finance teams.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 0, out
    assert "none of the 2 forbidden claim(s)" in out


def test_all_picks_up_the_claims_file(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("tokens.css", ":root { --b-c: #000000; --b-p: #ffffff; }\n")
    write("pairs.tsv", "t\t--b-c\t--b-p\tnormal\n")
    write("01.md", "Bank-grade.\n")
    code, out = run("all", tmp_path)
    assert "forbidden claim" in out
