# The visual system

Stage 4. Every decision here carries the five-line annotation from `pipeline.md`. This file is about making the decisions well.

**The board the owner picked sets the register.** The guidance below describes options and their trade-offs, not one house style. A restrained, document-like system is right for some territories and wrong for others; where a rule here reads as an absolute about *look* (restraint, accent rationing, texture, motion, imagery), it applies only when the picked board is in that register. Rules about *truth* (contrast, labelled specimens, no invented proof) apply everywhere.

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

**Decide how much colour the brand spends.** Two strong models: a *rationed* accent that appears a few times a page and always means something (rigour, status), or a *spent* colour used in big fields, plates and posters that becomes the brand's recognisable asset (energy, fame). Choose from the picked board; then hold it. Either way, a colour that carries meaning (status, record type) never doubles as decoration.

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

Gradient fields, grain and soft colour washes are legitimate *when they mean something in this brand* (a sky that follows the time of day, a material, a mood the owner's references share) and every text pairing on them is computed. Shader backgrounds, particle drift and ambient loops that exist only to look "AI" are atmosphere: avoid them. The tell is legibility: if text needs a glow to survive the background, the background is wrong.

## Imagery

Decided in stage 3, specified here: the mode, one treatment rule, and the sources (`imagery.md`). Specify allowed / discouraged / prohibited per category (photography, illustration, 3D, characters, product, data, evidence). The identity's own export set, the outlined wordmark, the mark and the icons in `assets/`, is built as in `assets.md`. If AI-generated imagery is ever used, disclose it on the surface where it appears.

## Data presentation

- Tabular, lining figures everywhere numbers appear — and verify the font actually supports it.
- Every figure beside its source, at the same visual weight.
- Label marks directly; legends are a fallback, never the only key.
- Render uncertainty rather than hiding it; make "inconclusive" a first-class displayed state.
- **No count-up animation.** A number animating from zero is theatre applied to a fact.

## Motion

Motion communicates state or causality. It does not exist to decorate.

- Interaction band 140–300ms. Longer durations only for genuine content disclosure.
- **Ambient motion is a choice, not a default.** Loops, drifts and marquees assert liveliness; use them only when the picked board's energy calls for it, keep them cheap on low-end devices, and give them a labelled stop control.
- Disclosure should not reflow the page — fix the container height so the reader never loses their place.
- Every animation has a reduced-motion **finished** state.
- If any decorative motion survives, it must be stoppable by a labelled control.

## Sound and voice (when the product speaks)

For voice assistants, phone services and anything users hear, sound is a distinctive asset.

- **Voice:** casting brief (accent, age, warmth, pace) matched to the audience; one voice per persona.
- **Fixed phrases:** the greeting and the confirmation line, word for word, so they become recognisable.
- **Sonic logo:** a 2–3 note motif under 1.5 seconds that survives a phone line (roughly 300–3,400 Hz), paired with one visual moment (the mark animating, a confirmation appearing).
- **Show sound as words, not waves.** Captions of what was said beat waveforms and orbs, which are now generic category signifiers.
- Where callers hear the client's customer's business name rather than the brand, the caller-facing sound belongs to that business; brand sound lives in the product, the site and marketing.
