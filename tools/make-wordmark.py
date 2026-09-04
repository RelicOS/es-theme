#!/usr/bin/env python3
"""Draw a word as outlines, in the theme's own typeface, as an SVG.

The system rail shows a logo where art/logos/<theme>.svg exists and the
system's name otherwise. Collections - all games, favorites - are the
theme's own idea rather than a console with a mark of its own, so they end
up as small text between big console wordmarks. This turns them into
wordmarks too, set in IBM Plex, so the rail reads as one thing.

It has to be outlines: the ES rasterises SVG with nanosvg, which does not
render <text> at all. So this reads the TrueType outlines straight out of
the font and emits them as paths - no font is embedded and nothing on the
device needs the font to be installed.

    python3 tools/make-wordmark.py <out.svg> <text> [--font F] [--track T]

Standard library only, like the other tools here.
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FONT = os.path.join(ROOT, "art", "fonts", "IBMPlexSans-Bold.ttf")
COLOUR = "#FFFFFF"


class Font:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        count = struct.unpack(">H", self.d[4:6])[0]
        self.tables = {}
        for i in range(count):
            o = 12 + 16 * i
            tag = self.d[o:o + 4].decode("latin-1")
            off, ln = struct.unpack(">II", self.d[o + 8:o + 16])
            self.tables[tag] = (off, ln)
        for needed in ("head", "maxp", "loca", "glyf", "cmap", "hmtx", "hhea"):
            if needed not in self.tables:
                sys.exit(f"{path}: no {needed} table (is this a TrueType font?)")
        head = self.tables["head"][0]
        self.upem = struct.unpack(">H", self.d[head + 18:head + 20])[0]
        self.long_loca = struct.unpack(">h", self.d[head + 50:head + 52])[0]
        self.num_glyphs = struct.unpack(">H", self.d[self.tables["maxp"][0] + 4:
                                                     self.tables["maxp"][0] + 6])[0]
        self.num_hmetrics = struct.unpack(">H", self.d[self.tables["hhea"][0] + 34:
                                                       self.tables["hhea"][0] + 36])[0]
        self._cmap4()

    def _cmap4(self):
        base = self.tables["cmap"][0]
        n = struct.unpack(">H", self.d[base + 2:base + 4])[0]
        self.sub = None
        for i in range(n):
            off = struct.unpack(">I", self.d[base + 8 + 8 * i:base + 12 + 8 * i])[0]
            if struct.unpack(">H", self.d[base + off:base + off + 2])[0] == 4:
                self.sub = base + off
        if self.sub is None:
            sys.exit("font has no format 4 character map")

    def gid(self, ch):
        s, d = self.sub, self.d
        seg = struct.unpack(">H", d[s + 6:s + 8])[0] // 2
        ends = struct.unpack(f">{seg}H", d[s + 14:s + 14 + seg * 2])
        so = s + 16 + seg * 2
        starts = struct.unpack(f">{seg}H", d[so:so + seg * 2])
        do = so + seg * 2
        deltas = struct.unpack(f">{seg}h", d[do:do + seg * 2])
        ro = do + seg * 2
        ranges = struct.unpack(f">{seg}H", d[ro:ro + seg * 2])
        c = ord(ch)
        for i in range(seg):
            if starts[i] <= c <= ends[i]:
                if ranges[i] == 0:
                    return (c + deltas[i]) & 0xFFFF
                addr = ro + 2 * i + ranges[i] + 2 * (c - starts[i])
                g = struct.unpack(">H", d[addr:addr + 2])[0]
                return (g + deltas[i]) & 0xFFFF if g else 0
        return 0

    def advance(self, g):
        hm = self.tables["hmtx"][0]
        i = min(g, self.num_hmetrics - 1)
        return struct.unpack(">H", self.d[hm + 4 * i:hm + 4 * i + 2])[0]

    def contours(self, g, dx=0, dy=0):
        """[[(x, y, on_curve), ...], ...] in font units."""
        lo = self.tables["loca"][0]
        if self.long_loca:
            a, b = struct.unpack(">II", self.d[lo + 4 * g:lo + 4 * g + 8])
        else:
            a, b = (x * 2 for x in struct.unpack(">HH", self.d[lo + 2 * g:lo + 2 * g + 4]))
        if a == b:
            return []
        o = self.tables["glyf"][0] + a
        n = struct.unpack(">h", self.d[o:o + 2])[0]
        if n < 0:
            return self._composite(o + 10, dx, dy)
        ends = struct.unpack(f">{n}H", self.d[o + 10:o + 10 + n * 2])
        p = o + 10 + n * 2
        p += 2 + struct.unpack(">H", self.d[p:p + 2])[0]          # skip hinting
        total = ends[-1] + 1
        flags = []
        while len(flags) < total:
            f = self.d[p]; p += 1
            flags.append(f)
            if f & 8:
                r = self.d[p]; p += 1
                flags.extend([f] * r)
        flags = flags[:total]

        def coords(short_bit, same_bit):
            out, v = [], 0
            nonlocal p
            for f in flags:
                if f & short_bit:
                    step = self.d[p]; p += 1
                    v += step if f & same_bit else -step
                elif not f & same_bit:
                    v += struct.unpack(">h", self.d[p:p + 2])[0]; p += 2
                out.append(v)
            return out

        xs = coords(2, 16)
        ys = coords(4, 32)
        result, start = [], 0
        for end in ends:
            result.append([(xs[i] + dx, ys[i] + dy, bool(flags[i] & 1))
                           for i in range(start, end + 1)])
            start = end + 1
        return result

    def _composite(self, p, dx, dy):
        out = []
        while True:
            flags, index = struct.unpack(">HH", self.d[p:p + 4]); p += 4
            if flags & 1:
                a1, a2 = struct.unpack(">hh", self.d[p:p + 4]); p += 4
            else:
                a1, a2 = struct.unpack(">bb", self.d[p:p + 2]); p += 2
            if flags & 8:
                p += 2
            elif flags & 0x40:
                p += 4
            elif flags & 0x80:
                p += 8
            if flags & 2:                      # args are offsets, the usual case
                out += self.contours(index, dx + a1, dy + a2)
            if not flags & 0x20:
                break
        return out


def path_data(contours, upem, size, x0, y1):
    """Font units -> an SVG path, y flipped, scaled to `size` per em."""
    s = size / upem
    def P(pt):
        return f"{(pt[0] - x0) * s:.2f},{(y1 - pt[1]) * s:.2f}"
    out = []
    for pts in contours:
        if not pts:
            continue
        # Start on a real point: rotate to the first on-curve one, or make
        # the implied midpoint between the two off-curve points that open
        # the contour.
        if not any(p[2] for p in pts):
            first = ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2, True)
            pts = [first] + pts
        else:
            i = next(i for i, p in enumerate(pts) if p[2])
            pts = pts[i:] + pts[:i]
        out.append("M" + P(pts[0]))
        i, n = 1, len(pts)
        while i <= n:
            cur = pts[i % n]
            if cur[2]:
                out.append("L" + P(cur))
                i += 1
                continue
            nxt = pts[(i + 1) % n]
            if not nxt[2]:                     # implied on-curve midpoint
                nxt = ((cur[0] + nxt[0]) / 2, (cur[1] + nxt[1]) / 2, True)
                out.append(f"Q{P(cur)} {P(nxt)}")
                i += 1
            else:
                out.append(f"Q{P(cur)} {P(nxt)}")
                i += 2
        out.append("Z")
    return "".join(out)


def main():
    args = [a for a in sys.argv[1:]]
    font_path, track = DEFAULT_FONT, 0.02
    for flag, cast in (("--font", str), ("--track", float)):
        if flag in args:
            i = args.index(flag)
            value = cast(args[i + 1])
            args = args[:i] + args[i + 2:]
            if flag == "--font":
                font_path = value
            else:
                track = value
    if len(args) < 2:
        sys.exit(__doc__)
    out_path, text = args[0], " ".join(args[1:])

    font = Font(font_path)
    tracking = track * font.upem
    pen, glyphs = 0.0, []
    for ch in text:
        g = font.gid(ch)
        if ch != " ":
            glyphs.append(font.contours(g, dx=int(round(pen)), dy=0))
        pen += font.advance(g) + tracking

    pts = [p for gl in glyphs for c in gl for p in c]
    if not pts:
        sys.exit(f"nothing to draw for {text!r} - is the font missing those glyphs?")
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)

    size = 100.0                                # arbitrary; the tile scales it
    scale = size / font.upem
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    body = "".join(f'<path d="{path_data(gl, font.upem, size, x0, y1)}" fill="{COLOUR}"/>'
                   for gl in glyphs if gl)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
           f'width="{w:.2f}" height="{h:.2f}">\n'
           f'<!-- "{text}" set in {os.path.basename(font_path)}, outlines only:\n'
           f'     the ES\'s SVG rasteriser does not render <text>. -->\n'
           f"{body}\n</svg>\n")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(svg)
    print(f"{out_path}: {text!r}  {w:.0f}x{h:.0f}  {len(glyphs)} glyphs")


if __name__ == "__main__":
    main()
