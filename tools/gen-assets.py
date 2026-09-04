#!/usr/bin/env python3
"""Generate the theme's bitmap assets without any image library.

Writes:
  art/white.png            8x8 opaque white, tinted by the theme (rows, cards, bars)
  art/systems/default.png  64x48 dark gradient, the hero placeholder for
                           systems that have no art/systems/<theme>.png

Run from anywhere: `python3 tools/gen-assets.py`.
"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_png(path, width, height, rows, alpha):
    """rows: list of bytes, each row = width * (4 if alpha else 3) bytes."""
    color_type = 6 if alpha else 2
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def lerp(a, b, t):
    return int(round(a + (b - a) * t))


def main():
    # white.png
    w = h = 8
    write_png(os.path.join(ROOT, "art", "white.png"), w, h,
              [bytes([255, 255, 255, 255]) * w for _ in range(h)], alpha=True)

    # systems/default.png: top #1a2033 -> bottom #10141f, with a faint
    # diagonal banding so it does not read as a flat fill.
    w, h = 64, 48
    top, bottom = (0x1A, 0x20, 0x33), (0x10, 0x14, 0x1F)
    rows = []
    for y in range(h):
        t = y / (h - 1)
        base = [lerp(top[i], bottom[i], t) for i in range(3)]
        row = bytearray()
        for x in range(w):
            band = 4 if ((x + y) // 6) % 2 == 0 else 0
            row += bytes(min(255, c + band) for c in base)
        rows.append(bytes(row))
    write_png(os.path.join(ROOT, "art", "systems", "default.png"), w, h, rows, alpha=False)
    print("assets written")


if __name__ == "__main__":
    main()
