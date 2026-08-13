# Accessibility

The conformance gate for a brand system in 2026. Researched 2026-08-13; every claim links to its source.

## Three corrections to guidance that circulates widely and is wrong

**1. SC 2.4.11 and 2.4.12 are "Focus Not Obscured", not "Focus Appearance".**

| SC | Name | Level |
|---|---|---|
| 2.4.11 | Focus Not Obscured (Minimum) | **AA** |
| 2.4.12 | Focus Not Obscured (Enhanced) | AAA |
| 2.4.13 | Focus **Appearance** | **AAA** |

The 2-CSS-pixel-perimeter focus rule belongs to 2.4.13 and is **AAA**. A system claiming AA is obliged only to ensure focus is not entirely hidden by author content — sticky headers, cookie banners, chat widgets. Design a strong focus indicator anyway; just do not cite it as an AA requirement.
<https://www.w3.org/TR/WCAG22/> · <https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html>

**2. APCA is not the WCAG 3 algorithm and has no normative status.** The current WCAG 3 draft states the contrast algorithm is "yet to be determined" and does not name APCA. Use WCAG 2 ratios as the conformance gate; use APCA only as an advisory tie-breaker. It is most useful over **dark-theme tokens**, where WCAG 2's `+0.05` flare constant scores near-black backgrounds generously and can wave through a pairing that reads poorly. **Never publish APCA numbers as your stated accessibility criteria** — there is no standard to conform to, so an APCA-only palette has no defensible conformance story.

**3. ADA Title II deadlines moved in April 2026.** A DOJ Interim Final Rule (20 April 2026) extended them by a year to **26 April 2027** (population ≥50,000) and **26 April 2028** (<50,000 and special districts). **The standard it names is WCAG 2.1 AA, not 2.2.** Any guidance citing 2026/2027 dates, or citing 2.2, is stale.

## The thresholds

| Requirement | Level | Threshold |
|---|---|---|
| 1.4.3 Contrast (Minimum) — normal text | AA | **4.5:1** |
| 1.4.3 — large text | AA | **3:1** |
| 1.4.6 Contrast (Enhanced) — normal text | AAA | 7:1 |
| 1.4.6 — large text | AAA | 4.5:1 |
| 1.4.11 Non-text Contrast | AA | **3:1** |
| 2.5.8 Target Size (Minimum) | AA | 24×24 CSS px |

**Large text** = at least 18pt (~24px) at any weight, **or** 14pt (~18.5px) **bold**. The lower threshold applies *only* to bold — 18.5px regular is normal text and needs 4.5:1.

## The anti-rounding rule — normative, and routinely violated

> "The computed values should not be rounded (e.g., 4.499:1 would not meet the 4.5:1 threshold)."

A pair computing to 4.49:1 **fails**. Contrast checkers that display one decimal show "4.5" for a failing pair — this is the single most common way an inaccessible palette gets signed off.

**Consequences for the system:**
- Compare against the unrounded float. `brandcheck` truncates rather than rounds for exactly this reason.
- Target a margin: **4.6:1+** for body text, so a later brand-colour nudge does not silently cross the line.
- `brandcheck contrast` warns when the tightest pair has under 5% headroom. Treat that warning as a design constraint, not noise.

## What 1.4.3 exempts

1. **Inactive UI components** — a disabled control has no contrast requirement.
2. **Pure decoration** — text with no informational value.
3. **Incidental text** — not visible, or part of a picture with significant other content.
4. **Logotypes** — *"Text that is part of a logo or brand name has no contrast requirement."*

Logotype exemption is real but narrow: it rests on the assumption that logos answer to corporate identity constraints. It is **not** a licence for author-chosen low-contrast branding elsewhere on the page.

## What 1.4.11 covers, and its four exemptions

**Applies to** — visual information required to identify components and states: input borders, checkbox and radio outlines, toggle tracks, focus rings, the boundary of a button when that boundary is what distinguishes it, and state distinctions (checked/unchecked, selected/unselected tab). And to **graphical objects**: meaningful icon strokes, chart series, data-viz marks, meter fills.

Two nuances that change token design:

- **It is the parts *required to identify* the component, not every pixel.** A filled button with a 4.5:1 label does **not** additionally need a 3:1 border — the label already identifies it. A ghost/outline button whose only affordance is its border **does**.
- **Adjacent colours count.** The 3:1 is measured against whatever the element actually sits against. For a nested surface (input on card on page) that adjacent colour changes per context. **This is why elevation and surface tokens must be validated per surface pairing, not once against a single canonical background.** A border that passes on the page ground can fail on a sunken well.

**Exempt:**

1. **Inactive/disabled components.** An explicit carve-out — disabled tokens are legitimately allowed to be low-contrast. Two cautions: greying out is a colour-only signal, so 1.4.1 still argues for a non-colour cue; and the exemption covers genuinely inoperable controls, not controls that merely look de-emphasised. *Note: the disabled control's **label** is a separate question — keep it readable.*
2. **User-agent-determined appearance.** Unstyled native controls and default focus rings are out of scope — **but the exemption is lost the moment the design system restyles them.** This is the trap in "we just reset the default focus outline."
3. **Pure decoration.**
4. **Essential presentation** — where a particular presentation is essential to the information (flags, medical diagrams, gradients representing measurement). A heatmap's gradient is essential; its axis labels are not.

## The formulas

```python
def srgb(c8):                       # one 0-255 channel
    c = c8 / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def luminance(hexstr):
    h = hexstr.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*srgb(r) + 0.7152*srgb(g) + 0.0722*srgb(b)

def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)       # then TRUNCATE, never round up
```

## Two criteria that constrain the system structurally

**1.4.1 Use of Color — Level A.** This gates even minimum conformance. The classic failure is removing underlines from links in body copy: hue alone then distinguishes them. Either keep an underline, or provide another non-colour cue. This is also why every status in a system needs a glyph and a word.

**1.4.12 Text Spacing — Level AA.** Content must survive line-height 1.5×, paragraph spacing 2×, letter-spacing 0.12em and word-spacing 0.16em with no loss of content or function. **In practice this prohibits fixed-height text containers.** Any component with a hard `height` around text will clip when a user applies a spacing stylesheet. Use `min-height`.

## Beyond contrast

- **Never colour alone** (1.4.1). Every status carries a glyph and a word as well as a hue. Differentiate component *classes* by shape too, so they survive greyscale and colour-vision deficiency. Test by rendering the artifact in greyscale.
- **Reduced motion.** Honour `prefers-reduced-motion: reduce`. The correct reduced state is the **finished** state, never blank or mid-animation.
- **Target size** 24×24 CSS px minimum (2.5.8, AA); 44×44 is the comfortable target for primary actions.
- **Focus** must be visible on `:focus-visible`. Never `outline: none` without an equal-or-better replacement.
- **Dark themes are not tints.** Re-derive and re-measure every pairing. Pure white on near-black glares; a slightly recessed foreground reads better and still passes.

## Why this is not optional

- **EN 301 549** is the EU technical standard. The operative version today is **v3.2.1, which requires WCAG 2.1 AA** — not 2.2. A v4.1.1 incorporating WCAG 2.2 is expected around October 2026, but that date is unconfirmed from primary source; do not plan against it.
- The **European Accessibility Act** applied from **28 June 2025** to consumer-facing products and services. That date has passed.
- **ADA Title II**: WCAG 2.1 AA, by **26 April 2027** / **26 April 2028**.

**Design to WCAG 2.2 AA anyway.** It is a superset of 2.1 AA, so it satisfies both regimes and survives the EN 301 549 update without rework.
- Procurement in most large organisations requires a VPAT/ACR. A brand system that cannot state its contrast ratios cannot be assessed, and blocks the sale.

Fixing a palette before it is signed off costs a token edit. Fixing it after launch costs a rebrand.
