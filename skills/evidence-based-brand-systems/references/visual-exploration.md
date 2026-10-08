# Visual exploration: boards before system

Stage 3. The owner chooses a direction by **looking at it**, not by reading about it. Territories are presented as rendered boards built from real imagery, a real mark and real applications. Tokens, documents and the style tile come after the owner has picked.

Why: an owner cannot judge a brand from prose and a scored matrix. A system specified before anyone has seen it is specified against the designer's taste, and the first visual the owner sees arrives after every decision is locked. That is how a brand ends up "correct" and rejected as bland.

## The board: six slides per territory

Each territory is one HTML file of 16:9 slides (1600×900), rendered to PNG and laid out side by side on one comparison page. Start from `templates/board.html`.

| # | Slide | Must show |
|---|---|---|
| 1 | Cover | The territory's hero: real imagery, the headline, the mark and wordmark, and the product proving itself (the signature device) |
| 2 | Mark | The mark on its construction grid, three app-icon grounds, the lockup, one sentence on what the shape means |
| 3 | Colour and type | Colour as proportion blocks (big for the lead colour), the display face set huge with the locale's currency or special glyph, the reading face in a sentence |
| 4 | Imagery | Three images in the territory's treatment, each carrying the signature device |
| 5 | Applications | A poster pair (one type-led, one image-led), or a billboard |
| 6 | Product | A website hero in a browser frame, plus a phone (notification, app or message), with the stage-honesty line visible |

Three territories × six slides. Fewer slides hide the weak territory; more slides drown the choice.

**Real content only.** The real company name, a real proposed headline, real product behaviour. Every invented business, person, time and amount is labelled "Example" on the element itself. Every unbuilt feature shown on a slide carries a visible "planned" line. The board runs through `brandcheck lexicon --claims forbidden-claims.txt` like any page.

## Three territories that differ in kind

Different in **mode**, not in palette. Useful axes (pick three combinations that really differ):

- Imagery mode: warm full-bleed photography · black-and-white photography with one brand colour · tinted or cut-out portraits on colour fields · crafted 3D objects · illustrated character · pure typographic
- Colour mode: one deep colour with one bright accent · black and white with one electric colour · gradient fields · tonal single-hue
- Mark mode: monogram built from the display face's own glyphs · symbol from the product's mechanism · logotype with one modified letter

If two territories could swap palettes without anyone noticing, they are one territory.

## The mark lab

Before choosing a mark for a board, generate 6–10 candidates and look at them.

1. **Source shapes from the brand's own vocabulary and its own font.** Outline glyphs from the display face (`brandassets wordmark FONT --text "’"` gives any glyph as paths) and compose from them: a monogram from the face's quote marks, a letter with one stroke replaced by the product's symbol. A mark drawn from the type stays related to the type.
2. **Render every candidate** at 300, 48, 24 and 16px on light and dark grounds (one sheet) and look at it.
3. **Kill** any candidate that: reads as a stock UI icon (receipt, chat bubble, phone handset, sparkle, check-in-a-circle); depends on detail that disappears at 16px; resembles a reference's or competitor's mark; means nothing you can say in one sentence.
4. Keep the best one per territory. **Shape before colour**: a distinctive shape earns recognition faster than a colour does (see `distinctive assets` in pipeline.md stage 2).

## Signature device

Each territory owns one device a visitor would recognise with the logo covered, derived from what the product actually does. Good devices are **the product's real output, placed into a living image**: a caption of the assistant's real words over a photograph, a confirmation mark inside the name, a colour that follows the time of the interaction. Weak devices are stationery and ornament: stamps, highlighters, handwriting fonts, stickers, doodles bolted onto a flat field.

## AI-default check

Before showing any board, compare it with the current defaults of AI-generated design and of the category. Revise a board that lands on one unless the brief asks for it:

- cream ground, high-contrast serif display, terracotta accent
- near-black ground with one acid green or vermilion accent
- broadsheet: hairline rules, zero radius, dense newspaper columns
- violet/indigo gradient with an orb, waveform, sparkle or glow ("AI" signifiers)
- a flat colour field with nothing living on it

## Look, then show

Render every slide to PNG and **look at every image** before the owner does. Then run the mechanical pass:

```bash
python3 scripts/boardcheck.py boards/direction-A.html     # text past its slide or poster, off-slide elements, collisions
python3 scripts/brandcheck.py lexicon boards --claims forbidden-claims.txt --strict
```

Fix what you see: text running past its container, an element clipped off the slide, a headline cut by a graphic, a logo that vanished on a same-colour ground, a brand name printed on someone's clothing in a photo.

## Presenting the choice

One comparison page: per territory, a two-line description (the idea, the mark's meaning) and its six slides. Ask the owner to choose **or to mix** ("B's mark with A's photography" is a valid answer). Record the choice and the owner's words in `02-creative-direction.md`. The scored matrix, if kept, is a record of trade-offs for the file, never the decider, and it says plainly that the person who scored the territories also designed them.

## When the owner rejects

Before redoing anything, write a **rejection diagnosis** (three short lists) and keep it in `02-creative-direction.md`:

1. What each rejected piece lacks **compared with the owner's own references**, looked at side by side.
2. What the owner's exact words point at ("too plain" is about imagery, depth and personality; "too much" is about competing devices).
3. Which rule or default in this process produced it.

Then redo from the diagnosis. Adding devices to a weak idea makes it worse, not bolder.
