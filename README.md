# Evidence-Based Brand Systems

A skill for [Claude Code](https://claude.com/claude-code) and compatible agent runtimes that produces **complete, verifiable brand systems** — identity, creative direction, visual system, guidelines, design tokens, and a working style tile — to a standard that survives accessibility, legal and procurement review.

It ships with `brandcheck`, a dependency-light verifier that mechanically checks what most brand work only asserts.

## Why

Brand work fails in two directions, and they are different failures.

**Asserting what nobody checked.** Contrast judged by eye. Fonts trusted from a specimen page. Research written from memory. A checklist ticked because it felt done. This produces a system that breaks under review.

**Documenting a system nobody built.** Guidelines specify seven graphic devices; the artifact ships two. Tokens live in three formats that disagree. This produces a system that reads as plainer and weaker than it was designed to be — and it is why so much brand work feels generic.

This skill closes both.

## Install

```bash
git clone https://github.com/<you>/evidence-based-brand-systems.git \
  ~/.claude/skills/evidence-based-brand-systems
```

Claude Code discovers it automatically. Other runtimes: see their skills directory, or the cross-runtime alias `~/.agents/skills/`.

Optional, for font verification:

```bash
pip install fonttools
```

## Use

Ask for brand work in the ordinary way — *"create a brand identity for…"*, *"we need brand guidelines and design tokens"*, *"audit our brand system"* — and the skill triggers on its own. Or invoke it directly:

```
/evidence-based-brand-systems
```

## What it produces

| File | Contents |
|---|---|
| `01-brand-identity.md` | Purpose, positioning, five personality traits with failure modes, values, voice with rewrite examples, naming and trademark status, taglines, approved descriptions |
| `02-creative-direction.md` | All research with evidence labels, a named taste profile, three distinct creative territories, a scored decision matrix, reference-independence check |
| `03-visual-direction.md` | Every major decision annotated with strategy, territory and reference traceability |
| `04-brand-guidelines.md` | Wordmark in reproducible units, **every colour pairing with its computed ratio**, voice in application, co-branding, prohibited applications |
| `05-design-system.md` | Every component with all states, keyboard and screen-reader behaviour, misuse, and a completed self-review checklist |
| `tokens.css` · `tokens.json` | Three-layer architecture, mechanically diffed against each other |
| `style-tile.html` | Self-contained, no build step, no image assets, both themes, visible focus, reduced motion |
| `pairs.tsv` | Every shipped colour pairing, declared and computed |

## brandcheck

```bash
python3 scripts/brandcheck.py all BRAND_DIR
python3 scripts/brandcheck.py contrast pairs.tsv
python3 scripts/brandcheck.py tokens BRAND_DIR
python3 scripts/brandcheck.py fonts FONT.ttf --glyphs "=≠?→✓" --licence OFL.txt
python3 scripts/brandcheck.py lexicon BRAND_DIR [--strict] [--show-suppressed]
```

Exit code 0 or it does not ship. What it catches:

- **Token drift.** CSS ↔ JSON agreement with `var()` and DTCG `{a.b.c}` references resolved on *both* sides, so aliases are not false mismatches. Handles flat custom properties and DTCG nested groups.
- **Themes disagreeing with themselves.** The `prefers-color-scheme` block and the `[data-theme]` block must define identical values, and the media block must be guarded so an explicit light choice beats a dark OS preference.
- **Contrast, computed and truncated.** WCAG 2.2 requires that ratios are *not* rounded — 4.499:1 fails 4.5:1. Checkers showing one decimal report that as a pass. Warns when the tightest pair has under 5% headroom.
- **Font reality.** Glyph coverage, whether `tnum` exists and is weight-stable, variable axis ranges, and Reserved Font Name status **read from the licence file, not the binary** — because IBM Plex declares an RFN in its `OFL.txt` and carries none in its `name` table.
- **Hype and fabricated proof**, with quoted material, labelled research and prohibition lists suppressed so a correct document scores zero. `--show-suppressed` audits every suppression.

## Iron Laws

1. Compute, never eyeball.
2. Inspect the binary, never the specimen.
3. Build what you specify.
4. One source of truth.
5. Three labels — verified, observed, interpretation — never blended.
6. Invented proof never ships.
7. Stage honesty is strategy.
8. Borrow the method, never the identity.
9. Ship the checks with the system.
10. A checklist item a reviewer can falsify does more damage than the defect it hides.

## Layout

```
SKILL.md                      the pipeline, iron laws, deliverable contract
references/
  pipeline.md                 the seven stages in full
  visual-system.md            colour, type, grid, graphic language, motion
  accessibility.md            thresholds, exemptions, formulas, legal position
  tokens-and-type.md          token architecture, DTCG 2025.10, font verification
  governance.md               brand architecture, co-branding, trademark, handoff
  verification.md             mechanical, rendered and adversarial review
templates/                    scaffolds for every deliverable
scripts/brandcheck.py         the verifier
```

## Scope

This skill governs brand systems. It layers **under** a client's existing brand governance rather than replacing it. Nothing in it is legal advice — trademark and regulated-industry claims route through counsel.

## Licence

MIT. See `LICENSE`.
