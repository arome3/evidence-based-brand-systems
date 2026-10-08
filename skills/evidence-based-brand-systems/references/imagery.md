# Imagery: decided, treated, sourced honestly

Stages 3–5. Every brand system decides its imagery: **which kind, one treatment, and where it comes from.** "No imagery" is one possible decision, made deliberately for a brand whose argument really is typographic; it is never the default. Brands that feel made rather than specified almost always carry a living layer: people, characters or objects photographed or drawn with care.

## Choose the mode

| Mode | Fits when | Watch for |
|---|---|---|
| Documentary photography of real customers and their work | The product serves people in a place (shops, clinics, kitchens); trust comes from "people like me" | Stock that reads foreign; staged smiles; logos on clothing |
| Portraits on colour (tinted, cut out, graded) | A persona or service brand; needs to work small (cards, social) | Cut-outs with poor edges; one tint on every face |
| Black and white plus one brand colour | Bold, editorial; colour must come only from the brand | Low-contrast greys; colour sneaking back in |
| Crafted 3D objects | Products with physical metaphors; no customers to photograph yet | Generic glossy "AI" renders; heavy files |
| Illustrated character or cast | A named assistant or mascot; humour is on brand | Childish style; characters in money or complaint moments |
| Typographic only | The argument is the words (manifesto, editorial) | Reading as plain or unfinished |

Pick one primary mode (plus at most one secondary) per territory. The three board territories should not all use the same mode.

## One treatment rule

State it in one sentence and apply it to every image: "warm grade, owners at work, the assistant's words on top"; "black and white, colour only from the record"; "tinted by the hour of the call". A treatment rule is what makes stock and commissioned images sit together as one brand.

## Product on top of life

The strongest pattern for a service product: the product's real output **floating over a real moment**: a caption card of what the assistant actually said, a notification, a booking chip, sitting on a photograph of the person it served. It proves the mechanism and keeps people in the picture. Label every such overlay "Example" until it is a real, consented record.

## Sourcing

**For boards and early sites, free-licence stand-ins are fine; for launch, commission.**

- Free stand-ins: use libraries whose licence allows commercial use without attribution, and record every file. `scripts/photosource.py` searches nappy.co (CC0; photos of Black and brown people), builds numbered contact sheets, downloads the picks and appends `SOURCES.tsv` (file, source URL, licence, date, "stand-in"). Unsplash and Pexels allow similar use but block automation without an API key; download by hand and add the rows yourself.
- Look at every candidate on the contact sheet before picking. Reject: visible brand names or logos on clothing or devices, people who read as a different market than the brand's, recognisable public figures, anything implying a real customer relationship.
- **Never present a stand-in as a customer.** No names, quotes or business names attached to a stock person as if they were real. Example captions say "Example".
- **Commissioned shoot brief** (a deliverable of stage 7): locations, the kinds of businesses and people, the treatment rule, shot list per application, model releases, and the line that replaces each stand-in.
- AI-generated imagery: allowed only if disclosed on the surface where it appears, and never for people presented as customers.

## Reference intake: look, don't summarise

Every reference the owner gives (sites, Behance or Dribbble projects, screenshots) is captured and **looked at by the designer**, image by image, before anything is written about it:

```bash
python3 scripts/refcapture.py site https://example.com --out refs/example
python3 scripts/refcapture.py project https://www.behance.net/gallery/... --out refs/project
python3 scripts/contactsheet.py refs/project --out refs/project/sheet --cols 2
```

A written summary of a reference, by you or by a helper, is not a substitute for looking at it. The owner's references are the standard the boards are judged against.
