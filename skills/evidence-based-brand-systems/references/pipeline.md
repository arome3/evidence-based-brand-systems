# The pipeline

Seven stages. Each produces something the next consumes. Skipping a stage does not save time; it moves the cost to review.

---

## 1. GROUND — build the fact base

**Read the project's own documents before writing anything.** Strategy docs, product spec, pricing, positioning, founder answers, any existing copy. If they conflict, establish the source-of-truth order and record it.

Produce a fact base with a row per claim the brand will make, each carrying its source (document path and section, or a URL fetched today). This includes mechanism, audience, commercial terms, stage — not just headline features.

**Record stage honesty explicitly:**

| Field | Why it decides design |
|---|---|
| Customers, publicly nameable | Decides whether a logo slot exists at all |
| Certifications actually held | Decides whether a badge row exists |
| Funding, publicly announced | Decides whether an investor line exists |
| Metrics you can evidence | Decides whether numbers appear |
| Claims forbidden at this stage | Becomes the prohibited-applications list, and `forbidden-claims.txt` |

**Write `forbidden-claims.txt` now**, from that last row and from anything the owner's documents rule out: one claim per line, a TAB, then the reason (`templates/forbidden-claims.txt`). A plain phrase matches however it is spaced or hyphenated; a line starting `re:` is a regular expression. List the rewordings too ("approved by regulators" needs its own `re:` line). `brandcheck lexicon` and `all` fail any hit in any document or page, whatever `--strict` says. Three things clear a hit, and only three: the phrase quoted inside a prohibition (`Never write "bank-grade"`), an evidence label marking someone else's material (`[OBSERVED 2026-09-01]`), and a denial directly before it (`not yet regulator-approved`, which is the stage honesty the brand should state). Quotation marks alone clear nothing; negation elsewhere in the line clears nothing; `[Assumption]` clears nothing. Point `--claims` at the file to gate a landing page kept elsewhere.

**Anything the brand needs that no document answers becomes an open question for the owner.** Never resolve an unknown by inventing something plausible. A flagged gap is a deliverable; a filled gap is a fabrication.

**When the owner's directives conflict** — the stated audience versus the requested tone, demanded proof versus actual stage — write to the documented facts and surface the conflict. Do not silently pick a side.

---

## 2. RESEARCH — four tracks, all fetched

Nothing in this stage comes from memory. If you did not fetch it during this engagement, it does not go in the document.

### Track A — Category conventions

Survey 8–20 brands in the client's category. For each convention, record: what it is, which brands exhibit it (with URLs), and a judgement — **does it still aid comprehension, or is it now undifferentiated noise?**

Do not assume every common convention is bad. Some conventions are load-bearing for buyer comprehension and abandoning them costs clarity for no gain. Say which.

Produce a cliché inventory that separates *dead* conventions (avoiding them earns nothing) from *live* ones (avoiding them is the differentiation).

### Track B — Direct competitors

Fetch each competitor's live site. Record dominant colours (actual values from CSS), typography, hero composition (quote the copy verbatim), graphic motifs, product presentation, CTAs, proof patterns, voice, emotional impression.

End with two lists: **the 5–8 things a visitor would remember** (which the client must not resemble), and **the whitespace the competitor leaves open**.

### Track C — Craft benchmarks

Study 3–4 high-craft systems for **how they build**, never how they look. Token architecture, type-scale construction, spacing, component specification, interaction states, documentation, accessibility, brand-to-product consistency.

Explicitly out of scope: their palettes, typefaces, layouts, gradients, illustrations, component styling, copy patterns, signature devices.

### Track D — Taste references

If the client supplies inspiration sites, review every one. These are taste signals, not templates.

Then do the thing that makes the exercise worth anything: **synthesise them into a named taste profile** with 2–4 genuinely shared qualities, each backed by per-site evidence. A list of ten site reviews is not a taste profile.

Name conflicts between references and resolve each one deliberately. Do not average them into a middle ground — averaging is how you get a brand that looks like everyone.

### Labelling — three classes, never blended

| Label | Means |
|---|---|
| **Verified** | Read directly from the implementation: fetched HTML/CSS/JS, a font binary, an API response. Quote exact values. |
| **Observed** | Seen on the rendered page but not confirmed in the implementation. **Never claim an exact colour value from a screenshot.** |
| **Interpretation** | Your subjective read of the effect or intent. |

If a site blocks inspection, record the limitation precisely, use only what is accessible, invent nothing, and continue.

**Method note:** fetch the raw HTML with a desktop user-agent, then fetch and grep the linked stylesheets and bundles for custom properties, `@font-face` rules, colour values, radii, shadows, gradients, transition durations, easings, container widths and breakpoints. Then load the page in a browser for the rendered pass. Where the two disagree, the implementation wins on values and the render wins on effect.

---

## 3. DIRECT — three territories, one selected

Develop **three meaningfully different** creative territories. Minor visual variations of one idea are not three territories.

Each must respond to both the product strategy and the taste profile. **Where they conflict, strategy wins, and the conflict is named.**

Each territory documents: concept name · central idea · connection to the strategy documents · emotional impression · personality, verbal, colour, typography, layout, graphic-language and product-interface implications · which taste qualities it expresses · which references informed it and **how the influence was transformed** · which reference tendencies it rejects · one principal strength · one principal risk · how it avoids category clichés · how it differs from each named competitor · why it is recognisably *this client* · why it could not be mistaken for any single reference.

**Select with a scored matrix.** Score every territory against: strategy fit, truth expression, audience credibility, differentiation, memorability, taste alignment, practicality, accessibility, extensibility, product-interface compatibility, ability to communicate the product's core mechanism, fit for the company's stage, independence from competitors and references.

**Weight the criteria, and never weight taste alignment above strategy fit, audience credibility, truth, differentiation, accessibility, or practicality.**

Document the unselected territories with reasons — and note which idea from each is being *retained* inside the winner. Good ideas from rejected territories are usually salvageable as devices.

---

## 4. SPECIFY — the visual system

Every major decision carries this annotation:

> **Decision** — what the brand does.
> **Strategy** — the reason, grounded in the client's own documents or audience.
> **Territory** — the principle from the selected territory it expresses.
> **Reference influence** — the reference that informed it, or "none".
> **Adaptation** — what was learned, and how this treatment stays distinct.

Apply it to palette, typography, grid, spacing, graphic language, texture, iconography, data presentation, motion, and both themes.

**"Reference influence: none" is a legitimate and common answer.** Do not attach a reference to a decision where no genuine influence exists — a fabricated lineage is as dishonest as a fabricated metric.

Detail: `visual-system.md`.

---

## 5. BUILD — tokens and artifact

**Iron Law 3 lives here: build what you specify.** The most common failure in brand work is a guidelines document describing seven graphic devices next to an artifact that renders two. The result reads as plainer and weaker than the system actually is, and every reviewer blames the design rather than the build.

Before leaving this stage, list every device named in stage 4 and point at where it is implemented. Anything unimplemented is either built now or struck from the specification.

- **Tokens:** author `tokens.css`, then generate `tokens.json` with `python3 scripts/brandcheck.py export BRAND_DIR`. Re-export after every edit; never type the JSON. The dark block remaps every semantic colour token, not just the page ground. See `tokens-and-type.md`.
- **Pairs:** every row of `pairs.tsv` names its tokens (`--b-color-text-primary`), so it is resolved fresh on every run, in both themes unless a fifth column says `light` or `dark`. Every surface a colour can sit on gets its own row.
- **Style tile:** self-contained (fonts embedded as `data:` URIs), no build step, no image files, both themes, visible focus, reduced-motion respected, every specified device rendered, all specimen content visibly labelled. The wordmark and mark appear as inline SVG coloured by CSS classes that read tokens. Mark a logotype or decorative element `data-contrast-exempt="reason"`.
- **Assets:** the wordmark, mark, icon set, avatar and share card, built with `scripts/brandassets.py`, icon colours given as token names. See `assets.md`.
- **Scripts and fonts:** copy `brandcheck.py` and `brandassets.py` into `BRAND_DIR/scripts/`, and put the font files with their licence in `BRAND_DIR/fonts/`.

---

## 6. VERIFY — mechanical, then rendered, then adversarial

Run the stage 6 sequence in SKILL.md's Verify section exactly: `export`, `all` (with `--strict` for a company with no public proof), and `sheet`. `all` includes the rendered layer and the asset checks, and fails if it could not render. Then do what no command can: review `asset-sheet.html` by eye, work through the manual items in `verification.md` Layer 2, and run the adversarial review.

Full protocol: `verification.md`.

---

## 7. GOVERN — make it usable by people who were not here

Application rules, co-branding posture, trademark handling, brand architecture, localisation, and the handoff. A system a contract developer cannot implement without asking questions is not finished.

The handoff includes the gates. Every page built from the system, the landing page first, runs the brand's forbidden claims and rendered check: `brandcheck lexicon SITE_DIR --claims BRAND_DIR/forbidden-claims.txt --strict` and `brandcheck render <served URL> --pairs BRAND_DIR/pairs.tsv`.

Detail: `governance.md`.
