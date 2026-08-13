# The visual system

Stage 4. Every decision here carries the five-line annotation from `pipeline.md`. This file is about making the decisions well.

## Visual DNA — state it in nine lines

Before specifying anything, write:

- **Three defining principles.** Each must be falsifiable — a principle that cannot be violated is decoration.
- **Three recurring devices.** The things a reader would recognise across surfaces.
- **Three prohibited tendencies.** Specific to *this* brand, not a generic list.
- **One sentence** on why this system could belong to no other company.

If that last sentence is generic, the system is generic, and no amount of execution will fix it.

## Colour

**Decide what colour *means* before choosing hues.** A palette assembled for looks cannot later be used to carry information, because every hue is already spent on decoration.

Strong systems usually reach one of these:
- Colour is **status** — chromatic values mark state and nothing else, so their appearance is always informative.
- Colour is **structure** — grounds and rules define architecture; one accent marks action.
- Colour is **expression** — the brand's emotional register. Legitimate, but then it cannot also carry status; you will need shape and type to do that.

**Ration the accent.** In the strongest reference systems studied, the accent appears astonishingly rarely — in one case roughly three times on an entire page, only as a status marker. Accent *scarcity*, not accent absence, is what reads as rigour. A page where colour appears constantly cannot use colour to mean anything.

**Map the competitive colour territory before choosing.** Categories saturate: security is red/blue/violet, fintech is blue/green, climate is green. Find what is unclaimed *in that category* rather than what is pleasant in isolation.

**Consider inverting the temperature relationship.** If every competitor pairs a warm ground with a warm accent, a cool ground with a warm accent is both distinctive and unexhausting.

**Per-token, specify:** name, value, usage, **prohibited usage**, and its foreground/background pairing. The prohibited-usage column is the one that prevents drift.

**Decide whether the system needs an alarm colour at all.** If the brand's register is calm, a category-standard alarm red may be actively wrong; errors can be stated rather than alarmed. This is a real choice, not an oversight — but make it deliberately and say so.

## Themes

Dark is not a tint of light. Re-derive every value and re-measure every pairing. Two findings that recur:

- Pure white on near-black glares. A slightly recessed foreground reads as composed and still passes comfortably.
- A ground that is a genuine mid-value, rather than an off-white, reads as a **material** rather than as emptiness. Several of the most crafted reference systems define pure white in their token set and then deliberately never use it as a ground.

## Typography

**Weight is the loudest lever.** Deciding what weight is *for* is the highest-leverage typographic decision available. A common strong choice: hierarchy by size, measure, tracking and position, with weight reserved for a structural distinction — prose versus interface apparatus, say — rather than for emphasis. Then "make it bold" has no meaning in the system, and the page cannot shout.

Whatever the rule, **state it**, because it is the first thing that erodes.

- **Two families is usually right**: one workhorse, one with a distinct job (data, metadata, code, annotation). Three needs justification.
- **Give the second family a semantic job, not a decorative one.** Monospace micro-type has become a generic shorthand for "technical credibility". It only earns its place if it carries actual data — an identifier, a date, a source, a state. A mono label reading `OUR PROCESS` is costume; one reading `OBSERVED 2026-08-12 · RUN 3 OF 5` is information.
- **Display type**: large sizes want tighter tracking. Regular-weight type at large size with tight tracking reads as a solid typographic block and states things as fact; heavy weight at large size shouts. Pick which you want.
- **Bind size, line-height, weight and tracking as a quad.** See `tokens-and-type.md`.

## Grid, spacing, radius, elevation

- **One base unit** (4px is conventional), one scale, nothing off-scale.
- **Reading measure** capped around 66–72 characters, declared as a system invariant rather than per-component.
- **Radius and elevation are register decisions.** Rounded, elevated cards read as application chrome; square, ruled, flat surfaces read as document. Choose to match what the brand *is*, then hold the line — a maximum radius stated in the system is easy to enforce and instantly recognisable.
- **Consider whether shadows are needed at all.** Several high-craft systems ship essentially none, separating surfaces with hairlines and ground changes instead. Reserve elevation for genuinely layered UI.
- **A reserved rail** — a column held for annotation, provenance or metadata — buys asymmetry and a strong left edge with no ornament. If you use one, **fill it with something real**; an empty rail is just a margin.

## Plates and section rhythm

Full-bleed grounds that change what *kind* of claim is being made are one of the cheapest ways to make a page feel designed rather than defaulted. Hard cuts, not gradients.

**Bind each plate to a meaning, and use as many plates as you have arguments — no more.** A saturated accent plate reserved for the block where the company commits to something keeps "the accent means action" true at page scale as well as at chip scale. A plate used as a mood beat is decoration.

## Graphic language

Define reusable devices, each bound to a specific meaning, and **name what each is forbidden to express**. Derive them from the client's actual vocabulary — the nouns their product produces. A device you can only describe in visual terms is ornament.

**Then build them.** A guidelines document naming seven devices beside an artifact rendering two is the most common defect in brand work, and the reason systems read as plainer than they were designed to be.

**The best centrepiece is a truthful model of the mechanism.** The strongest reference systems studied draw their own product — the actual thing, in the visual language of the discipline that produces it — rather than a metaphor for it. The prettiest thing on the page should also be the truest thing on the page.

## Texture

The line is: **does it carry information about what the surface is, and does it leave every measured ratio unchanged?**

A material grain that makes a ground read as a surface can be generated procedurally (an inline SVG `feTurbulence` data URI needs no image asset), painted behind content, and averaging to the base colour so no contrast pairing changes. That is material.

Gradient fields, shader backgrounds, particle drift, blur bloom and ambient loops are atmosphere — they carry feeling instead of information, and on a page whose argument is evidence they actively contradict the pitch. One reference system's shader required a triple text-shadow glow to rescue legibility from it; that is the tell.

## Imagery

Decide what the brand shows *instead of* the category's stock imagery. Specify allowed / discouraged / prohibited per category: evidence, source material, product, abstract graphics, photography, illustration, data visualisation.

**Aim for zero required image assets in version one.** It keeps the system implementable by one person, keeps it fast, and forces the graphic language to do real work. If AI-generated imagery is ever used, **disclose it on the surface where it appears** — a rare convention, and the one most compatible with a brand claiming accuracy.

## Data presentation

- Tabular, lining figures everywhere numbers appear — and verify the font actually supports it.
- Every figure beside its source, at the same visual weight.
- Label marks directly; legends are a fallback, never the only key.
- Render uncertainty rather than hiding it; make "inconclusive" a first-class displayed state.
- **No count-up animation.** A number animating from zero is theatre applied to a fact.

## Motion

Motion communicates state or causality. It does not exist to decorate.

- Interaction band 140–300ms. Longer durations only for genuine content disclosure.
- **No ambient motion.** Loops, drifts, marquees and self-running demos assert liveliness, which is activity presented as progress.
- Disclosure should not reflow the page — fix the container height so the reader never loses their place.
- Every animation has a reduced-motion **finished** state.
- If any decorative motion survives, it must be stoppable by a labelled control.
