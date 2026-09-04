# System logos

Drop an SVG here named after the system's `<theme>` tag in
`es_systems.cfg` - `snes.svg`, `gb.svg`, `n64.svg`, `psx.svg` - and the
system rail draws it instead of the console's name. Anything without a
file keeps its name, so the folder can be filled in a few systems at a
time.

The switch between the two is the user's: **UI SETTINGS > THEME
CONFIGURATION > SYSTEM TILES**, with `NAMES` forcing names even where a
logo exists. It can also be set for one console at a time from that
system's VIEW CUSTOMIZATION.

## What the tile expects

- **SVG only.** The path in `views/system.xml` ends in `.svg`; the ES
  rasterises it with nanosvg, so keep to plain paths and fills - no
  filters, gradients on strokes, or embedded bitmaps.
- **Fitted to 99x99px** (`maxSize` 0.8 of the 124px tile) and scaled down
  with the tile when it is not the selection, so anything thinner than
  about 2px at that size disappears. Draw for the small end.
- **Its own colours are kept**, they are not tinted. The tile behind it is
  near-black, so pale or white marks read best; a dark logo on a dark tile
  will not.

## The collections are ours

`auto-allgames.svg`, `auto-favorites.svg` and `ports.svg` are not from the
pack. A collection is the frontend's own idea rather than a console with a
mark of its own, so it gets one of ours.

**Collections get a drawing, not a word.** `auto-favorites.svg` is a star
and `auto-allgames.svg` is four tiles, both drawn straight into the SVG.
The reason is language: a tile with no logo falls back to the system's
name, and for a collection the ES's name is its internal id - `all`,
`favorites`, `recent` - which is English whatever the interface language
is. A drawn word would be stuck in English the same way. A mark is not.
Any collection added later wants the same treatment.

**A plain system can have a word.** `ports.svg` is the word PORTS, set in
the theme's own IBM Plex Sans Bold by `tools/make-wordmark.py`:

    python3 tools/make-wordmark.py art/logos/ports.svg "PORTS"

That is safe because `ports` is an ordinary system out of
`es_systems.cfg`, and its name is whatever that file says - the ES does
not translate it, unlike collection labels.

The wordmarks are outlines, not text: nanosvg does not render `<text>` at
all, so the tool reads the TrueType contours out of the font and writes
them as paths. Nothing on the device needs the font for them to draw.
Setting a word in a typeface and converting it to outlines is ordinary use
of the font rather than distribution of it, so these carry no OFL
obligation of their own - unlike `art/fonts/`, which does.

The theme folder name is what the file has to be called, and for the ES's
automatic collections that is not the name on screen: `auto-allgames`,
`auto-favorites`, `auto-lastplayed`, `auto-at2players`, `auto-neverplayed`,
`custom-collections` and so on.

## Credit

The logos here are by **Dan Patrick**, from "Console Logos Professionally
Redrawn + Official Versions" v2.1 - over 500 hours of work across 15
months, announced on r/emulation and archived at:

    https://archive.org/details/console-logos-professionally-redrawn-plus-official-versions
    https://www.reddit.com/r/emulation/comments/10z1gsb/v21_i_redrew_every_consoles_logo_for_emulation/

Used with the author's permission, given in that post:

> If you want to use these for any weird or obscure uses go ahead! I
> enjoyed hearing about all the different passions projects people were
> using these for. That's great. Also, I will always appreciate credit.
> Thanks! Please enjoy them!

Credit is the one thing asked for, so it travels with the files: this
note, the carve-out in the theme's LICENSE, and the RelicOS release notes.
Redrawn artwork is the author's; the trademarks it depicts are their
respective owners' and are used here only to name the console a game runs
on.

If a set is ever swapped for another, this section is what has to change
with it - the licence deliberately does not cover this folder.

## How these were made

One file per system out of the `Light - Just White` folder of the SVG set
(`v2.1_SVGs_(vector)_(Full Set)`), which is the variant drawn for dark
backgrounds. Where a platform had several drawings, the plain one was
taken - the numbered ones are usually a different console (`Sony
Playstation 2`) or a different lettering set, not a variant of the same
mark.

They are not the original files. Illustrator puts its colours in a
`<style>` block and tags the shapes with `class="st0"`, and the ES's SVG
rasteriser - nanosvg - has no CSS parser at all: it would ignore both,
fall back to the SVG default fill of black, and the logo would vanish
against the tile. `tools/convert-logos.py` inlines those rules as
presentation attributes, drops the Illustrator `<switch>`/`<foreignObject>`
payload, and reports anything nanosvg still cannot draw. Nothing else in
the artwork was touched.

    python3 tools/convert-logos.py <folder of named SVGs>

`tools/check-logos.c` is the other half: it rasterises through the very
same nanosvg the device uses and reports how much ink each logo has and
how bright it is. A logo that comes out `lum=0` is the silent failure -
it draws, in black, invisibly. Every file here was checked that way.
