#!/usr/bin/env python3
"""Generate the theme's bitmap assets without any image library.

Writes:
  art/white.png  8x8 opaque white, tinted by the theme (rows, cards, bars)

art/systems/default.png used to be generated here too - a flat gradient
standing in for the system banner. It is artwork now, so this tool leaves
it alone; regenerating it would paint over the banner. The old generator
is in the history if the placeholder is ever wanted back.

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
    print("assets written")


if __name__ == "__main__":
    main()
