# Governance — making the system survive contact with an organisation

Researched 2026-08-13. Most brand systems fail not because the design is wrong but because the rules never travel.

## A brand system has four layers. Most stop at one.

| Layer | Contents | Owner |
|---|---|---|
| 1. **Identity** | Logo, colour, type, motion, imagery, voice | Brand / creative |
| 2. **Distribution** | Brand portal, DAM, templates, design tokens, machine-readable rule packs | Brand ops + IT |
| 3. **Governance** | Approval routing, RACI, exception process, versioning, audit trail | Brand ops + Legal |
| 4. **Legal & compliance** | Trademark usage, co-branding licences, regulated-claims review, accessibility statements | Legal / Regulatory |

**The documented failure mode is building Layer 1 and stopping.** A beautiful PDF that nobody can find, nobody can apply to a new format, and nobody enforces is not a brand system — it is a brand *artifact*. Layers 2–4 are what make the rules travel.

Even for a two-person company, decide each layer now, at whatever scale is honest. "There is no DAM; assets live in `/brand` in the repo, and the founder approves" is a valid Layer 2 and 3 answer. No answer is not.

## Why guidelines get ignored

Design against each of these; they are the observed causes, not hypotheses.

| Cause | Counter |
|---|---|
| Nobody can find the current version | One canonical location; version and date on every page |
| Rules are stated as taste, not reasons | Every rule carries its *why*; a rule without a reason loses every argument |
| No answer for a format the guide didn't anticipate | Give principles that generalise, not only worked examples |
| Following the rules is slower than ignoring them | Ship tokens and templates, not just descriptions |
| No consequence, no review, no owner | Name the approver and the exception route |
| The guide describes a system nobody built | Iron Law 3 — specification and implementation ship together |

## Brand architecture

State which model applies, because it determines every lockup rule:

- **Branded house** — one master brand, descriptive sub-names (Google Maps).
- **House of brands** — independent brands, parent invisible or minimal (P&G).
- **Endorsed** — sub-brand leads, parent endorses ("An X company").
- **Hybrid** — most large organisations, which is why the rule must be written down.

For each relationship specify: which mark leads, size relationship, minimum clear space between them, permitted lockup orientations, and **when the endorsement may be omitted**. That last one is what people actually need and it is almost always missing.

## Co-branding and partner logos

Specify: minimum clear space between marks, size parity rules (usually equal cap-height or equal optical weight, not equal pixel width), the separator, permitted orders, backgrounds, and who approves.

**For a company without partners, the answer is that the slot does not exist.** Do not design a partner strip "for later" — an empty or half-filled logo row advertises weakness, and a placeholder ships.

**Research sources are cited, never badged.** A citation is an attribution; a logo is an implied endorsement. The layout must make the difference obvious.

## Trademark usage

- **™** — unregistered claim, usable immediately. **®** — registered only. Using ® before registration is a misrepresentation and, in several jurisdictions, an offence.
- **℠** for services in some jurisdictions.
- Mark the **first or most prominent** occurrence in a document, not every instance.
- Never modify the mark to fit a layout; never use it as a noun or verb in body copy if you want to keep it.
- **Third-party marks** run the other way: acknowledge others' marks, never imply endorsement, and follow their brand guidelines when displaying them.
- **Pre-registration wording matters.** If clearance is pending, say exactly that. Never upgrade "knockout search clear" to "cleared" or "trademarked". Route the final wording through counsel.

## Regulated industries

Where the client is regulated, the brand system must name the review gate and design for it:

- **Pharma — MLR** (medical, legal, regulatory review). Every claim needs referenced substantiation; the system must make claim provenance visible and attachable.
- **Finance — FINRA Rule 2210.** Retail communications need principal approval and record retention; performance claims carry mandated disclosures.
- **Generalisable pattern:** claims carry evidence, evidence is versioned, approval is recorded, and material has an expiry. If your artifacts cannot carry a source, a date and an approver, they will fail the review regardless of how they look.

## Accessibility statement

Enterprises need one, and procurement often needs a VPAT/ACR. Publish: the standard targeted (WCAG 2.2 AA), known gaps, the feedback route, and the date of last assessment. A brand system that cannot state its contrast ratios cannot be assessed — and blocks the sale.

## Localisation and RTL

- Use logical CSS properties (`margin-inline-start`, `border-inline-start`) so the system mirrors correctly. A `border-left` accent rule becomes wrong in Arabic; `border-inline-start` does not.
- State what mirrors and what does not — logos and most iconography do not mirror; directional arrows do.
- Check the typeface's script coverage before committing. Latin-only families are common among open fonts and are a hard blocker for expansion.
- Give translated copy room: German and Finnish run long, and a headline tuned to the character count of English will break.

## Motion policy

State the purpose of motion, the duration and easing tokens, and the reduced-motion behaviour. **The correct reduced-motion state is the finished state**, never blank and never mid-animation. Decorative motion, if any exists, must be stoppable by a labelled control.

## Versioning and handoff

Version the guidelines themselves, with a date and a changelog. When a rule reverses, **amend in place and say so** — a silently edited rule destroys trust in every other rule in the document.

The handoff test: can a contract developer who has read none of the strategy implement this without asking a question? If not, the missing answer goes in the system before it ships.
