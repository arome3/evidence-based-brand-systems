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


def test_quoting_a_forbidden_claim_while_making_it_still_fails(run, write, tmp_path):
    # Quotation clears a forbidden claim only inside a prohibition or labelled
    # research, never when the sentence is making the claim.
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", 'Our "bank-grade" controls, from day one.\n')
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_labelled_research_may_quote_a_competitors_claim(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("02.md", 'Acme hero copy: "bank-grade reconciliation" [OBSERVED 2026-09-01]\n')
    code, out = run("lexicon", tmp_path)
    assert code == 0, out


def test_script_and_data_sources_are_scanned(run, write, tmp_path):
    write("site/forbidden-claims.txt", CLAIMS)
    write("site/src/copy.ts", "export const hero = 'Bank-grade from day one';\n")
    write("site/src/strings.json", '{"hero": "Regulator approved"}\n')
    code, out = run("lexicon", tmp_path / "site")
    assert "copy.ts:1 forbidden claim" in out
    assert "strings.json:1 forbidden claim" in out


def test_all_requires_a_claims_file(run, write, tmp_path):
    write("tokens.css", ":root { --b-c: #000000; --b-p: #ffffff; }\n")
    write("pairs.tsv", "t\t--b-c\t--b-p\tnormal\n")
    code, out = run("all", tmp_path)
    assert code == 1
    assert "forbidden-claims.txt" in out


def test_an_honest_denial_is_not_the_claim(run, write, tmp_path):
    # Stage honesty says what the company is NOT yet; the gate must allow it.
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "Harbourline is not yet regulator-approved.\n\n"
                      "Our controls are not bank-grade, and we say so.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 0, out


def test_a_negation_elsewhere_in_the_line_does_not_clear_it(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "Not a toy: bank-grade from day one.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_an_assumption_label_does_not_clear_a_forbidden_claim(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "[Assumption] Bank-grade reconciliation for every team.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_a_prohibition_word_after_the_quoted_claim_does_not_clear_it(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", 'Our "bank-grade" controls never sleep.\n')
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_not_just_is_an_affirmation_not_a_denial(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "Harbourline is not just bank-grade.\n\nIt isn't merely regulator approved.\n")
    code, out = run("lexicon", tmp_path)
    assert "index.md:1 forbidden claim" in out
    assert "index.md:3 forbidden claim" in out


def test_an_evidence_label_clears_only_quoted_material(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "Harbourline is bank-grade [VERIFIED 2026-09-01].\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_markup_inside_a_phrase_does_not_hide_it(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.html", "<p>Our <em>bank</em>-grade controls</p>\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_a_phrase_wrapped_across_lines_is_caught(run, write, tmp_path):
    write("forbidden-claims.txt", CLAIMS)
    write("index.md", "Reconciliation that is regulator\napproved from day one.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 1


def test_third_party_licence_files_are_not_brand_copy(run, write, tmp_path):
    # A font's OFL.txt says "licensed under" and "partnership with"; it is a
    # third-party legal text shipped beside the fonts, not the brand's voice.
    write("forbidden-claims.txt", "re:\\blicen[cs]ed (by|under)\\b\tno licence held\n")
    write("fonts/brand/OFL.txt", "This Font Software is licensed under the SIL Open Font License.\n")
    write("fonts/brand/LICENSE.md", "Licensed under the Apache License.\n")
    write("01.md", "Reconciliation for finance teams.\n")
    code, out = run("lexicon", tmp_path)
    assert code == 0, out
