# Tokens and typography

Researched 2026-08-13. The two places where brand systems silently rot: token files that drift apart, and font claims nobody measured.

---

# Part I — Design tokens

## Three layers, and why the middle one exists

```
core       --brand-slate-500        raw values, named by scale position only
   ↓
semantic   --color-border-control   named by role
   ↓
component  --input-border           named by part
```

Component CSS references the **semantic and component layers only** — never core, never a raw value.

The middle layer is not bureaucracy; it is what makes theming possible. Dark mode remaps semantic tokens and touches nothing else, so one attribute flips a whole page. A component that reaches past the semantic layer breaks that **silently, and only in dark mode** — the worst failure mode there is, because it passes review in light.

**Anti-examples worth putting in your own docs so reviewers can point at them:**

```css
/* ✗ raw value */                    color: #7a2e3b;
/* ✗ core layer inside a component */ color: var(--brand-oxblood-700);
/* ✓ */                               color: var(--button-primary-text);
```

## Naming

```
--<prefix>-<category>-<concept>-<property>-<variant/state>
```

- States are suffixes (`-hover`, `-disabled`, `-error`), so a state can never be improvised at the call site.
- **"On-colour" pairings are pre-decided tokens** (`--color-text-on-accent`). Nobody should have to judge readable-text-for-this-background twice.
- **Type roles are quads**: size, line-height, weight and tracking are co-tokens applied together. Applying a size without its quad is a defect — it is how leading and tracking drift apart across a codebase.
- **Responsiveness lives in the tokens**, not in components. Redefine the same custom properties inside a media query at `:root`. If you are writing a media query inside a component for `font-size`, the token is wrong.

## Theming

Ship **both** mechanisms, or an explicit user choice cannot beat the system preference:

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* … */ }
}
:root[data-theme="dark"] { /* … */ }
```

The `:not([data-theme="light"])` guard is what lets an explicit light choice win over a dark OS preference. Set `color-scheme` in both blocks so native controls, scrollbars and form widgets follow. **The two blocks must define identical values** — `brandcheck tokens` verifies this, because a page that disagrees with itself about what dark means is a bug nobody finds until a user reports it.

## One authored format

Pick one file as the source of truth. Generate every other format from it. Then **mechanically diff them** — this is the single highest-value check in the whole system, because token drift is invisible, cumulative, and always discovered at the worst moment.

`brandcheck tokens` resolves both `var(--x)` and DTCG `{a.b.c}` references on both sides before comparing, so an aliased token does not read as a false mismatch.

## DTCG format — get the version right

The Design Tokens Community Group is a **W3C Community Group, not a Working Group**. Its output is a Community Group Report — **not a W3C standard and not on the standards track**. The accurate phrasing is "a W3C Community Group specification".

**Target version 2025.10**, published 2025-10-28 as a Final Community Group Report. Its status section states: *"This specification is considered stable."*

Three modules — <https://www.designtokens.org/TR/2025.10/>:

1. **Format** — file format, groups, aliases, types, composite types. This is the one you implement.
2. **Color** — the `color` type is defined *here*, not in the format module.
3. **Resolver** — multi-context theming. Optional.

> ### Trap: `tr.designtokens.org` is not the spec you want
> `https://tr.designtokens.org/format/` serves a **preview draft** whose own banner reads: *"This is a preview draft of in progress changes. Do not refer to this document directly, and do not implement anything in this document."* It carries the same "2025.10" title as the stable release, so matching on the title is not enough. Many tools still link to it.
>
> **Cite and implement `www.designtokens.org/TR/2025.10/…`.**

**The single structural rule:** an object with a `$value` property **is a token**; an object without one **is a group**. An object that is both is an error. Names may not begin with `$` or contain `{`, `}` or `.`.

**`$type` is never inferred from the value.** It is explicit, inherited from the nearest parent group, or taken from an alias target. Otherwise the token is invalid.

### The 2025.10 breaking change: several values are objects, not strings

This is the thing most tools and most guidance still get wrong. In 2025.10:

| Type | Value shape |
|---|---|
| `color` | `{ colorSpace, components, alpha?, hex? }` — `hex` is an optional **6-digit fallback**, not the value |
| `dimension` | `{ value, unit }` — unit required even when value is `0` |
| `duration` | `{ value, unit }` |

Components are **0–1**, not 0–255. Fourteen colour spaces are supported (`srgb`, `oklch`, `display-p3`, `lab`, `rec2020`, …).

```json
{
  "$description": "Naming contract: JSON path a.b.c maps to CSS custom property --a-b-c.",
  "brand": {
    "color": {
      "$type": "color",
      "border": {
        "$value": { "colorSpace": "srgb", "components": [0.439, 0.475, 0.502], "hex": "#707980" },
        "$description": "Control borders. Meets 3:1."
      },
      "focus": { "$value": "{brand.color.border}" }
    },
    "space": { "2": { "$type": "dimension", "$value": { "value": 0.5, "unit": "rem" } } }
  }
}
```

**Emitting `"$value": "#707980"` is second-editors-draft format, not 2025.10.** A checker that treats an object `$value` as a group will silently skip every colour token in a valid file and report it clean — `brandcheck` handles both shapes deliberately.

Two reference syntaxes exist: `{group.token}` (resolves to `$value`, tokens only) and `$ref` (a JSON Pointer, property-level, newest and least implemented).

### Adoption reality — verify, do not assume

"Supports DTCG" usually means draft-era support. As of 2026-08-13: **Style Dictionary 5.5.1 states outright that 2025.10 "does not have full support yet… work in progress in v5."** Tokens Studio still defaults to its legacy non-`$` format with DTCG as opt-in, and documents gaps (`shadow` `x`/`y` versus `offsetX`/`offsetY`). Figma's native DTCG export was announced but shipped behaviour is unconfirmed.

**Test any claimed DTCG support by inspecting a real export's colour and dimension values.** If colours come out as hex strings, the tool is emitting the 2022 draft.

**State the naming contract in `$description`.** If a generated file cannot be mechanically mapped back to the authored one, it cannot be diffed, and it will drift.

## Store claim facts as tokens

Numbers the brand asserts — prices, durations, counts, targets — belong in the token file, not scattered through markup:

```css
--fact-price-min: 5000;
--fact-sprint-weeks-min: 6;
--fact-customers: 0;          /* pre-launch */
```

Update the token, not the markup. For a company whose credibility depends on accuracy, treating claims as single-source data is a design-system decision, not a copywriting habit. It is also the cheapest possible defence against a stale number surviving on one page after being corrected on three others.

---

# Part II — Typography

## Verify the binary, never the specimen

A foundry specimen shows the full character set. Your subset, your weights, and your actual feature support are questions only the file can answer.

```bash
python3 scripts/brandcheck.py fonts FONT.ttf --glyphs "=≠?→✓" --licence OFL.txt
```

**The failure this prevents:** Public Sans is an excellent, OFL-licensed family — and it contains **neither U+2192 (→) nor U+2713 (✓)**. A status system using those marks renders tofu in it. Discovered in five seconds by inspection; discovered in production by a customer.

**The second failure:** default digits are frequently *not* uniform width. `font-variant-numeric: tabular-nums` binds to a `tnum` feature — if the family has no `tnum`, the declaration **silently does nothing** and every numeric column wobbles. Some families (IBM Plex Mono) are tabular by construction and need no feature; some (Libre Franklin) have neither, and cannot produce aligned columns at all.

Also check: whether `tnum` width is **stable across weights** (if not, a bold total row will not align with the regular rows above it), whether a slashed zero exists, and the exact variable axis ranges — **declare exactly the axis range the font carries**, because a wider declared range makes browsers synthesise smeared fake weights.

## Licensing

**SIL OFL 1.1** permits commercial use, embedding, self-hosting, modification and redistribution. It forbids selling the font by itself. **No UI attribution is required** — but the copyright and licence notice must travel with the font files you ship. Put `OFL.txt` next to the fonts.

### Reserved Font Names — audit the licence, never the binary

> **IBM Plex is the counterexample that breaks naive tooling.** Its `OFL.txt` reads `Copyright © 2017 IBM Corp. with Reserved Font Name "Plex"`, but the shipped binary's `name` table contains **no RFN string at all**. A pipeline that greps binaries would clear IBM Plex for rename-free modification — incorrectly.
>
> **The accompanying licence file is the source of truth.**

An RFN means: subset freely, but any modification to the outlines — or to the name table — requires renaming the derivative. Measured status for common families: Inter, Roboto, JetBrains Mono, Public Sans, DM Sans, Work Sans and Space Grotesk declare **no** RFN. **Lato, Source Sans 3 and IBM Plex do.**

## Self-hosting

- **WOFF2 only.** ~96% global support; every browser you support has it.
- **Subset** to the unicode ranges you actually use — but subsetting that rewrites the name table is modification, so check RFN status first.
- **Variable fonts** where available: one file per style beats five static weights, and gives you the full axis.
- **Metric-matched fallbacks** to kill layout shift during load:

```css
@font-face {
  font-family: "Brand Fallback";
  src: local("Arial");
  size-adjust: 107.4%;        /* measured against the real face */
  ascent-override: 90%;
  descent-override: 22%;
}
```

- `font-display: swap`, `<link rel="preload" as="font" crossorigin>`, and a long immutable cache header.

## Distinctiveness is contextual

Popularity rank matters less than saturation *in the client's category*. A family ranked #58 globally but unused in the client's market is more distinctive in context than the rank suggests — and a family ranked #3 (Inter) carries no brand signal anywhere.

Watch for **borrowed equity**: a face that reads as "the Vercel font" or "the IBM font" to a technical audience is spending someone else's brand rather than building the client's.

## The system must survive font failure

Every stack falls back to metric-sane system faces. No layout may depend on font metrics. **Test with the import blocked** — and verify that any glyph your UI depends on exists in the *fallback* too, not just the webfont.
