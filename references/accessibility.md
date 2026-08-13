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

**2. APCA is not the WCAG 3 algorithm and has no normative status.** The current WCAG 3 draft states the contrast algorithm is "yet to be determined" and does not name APCA. Use WCAG 2 ratios as the conformance gate; use APCA only as an advisory tie-breaker. **Never publish APCA numbers as your stated accessibility criteria** — there is no standard to conform to, so an APCA-only palette has no defensible conformance story.

**3. ADA Title II deadlines moved in April 2026** to **April 26 2027** and **April 26 2028**. Earlier published 2026/2027 dates are stale.

## The thresholds

| Requirement | Level | Threshold |
|---|---|---|
| 1.4.3 Contrast (Minimum) — normal text | AA | **4.5:1** |
| 1.4.3 — large text | AA | **3:1** |
| 1.4.6 Contrast (Enhanced) — normal text | AAA | 7:1 |
| 1.4.6 — large text | AAA | 4.5:1 |
| 1.4.11 Non-text Contrast | AA | **3:1** |
| 2.5.8 Target Size (Minimum) | AA | 24×24 CSS px |

**Large text** = 18.66px (14pt) **bold**, or 24px (18pt) at any weight.

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

## Beyond contrast

- **Never colour alone** (1.4.1). Every status carries a glyph and a word as well as a hue. Differentiate component *classes* by shape too, so they survive greyscale and colour-vision deficiency. Test by rendering the artifact in greyscale.
- **Reduced motion.** Honour `prefers-reduced-motion: reduce`. The correct reduced state is the **finished** state, never blank or mid-animation.
- **Target size** 24×24 CSS px minimum (2.5.8, AA); 44×44 is the comfortable target for primary actions.
- **Focus** must be visible on `:focus-visible`. Never `outline: none` without an equal-or-better replacement.
- **Dark themes are not tints.** Re-derive and re-measure every pairing. Pure white on near-black glares; a slightly recessed foreground reads better and still passes.

## Why this is not optional

- **EN 301 549** is the EU technical standard; the **European Accessibility Act** applied from **June 2025** to consumer-facing products and services.
- **ADA Title II** compliance dates: **April 26 2027** and **April 26 2028**.
- Procurement in most large organisations requires a VPAT/ACR. A brand system that cannot state its contrast ratios cannot be assessed, and blocks the sale.

Fixing a palette before it is signed off costs a token edit. Fixing it after launch costs a rebrand.
