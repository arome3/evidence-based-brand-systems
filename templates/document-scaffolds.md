# Document scaffolds

Required headings for the five brand documents. Fill them; do not drop sections.
A section with nothing to say gets an honest sentence saying so, never deletion —
a missing section reads as an oversight, a stated gap reads as a decision.

---

## 01-brand-identity.md

```
# <Brand> — Brand Identity
**Date** · **Status** · **Prepared for**
Scope note: what every claim below traces to.

## Assumptions            <- at the TOP, always. Every unresolved decision listed.
## Brand foundation       purpose · promise · positioning · audience
                          functional / commercial / emotional benefit
                          what it IS · what it is NOT
## Brand personality      exactly five traits. Each: meaning · "this, not that" ·
                          verbal · visual · product expression · FAILURE MODE IF OVERUSED
## Values                 name · meaning · observable behaviour · copy / design /
                          product implication. No "innovation" or "excellence"
                          unless made concrete and distinctive.
## Voice                  attributes · >=3 rewrite examples
                          (generic line -> why it fails -> brand version -> rule shown)
                          how it speaks about: uncertainty · competitors · its own stage ·
                          what it cannot promise
## Naming and wordmark    rationale · pronunciation · typographic wordmark rationale ·
                          parent-company relationship · TRADEMARK STATUS (exact wording)
## Taglines               exactly three. Each: rationale · strength · risk · where to use
## Approved descriptions  one-line · 25-word · 50-word · boilerplate (count the words)
```

**Label proposed principles as recommendations.** Do not invent a mission the strategy documents do not support.

---

## 02-creative-direction.md

```
## Part I — Research
  Category conventions      cliché inventory: dead vs live conventions
  Competitors               per competitor: colour, type, hero, motifs, proof, voice
                            + what a visitor remembers + the whitespace they leave
  Craft benchmarks          METHODS ONLY. Explicitly out of scope: their look.
  Taste references          per-site observations, all labelled
                            [VERIFIED] / [OBSERVED] / [INTERPRETATION]
  Shared qualities          2-4, each with per-site evidence
  Taste profile             a NAME · one-sentence definition · defining qualities ·
                            emotional register · colour · typography · composition ·
                            texture · motion · what it rejects
  Conflicts                 each conflict, both sides, the choice, why, exceptions
  Rejected influences       what was declined and the reason
  Typeface substitutions    Reference / Open alternative / Similarities /
                            Differences / Source / Licence

## Part II — Territories
  Three territories, each with the full block (see pipeline.md)
  Decision matrix           weighted scores, taste never outranking strategy
  Selected territory        written rationale · emotional impression · central metaphor ·
                            mood in words · verbal / visual / product implications
  Rejected territories      reasons, and which ideas are RETAINED inside the winner
  Application scenarios     correct and incorrect
  Risks and safeguards
  Competitor differentiation check
  Traceability map          Reference | Quality learned | Used? (Yes/Partially/No) |
                            Adaptation | Reason
  Reference-independence    element by element
```

Do not include mood boards or external images. The writing must be specific enough that an independent designer could build one.

---

## 03-visual-direction.md

Every major decision carries:

```
> **Decision** — what the brand does.
> **Strategy** — grounded in the client's documents or audience.
> **Territory** — the principle it expresses.
> **Reference influence** — the reference, or "none".
> **Adaptation** — what was learned, how this stays distinct.
```

Applied to: palette · typography · grid · spacing · graphic language · texture · iconography · data presentation · motion · light theme · dark theme.

```
## Visual DNA          3 principles · 3 devices · 3 prohibited tendencies ·
                       1 sentence on why this belongs to no one else
## Colour              per token: name · value · usage · PROHIBITED USAGE · pairing
                       semantic + status palettes; never colour alone
## Typography          stacks · licence · source · direct licence URL · fallbacks
                       responsive scale: token | mobile | desktop | weight | line |
                       tracking | use
## Spacing and layout  base unit · scale · containers · grid · breakpoints ·
                       reading width · radius philosophy · shadow philosophy
## Imagery             allowed / discouraged / prohibited. No image assets in v1.
## Graphic language    each device bound to a meaning, and what it may NOT express
## Iconography         style · stroke · grid · sizes · accessibility
## Motion              purpose · durations · easing · states · reduced-motion
```

When a rule is later reversed, **amend in place and say so**. A silently edited rule destroys trust in every other rule.

---

## 04-brand-guidelines.md

```
## Wordmark             construction (reproducible units) · clear space · minimum size ·
                        light / dark / monochrome · misuse · pre-registration handling
## Colour pairing       EVERY pairing: fg token · bg token · fg hex · bg hex ·
                        computed ratio · threshold · pass/fail · intended use
                        + documented exemptions (disabled, decorative, logotype)
## Voice in application buttons · forms · empty states · errors · warnings ·
                        loading · completion · uncertainty
## Brand applications   email signature · avatar · OG image · report · proposal ·
                        product UI · presentation
## Parent relationship  lockup · placement · size · clear space · when required/omitted
## Partners             co-branding posture; for a pre-launch company the slot
                        DOES NOT EXIST
## Prohibited           everything that must never appear
```

---

## 05-design-system.md

```
## Foundations          principles · token architecture · naming · themes ·
                        responsive approach · accessibility standard · content design
## Components           button · input · card · table · nav · footer · callout
                        + the brand's own signature components
   For EACH:            purpose · anatomy · variants · sizes · default · hover ·
                        focus-visible · active · disabled · loading · error ·
                        responsive · keyboard · screen reader · content rules ·
                        usage · MISUSE
## Self-review checklist   completed, honestly, with methods stated
## Open items             decisions only the owner can make
```

State "not applicable" explicitly where a state genuinely does not exist. An undocumented state is indistinguishable from a forgotten one.
