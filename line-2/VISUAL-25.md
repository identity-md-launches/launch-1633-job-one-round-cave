# Pepe 25 — Blank Seal

A loose cord waits beside a blank seal until its owner decides.

The new mark is a small yellow ochre tablet with an open circle, beside an unclosed charcoal cord and a red ochre bead. The gap keeps the symbol at the stage of a draft awaiting its owner's choice. It matches Approval Draft's optional, unsigned `approve(spender, 0)` candidates.

| Output | Format | Dimensions | Bytes |
| --- | --- | --- | ---: |
| `artifacts/line-2/wall-v5.png` | 8-bit RGB PNG | 1254 × 1254 | 3,947,296 |
| `dist/line-2/25.jpg` | Baseline, 3-component JPEG | 512 × 512 | 55,652 |

Recovered the latest painted source from Pepe 24's image URL and verified its SHA-256: `cd80330d897598928f981281cb2443a05994963ce62cb908108b037b7b917e5c`. The pigment insert was composited into **x=872, y=570, width=220, height=136**. A separate decode compared the result to the source: all **18,522 changed pixels** fall within **x=872–1091, y=570–705**; every pixel outside the placement rectangle is identical. The central Pepe, prior pouches and cords, rock and torch-lit framing remain in place.

Chosen review: inspect the complete PNG and the finished JPEG thumbnail. The inherited central figure retains Pepe's wide mouth and heavy-lidded eyes. Its two hands show five digits each (four fingers and one thumb); the new mark adds no hands. Pigments are charcoal and red/yellow ochre over visible stone texture. No letters, numbers, captions, signatures, logos, watermarks, borders, real people, political or hateful symbols were observed. **Unmet visual requirements observed: none.** These style and digit checks are a visual assessment, not independent certification.

## Image method

Used the built-in image editor to generate one isolated pigment insert, then consumed its returned PNG bytes in memory. `line-2/finish_wall_25.py` refuses any source wall other than Pepe 24's verified hash, composites the insert only in the placement rectangle, and writes the required full wall. It does not save the insert. Reused `shared/wall-thumbnail/thumbnail.py` to create the required JPEG and inspected that finished thumbnail. No other image was saved in the workspace.

The actual output bytes had an alpha channel; transparency was retained during compositing. Exact prompt:

> Use case: isolated cave-painting insert for later compositing onto the reference wall. Input image: use Image 1 only as a style reference for worn ochre and charcoal marks. Do not reproduce the wall or any existing figures. Primary request: Draw one small standalone cave symbol centered on a completely flat, pure white background. The symbol is a roughly rectangular yellow-ochre stone tablet outlined with broken charcoal strokes; leave its interior blank except for one simple open circle. Beside it, a charcoal cord curves into an visibly unclosed loop and stops short of the tablet, with a small muted red-ochre bead at its end. There must be a clear gap between cord and tablet: this is an unsigned draft awaiting its owner's choice, not an executed action. Style/medium: primitive hand-made burnt-stick and thumb pigment, uneven and slightly worn, flat 2D marks like a Lascaux cave figure. Composition: one simple motif, centered, large enough to crop cleanly, lots of pure white negative space around it. No rock texture or background shading. Palette: charcoal black, muted red and yellow ochre only. Avoid: all letters, numbers, captions, symbols resembling writing, signatures, logos, watermark, frame, border, hand, handprint, person, frog, photographic objects, shadows, gradients, 3D, realistic tablet details.

Exact output measurements and the list of unmet visual requirements are also in `visual-checks-25.json`.
