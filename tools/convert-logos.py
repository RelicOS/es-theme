#!/usr/bin/env python3
"""Make Illustrator SVGs safe for the ES's SVG rasteriser.

The ES draws SVGs with nanosvg, which has no CSS parser at all. Artwork
exported from Illustrator puts its colours in a <style> block as class
rules and tags the shapes with class="st0" - nanosvg ignores both, falls
back to the SVG default fill of black, and the logo disappears against a
dark tile. This inlines those rules as presentation attributes and drops
the stylesheet, then reports anything left that nanosvg still cannot draw.

    python3 tools/convert-logos.py SRCDIR [DESTDIR]

SRCDIR holds <system>.svg named after the `<theme>` tags in es_systems.cfg;
DESTDIR defaults to art/logos/. Existing files are overwritten.

Standard library only, like the other tools here.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Elements and attributes nanosvg does not implement. Hitting one of these
# does not stop the conversion - the file may still be mostly fine - but it
# is worth knowing before the logo turns up wrong on the device.
UNSUPPORTED = {
    "text": "text is not rendered; it has to be converted to outlines",
    "tspan": "text is not rendered; it has to be converted to outlines",
    "image": "embedded bitmaps are not rendered",
    "filter": "filters are not rendered",
    "mask": "masks are not applied",
    "use": "<use> references are not resolved",
    "pattern": "patterns are not rendered",
    "clipPath": "clip paths are ignored, so clipped art may spill",
    "switch": "<switch> is not evaluated",
}

# Declarations worth carrying over. nanosvg reads these as attributes.
KEEP = {"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
        "stroke-miterlimit", "stroke-dasharray", "fill-rule", "clip-rule",
        "opacity", "fill-opacity", "stroke-opacity"}


def parse_css(block):
    """`.st0{fill:#FFF;} .a,.b{...}` -> {class: {prop: value}}."""
    rules = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
        decls = {}
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, _, value = decl.partition(":")
            prop, value = prop.strip(), value.strip()
            if prop in KEEP and value:
                decls[prop] = value
        if not decls:
            continue
        for sel in selectors.split(","):
            sel = sel.strip()
            if sel.startswith(".") and re.fullmatch(r"\.[A-Za-z_][\w-]*", sel):
                rules.setdefault(sel[1:], {}).update(decls)
    return rules


def strip_illustrator(svg):
    """Drop the Illustrator PGF payload and unwrap <switch>.

    Illustrator writes <switch><foreignObject>...private data...</foreignObject>
    <g i:extraneous="self">...the actual art...</g></switch>. nanosvg does not
    evaluate <switch>, so the art is safer out of it.
    """
    svg = re.sub(r"<foreignObject\b.*?</foreignObject>", "", svg, flags=re.S)
    svg = re.sub(r"<foreignObject\b[^>]*/>", "", svg)
    svg = re.sub(r"</?switch\b[^>]*>", "", svg)
    svg = re.sub(r"<i:[^>]*>.*?</i:[^>]*>", "", svg, flags=re.S)
    svg = re.sub(r"<i:[^>]*/>", "", svg)
    return svg


def inline(svg):
    svg = strip_illustrator(svg)
    styles = re.findall(r"<style[^>]*>(.*?)</style>", svg, re.S)
    rules = {}
    for block in styles:
        rules.update(parse_css(block))

    svg = re.sub(r"<style[^>]*>.*?</style>", "", svg, flags=re.S)

    applied = [0]

    def fix_tag(m):
        tag = m.group(0)
        cls = re.search(r'\sclass="([^"]*)"', tag)
        if not cls:
            return tag
        decls = {}
        for name in cls.group(1).split():
            decls.update(rules.get(name, {}))
        tag = tag.replace(cls.group(0), "")
        if decls:
            applied[0] += 1
        # An attribute already on the element wins over the stylesheet, the
        # same way it would in a browser for a plain class selector.
        extra = "".join(f' {p}="{v}"' for p, v in decls.items()
                        if not re.search(rf'\s{re.escape(p)}="', tag))
        body = tag.rstrip()
        selfclose = body.endswith("/>")
        body = (body[:-2] if selfclose else body[:-1]).rstrip()
        return body + extra + ("/>" if selfclose else ">")

    svg = re.sub(r"<[a-zA-Z][^>]*>", fix_tag, svg)
    svg = re.sub(r"\n\s*\n+", "\n", svg)
    return svg, applied[0], bool(rules)


def audit(name, svg):
    notes = []
    for element, why in UNSUPPORTED.items():
        if re.search(rf"<{element}\b", svg):
            notes.append(f"<{element}>: {why}")
    if re.search(r'\sclass="', svg):
        notes.append("class attributes left over: some rule did not resolve")
    # Anything with no fill of its own inherits black from the SVG default.
    shapes = re.findall(r"<(path|polygon|polyline|rect|circle|ellipse)\b[^>]*>", svg)
    bare = [s for s in re.findall(
        r"<(?:path|polygon|polyline|rect|circle|ellipse)\b[^>]*>", svg)
        if 'fill=' not in s and 'style=' not in s]
    if bare and not re.search(r"<g[^>]*\sfill=", svg):
        notes.append(f"{len(bare)}/{len(shapes)} shapes have no fill: "
                     "they will draw black")
    return notes


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    dest = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "art", "logos")
    os.makedirs(dest, exist_ok=True)

    names = sorted(f for f in os.listdir(src) if f.endswith(".svg"))
    flagged = 0
    for fn in names:
        svg = open(os.path.join(src, fn), encoding="utf-8", errors="replace").read()
        svg, applied, had_css = inline(svg)
        open(os.path.join(dest, fn), "w", encoding="utf-8").write(svg)
        notes = audit(fn, svg)
        if notes:
            flagged += 1
            print(f"{fn}:")
            for n in notes:
                print(f"    {n}")
    print(f"\n{len(names)} logos written to "
          f"{os.path.relpath(dest, ROOT)}, {flagged} flagged")


if __name__ == "__main__":
    main()
