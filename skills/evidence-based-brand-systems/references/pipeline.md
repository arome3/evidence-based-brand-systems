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

**Write `forbidden-claims.txt` now**, from that last row and from anything the owner's documents rule out: one claim per line, a TAB, then the reason (`templates/forbidden-claims.txt`). A plain phrase matches however it is spaced or hyphenated; a line starting `re:` is a regular expression. List the rewordings too ("approved by regulators" needs its own `re:` line). `brandcheck lexicon` and `all` fail any hit in any document or page, whatever `--strict` says. Matching runs on each paragraph, list item or table row with markup stripped, so `<em>bank</em>-grade` and a phrase wrapped across lines are still caught. Three things clear a hit, only within its own sentence, and nothing else: the phrase quoted after a prohibition (`Never write "bank-grade"`), the phrase quoted with an evidence label marking someone else's copy (`Acme: "bank-grade" [OBSERVED 2026-09-01]`), and a plain denial directly before it (`not yet regulator-approved`, the stage honesty the brand should state; `not just bank-grade` is an affirmation and fails). Quotation marks alone clear nothing; a prohibition word after the phrase clears nothing; an unquoted label, `[Assumption]` included, clears nothing. Point `--claims` at the file to gate a landing page kept elsewhere.

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

If the client supplies inspiration (sites, Behance or Dribbble projects, screenshots), capture every one with `scripts/refcapture.py` and **look at every image yourself** (Iron Law 12). If the client supplies none, ask for two to six before stage 3; a brand chosen without any taste signal is chosen against yours. These references are the owner's standard for the look: their qualities, energy and level of craft. They are not templates to copy.

Look specifically for what makes them feel *made*: the imagery layer (photography, characters, 3D, illustration) and its treatment, the mark and how it is constructed, the signature device you would recognise with the logo covered, how colour is used at scale, and how the brand is shown on real things.

Then do the thing that makes the exercise worth anything: **synthesise them into a named taste profile** with 2–4 genuinely shared qualities, each backed by per-site evidence. A list of ten site reviews is not a taste profile.

Name conflicts between references and resolve each one deliberately. Do not average them into a middle ground — averaging is how you get a brand that looks like everyone.

**Taste versus strategy.** Where a reference's *look* conflicts with a strategy fact about claims, proof, audience reach or page weight, strategy decides that fact (no invented proof, no 9 MB hero video for buyers on mobile data) and the look is kept by other means. Where the conflict is only aesthetic (restraint versus energy, photography versus none, gradient versus flat), the owner's references win.

### Distinctive assets

Name which assets the brand will own and repeat beside its name for years: a shape (mark, frame, crop), a colour, a character, a sound, a phrase. A new brand has no fame, so pick assets nobody in the category uses (check against Track A and B) and lead with a **shape**: shapes earn recognition faster than colours. For a product that speaks (voice assistants, phone services), sound is an asset: a fixed greeting, a confirmation phrase, a short chime that survives a phone line.

### Labelling — three classes, never blended

| Label | Means |
|---|---|
| **Verified** | Read directly from the implementation: fetched HTML/CSS/JS, a font binary, an API response. Quote exact values. |
| **Observed** | Seen on the rendered page but not confirmed in the implementation. **Never claim an exact colour value from a screenshot.** |
| **Interpretation** | Your subjective read of the effect or intent. |

If a site blocks inspection, record the limitation precisely, use only what is accessible, invent nothing, and continue.

**Method note:** fetch the raw HTML with a desktop user-agent, then fetch and grep the linked stylesheets and bundles for custom properties, `@font-face` rules, colour values, radii, shadows, gradients, transition durations, easings, container widths and breakpoints. Then load the page in a browser for the rendered pass. Where the two disagree, the implementation wins on values and the render wins on effect.

---

## 3. EXPLORE — boards, then the owner picks

Develop **three territories that differ in kind** (imagery mode, colour mode, mark mode), each grounded in a strategy truth and judged against the owner's references. Present each as a **rendered board of six 16:9 slides** with real imagery, a mark from the mark lab, a signature device and real applications. Full protocol: `visual-exploration.md`; imagery: `imagery.md`.

For each territory, write a short block in `02-creative-direction.md`: the central idea and the strategy truth it comes from · what the mark means · the imagery mode and treatment · the signature device · which reference qualities it carries and how they were transformed · principal strength · principal risk · how it differs from each named competitor.

**The owner decides by eye**, and may mix ("this mark with that photography"). Record the pick in their words. A scored matrix may be kept as a record of trade-offs; it says who scored it, and it never overrides the owner's choice.

Document the unselected territories with reasons, and the ideas from each that are retained inside the winner.

If the owner rejects all three, write the rejection diagnosis (`visual-exploration.md`) before making anything new.

---

## 4. SPECIFY — the visual system for the picked board

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
- **Scripts and fonts:** copy `brandcheck.py` and `brandassets.py` into `BRAND_DIR/scripts/`, and put each family in `BRAND_DIR/fonts/<family>/` with its own licence file; every face is checked against the licence beside it.
- **Imagery:** the chosen mode and treatment applied to every image the system uses; every file logged in `SOURCES.tsv`, stand-ins marked as stand-ins (`imagery.md`). The style tile stays image-free; the imagery lives in the deck and the applications.
- **Guidelines deck:** `guidelines-deck.html`, the owner-facing brand book in the board's visual language, built from the same tokens, fonts and assets, rendered to PNG, checked with `boardcheck` and looked at slide by slide.
- **Guidelines pairing table:** put the `<!-- brandcheck:pairs:start -->` / `<!-- brandcheck:pairs:end -->` markers in `04-brand-guidelines.md` and fill them with `brandcheck contrast pairs.tsv --update 04-brand-guidelines.md`. A ratio typed into the guidelines goes stale on the next token edit; `all` fails a stale table.

---

## 6. VERIFY — mechanical, then rendered, then adversarial

Run the stage 6 sequence in SKILL.md's Verify section exactly: `export`, `contrast --update`, `sheet`, then `all` (with `--strict` for a company with no public proof). `all` includes the rendered layer and the asset checks, and fails if it could not render. Run `boardcheck` on the boards and the deck. Then do what no command can: look at every rendered slide, review `asset-sheet.html` by eye, work through the manual items in `verification.md` Layer 2, and run the adversarial review.

Full protocol: `verification.md`.

---

## 7. GOVERN — make it usable by people who were not here

Application rules, co-branding posture, trademark handling, brand architecture, localisation, the commissioned-imagery shoot brief that replaces every stand-in, and the handoff. A system a contract developer cannot implement without asking questions is not finished.

The handoff includes the gates. Every page built from the system, the landing page first, runs the brand's forbidden claims and rendered check: `brandcheck lexicon SITE_DIR --claims BRAND_DIR/forbidden-claims.txt --strict` and `brandcheck render <served URL> --pairs BRAND_DIR/pairs.tsv`.

Detail: `governance.md`.
