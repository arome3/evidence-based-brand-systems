---
name: evidence-based-brand-systems
description: Use when creating, overhauling, or auditing a brand identity, visual identity, design language, brand book, brand guidelines, design tokens, or style guide for any company or product; when a brand system must survive accessibility, legal, procurement, or trademark review; when a pre-launch or zero-customer company needs credibility without fabricated proof; or when brand documentation has drifted from what was actually built.
---

# Evidence-Based Brand Systems

## Overview

A brand system is a set of claims: about what a company is, how its surfaces look, how they behave, and how they may be used. **Every one of those claims is either verified or it is decoration.**

Brand work fails in two directions, and they are not the same failure:

1. **Asserting what nobody checked.** Contrast judged by eye. Fonts trusted from a specimen page. Research written from memory. A checklist ticked because it felt done.
2. **Documenting a system nobody built.** Guidelines specify seven graphic devices; the artifact ships two. Tokens exist in three formats that disagree. The style tile renders nothing the strategy asked for.

The first produces a system that breaks under review. The second produces a system that reads as plainer and weaker than it was designed to be — and it is the failure that makes brand work feel generic.

This skill closes both: a pipeline that grounds every decision in the project's own documents and in fetched evidence, and a verifier that mechanically checks what a machine can check.

## The pipeline

Copy this into your working notes and check items off. Do not skip stages — stage 4 is worthless without stage 2, and stage 6 is what makes any of it defensible.

```
[ ] 1. GROUND    — the project's own documents; fact base; stage honesty
[ ] 2. RESEARCH  — category, competitors, craft benchmarks, references (all fetched)
[ ] 3. DIRECT    — 3 distinct territories, scored matrix, one selected
[ ] 4. SPECIFY   — visual system, every decision traced to strategy + territory
[ ] 5. BUILD     — tokens + style tile; every specified device implemented
[ ] 6. VERIFY    — brandcheck passes; rendered checks pass; adversarial review passes
[ ] 7. GOVERN    — application rules, co-branding, trademark, handoff
```

Full protocol for each stage: `references/pipeline.md`.

## Iron Laws

Individually citable. Quote them by number in review.

1. **Compute, never eyeball.** Every foreground/background pairing that ships is declared in `pairs.tsv` and computed. An undeclared pairing is an unverified pairing.
2. **Inspect the binary, never the specimen.** Font claims — glyph coverage, tabular figures, axes, licence — come from the actual file via `fontTools`, not from a foundry page.
3. **Build what you specify.** A device named in the guidelines and absent from the artifact is a defect in both. Specification and implementation ship together or neither ships.
4. **One source of truth.** Tokens live in exactly one authored format. Every other format is generated from it and mechanically diffed against it.
5. **Three labels, never blended.** *Verified* (read from the implementation), *observed* (seen rendered, not confirmed), *interpretation* (your judgement). Mixing them is how taste gets laundered into fact.
6. **Invented proof never ships.** No customer logos, badges, counts, awards, testimonials, analyst marks, or screenshots-as-production the company has not earned. Not as placeholders. Not "for the pitch".
7. **Stage honesty is strategy.** State plainly what proof does not yet exist. For a zero-customer company, the slot is *deleted*, not filled with something weaker.
8. **Borrow the method, never the identity.** Reference brands are studied for how they build, not for how they look. Similarity in one principle is fine; similarity in the overall identity is theft and reads as such.
9. **Ship the checks with the system.** The verifier and the declared pairings are deliverables. A system nobody can re-verify decays on first edit.
10. **A checklist item a reviewer can falsify does more damage than the defect it hides.**

## What the deliverable IS

Not a prohibition list — a contract. The output is these files, and each has required contents:

| File | Must contain |
|---|---|
| `01-brand-identity.md` | Assumptions (at top) · purpose, promise, positioning · audience · what it is / is not · personality traits with failure modes · values with observable behaviour · voice with rewrite examples · naming, pronunciation, trademark status · taglines · approved descriptions |
| `02-creative-direction.md` | All research with labels and dates · ≥3 distinct territories · scored decision matrix · selected territory + written rationale · rejected territories with reasons · competitor differentiation check · reference-independence check |
| `03-visual-direction.md` | Every major decision annotated: **Decision / Strategy / Territory / Reference influence / Adaptation** · colour with usage + prohibited usage + pairing · type scale as quads · spacing, grid, imagery, iconography, motion |
| `04-brand-guidelines.md` | Wordmark construction in reproducible units · **every pairing with its computed ratio** · voice in application (buttons, errors, empty states) · brand applications · co-branding · prohibited applications |
| `05-design-system.md` | Foundations · every component with all states, keyboard, screen-reader, misuse · completed self-review checklist |
| `tokens.css` | Three layers: core → semantic → component. Themes by semantic remap only |
| `tokens.json` | Generated mirror. Must agree value-for-value |
| `style-tile.html` | Self-contained (fonts self-hosted, not CDN-dependent), no build, no image assets, both themes, visible focus, reduced-motion, every specified device rendered |
| `pairs.tsv` | Every shipped pairing: `name<TAB>fg<TAB>bg<TAB>threshold` |

Templates for all of these: `templates/`.

## Verify

```bash
python3 scripts/brandcheck.py all BRAND_DIR      # tokens + contrast + lexicon
python3 scripts/brandcheck.py fonts FONT.ttf --glyphs "=≠?→✓" --licence OFL.txt
```

Exit code 0 or it does not ship. `brandcheck` covers what is mechanical. What it cannot judge — differentiation, strategic fit, whether the thing is any good — is the adversarial review in `references/verification.md`. Both are required.

## Rationalizations — every one means stop

| Excuse | Reality |
|---|---|
| "That contrast obviously passes" | Then computing it costs five seconds. #7a4a00 on #f1e9d9 looks marginal and passes at 6.19; #ffffff on #ff0000 looks fine and fails at 3.99. |
| "The font's specimen page shows a checkmark" | Specimen pages show the foundry's full character set, not your subset. Public Sans has no U+2713. Inspect the binary. |
| "I'll add the diagram later; the tokens are the important part" | The device you skip is the one that made the system distinctive. Later never arrives, and the guidelines now describe fiction. |
| "The client explicitly asked for the logo wall" | The client asked you to expose them to a false-advertising claim. Offer the honest alternative; do not ship the fabrication. |
| "It's a placeholder, we'll swap in real logos" | Placeholders ship. Every time. |
| "Three token formats is more useful for the team" | Three formats is three chances to disagree. One authored, the rest generated. |
| "This reference site is exactly right for them" | Then you have designed that company's brand, not this one's. Take the method. |
| "Accessibility can be a fast-follow" | It is a legal requirement in the EU (EAA, June 2025) and under ADA Title II. It is also ten times cheaper before the palette is signed off. |
| "I reviewed it carefully" | Reviewing is not measuring. Run the checks. |
| "The strategy documents don't say, so I'll use my judgement" | Unknowns are flagged as open decisions for the owner, never filled with something plausible. |

## Red flags — stop and re-ground

- A ratio in your documentation you did not compute this session
- A font fact you did not read out of the file
- A device in the guidelines you cannot point to in the artifact
- A second token format edited by hand
- A number, logo, badge or count with no dated referent
- A palette that resembles the reference you studied most recently
- A checklist item you are about to tick that a reviewer could falsify
- The words "obviously", "clearly", or "should be fine" attached to a measurable claim

## Reference routing

| Read | When |
|---|---|
| `references/pipeline.md` | Before starting. The full protocol for all seven stages, including how to research sites and label evidence, and how to develop and score territories |
| `references/visual-system.md` | Stage 4. Colour, themes, typography, grid, plates, graphic language, texture, imagery, data, motion |
| `references/accessibility.md` | Stages 4–6. Thresholds, exemptions, the anti-rounding rule, the formulas, the legal position |
| `references/tokens-and-type.md` | Stage 5. Three-tier architecture, naming, theming, DTCG 2025.10, font verification and licensing |
| `references/governance.md` | Stage 7. Brand architecture, co-branding, trademark, regulated review, localisation, handoff |
| `references/verification.md` | Stage 6. Mechanical, rendered and adversarial review, plus the self-review checklist |

Templates for every deliverable are in `templates/`. Start from them; they carry the required structure.

This skill governs brand systems. It layers under a client's existing brand governance rather than replacing it, and nothing in it is legal advice — trademark and regulated-industry claims route through counsel.
