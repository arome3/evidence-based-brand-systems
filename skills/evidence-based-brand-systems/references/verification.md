# Verification

Three layers, all required. Mechanical checks catch what a machine can see; the rendered pass catches what only a browser knows; the adversarial review catches what only a hostile reader would notice.

---

## Layer 1 — Mechanical

```bash
python3 scripts/brandcheck.py all BRAND_DIR
python3 scripts/brandcheck.py fonts FONT.ttf --glyphs "…" --licence OFL.txt
```

Exit code 0 or it does not ship. What it verifies:

| Check | Catches |
|---|---|
| CSS ↔ JSON token agreement (references resolved on both sides) | The drift that appears after any edit and is invisible until something looks wrong in one surface only |
| Dark-theme block parity | A page disagreeing with itself about what dark means |
| `var()` resolution across CSS and HTML | A token renamed in one place |
| Raw colour outside token declarations | Component CSS bypassing the system |
| Every declared pairing computed, truncated not rounded | Inaccessible palettes signed off by a checker showing one decimal |
| Headroom warning under 5% | A pair that passes today and breaks on the next colour nudge |
| Font glyph coverage, `tnum`, axes, RFN | Tofu in production; silently non-tabular columns; illegal modification |
| Banned lexicon and unreferenced proof claims | Hype language and fabricated credibility |

**Cannot be checked mechanically, so do not pretend otherwise:** whether the system is differentiated, whether it fits the strategy, whether it is any good.

---

## Layer 2 — Rendered

Open the artifact. Every item is a thing to *do*, not to reason about.

- [ ] **Desktop and mobile widths.** Confirm zero horizontal overflow on the page body; wide content scrolls inside its own container.
- [ ] **Both themes**, via the control and via the system preference, in both directions.
- [ ] **Keyboard focus.** Tab to a control and read the computed outline — width, style, colour, offset, and that `:focus-visible` matches.
- [ ] **Reduced motion.** Confirm the media block exists and lands animations in their finished state.
- [ ] **Webfonts blocked.** Strip the font families and confirm nothing breaks — including that every glyph the UI depends on exists in the *fallback*.
- [ ] **Self-contained.** The artifact opens from disk with no build step and no fetches. A webfont `@import` is only convenience **if the faces are also self-hosted with `@font-face`**; with zero `@font-face` blocks the CDN *is* the typography, and the tile silently loses its type on a locked-down enterprise network or in an offline review. Graceful degradation is necessary but not sufficient — a contract developer implementing from the tile inherits the dependency.
- [ ] **Greyscale.** Every status must remain identifiable without hue.
- [ ] **Zoom to 200%.** Text reflows, nothing is clipped.

**Test design matters.** A badly designed test gives false confidence. Measuring glyph *widths* in a monospace font proves nothing — every glyph including tofu has the same advance width. Rasterise the glyph and compare against a known-missing codepoint instead.

---

## Layer 3 — Adversarial review

Run each pass as if trying to defeat the system. Each has a distinct question.

### Pass 1 — Independence

Put the artifact beside each reference and each competitor. For every device, ask: *would someone who has seen that site recognise this?*

Similarity in one isolated principle is acceptable and unavoidable — hairline rules, mono labels and restrained palettes are shared craft, not anyone's property. **Similarity in the overall identity is theft and reads as such.**

If any section could reasonably be mistaken for a specific reference, name it and change it. Document the check element by element: element, nearest reference, and how this diverges.

### Pass 2 — Skeptical buyer

Read as the actual audience, hostile. Which claim would they test first? What does the artifact ask them to take on faith? For a company without proof, what is *actually* being offered instead — and is it visible in the first screen?

### Pass 3 — Fabrication sweep

Every number, logo, badge, count, screenshot, quote and date: does it trace to something real and dated? Is every specimen visibly labelled as illustrative, adjacent to the content rather than in a page footnote?

**A specimen that could be mistaken for a real finding is a fabrication regardless of intent.** Use bracketed placeholders, zeroed dates and zeroed identifiers so it cannot be misread.

### Pass 4 — Specification-to-artifact

Walk the guidelines and point at where each named device is implemented. This catches Iron Law 3 violations, which are the most common defect in otherwise good brand work and the reason systems read as generic.

### Pass 5 — Handoff

Give it to someone who has read none of the strategy. Can they implement without asking a question? Every question they ask is a gap.

---

## The self-review checklist

Append the completed checklist to the design-system document. **Mark it honestly — a checklist item a reviewer can falsify does more damage than the defect it hides.** Where a claim was verified, state the method.

- [ ] Every deliverable traces to the selected territory; no orphan decisions
- [ ] Three meaningfully distinct territories considered; one selected on a scored matrix
- [ ] Unselected territories documented with reasons, and retained ideas named
- [ ] All research fetched this engagement; nothing from memory
- [ ] Verified / observed / interpretation labelled and never blended
- [ ] No exact value claimed from a rendered screenshot
- [ ] Taste profile carries 2–4 evidence-backed shared qualities
- [ ] Reference conflicts documented and deliberately resolved, not averaged
- [ ] Client constraints override reference aesthetics where they conflict
- [ ] Every commercial reference font replaced with a verified open alternative
- [ ] Every major visual decision carries strategy + territory + reference traceability
- [ ] Every shipped pairing computed and listed; ratios truncated, not rounded
- [ ] Status understandable without colour, and in greyscale
- [ ] Category and AI-cliché scan clean
- [ ] Differentiation from each named competitor documented
- [ ] No fabricated trust element anywhere; unearned slots deleted, not filled
- [ ] Artifact opens with no build step and no image assets
- [ ] Works with webfonts blocked
- [ ] Renders correctly at desktop and mobile; no horizontal page overflow
- [ ] Both themes correct, in both switching directions
- [ ] Keyboard focus visible and measured
- [ ] Reduced motion respected, landing in the finished state
- [ ] Every recommended font has a verified open licence and a direct source link
- [ ] Token formats agree value-for-value, mechanically checked
- [ ] Every device named in the guidelines is implemented in the artifact
- [ ] Specimen content visibly labelled as illustrative
- [ ] A stranger can explain what the company does from the artifact
- [ ] The system can be handed to a contract developer without unresolved questions
- [ ] Open decisions for the owner are listed explicitly
- [ ] Only files inside the agreed output directory were created or modified

## Reporting

State what was verified and how. "Contrast checked" is not a report; "90 of 90 pairings computed, tightest 3.53:1 against a 3.0 requirement" is. Where something was not verified, say so plainly and say why — an honest gap is a finding, a hidden gap is a defect.
