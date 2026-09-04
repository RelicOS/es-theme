#!/usr/bin/env python3
"""Cut the RelicOS mark out of the boot splash artwork into art/logo.png.

The boot splash (system/board/r36s/splash/relicos-splash-640x480.png, the one
S15splash paints on /dev/fb0) is a 640x480 frame with the mark and the
wordmark centred on the flat background. The ES's own loading screen wants
just the artwork, so this crops to the bounding box of everything that is not
the background colour and writes it out with the same background kept opaque
- the splash paints the identical colour behind it.

Standard library only, like tools/gen-assets.py.

    python3 tools/crop-logo.py [SOURCE.png]
"""
import os
import struct
import sys
import zlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(os.path.dirname(ROOT), "system", "board", "r36s",
                           "splash", "relicos-splash-640x480.png")
DEST = os.path.join(ROOT, "art", "logo.png")
MARGIN = 8


def read_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"{path}: not a PNG")
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    width, height, depth, ctype, _, _, interlace = ihdr
    if depth != 8 or ctype not in (2, 6) or interlace:
        sys.exit(f"{path}: need 8-bit RGB/RGBA, non-interlaced")
    bpp = 4 if ctype == 6 else 3
    stride = width * bpp
    raw = zlib.decompress(idat)
    rows, prev, p = [], bytearray(stride), 0
    for _ in range(height):
        f, cur = raw[p], bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for i in range(stride):
            a = cur[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                cur[i] = (cur[i] + a) & 255
            elif f == 2:
                cur[i] = (cur[i] + b) & 255
            elif f == 3:
                cur[i] = (cur[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        rows.append(bytes(cur))
        prev = cur
    return width, height, bpp, rows


def write_png(path, width, height, rows):
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(png)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    w, h, bpp, rows = read_png(src)

    counts = Counter()
    for row in rows:
        for x in range(w):
            counts[row[x * bpp:x * bpp + 3]] += 1
    background = counts.most_common(1)[0][0]

    x0, y0, x1, y1 = w, h, -1, -1
    for y, row in enumerate(rows):
        for x in range(w):
            if row[x * bpp:x * bpp + 3] != background:
                x0, y0 = min(x0, x), min(y0, y)
                x1, y1 = max(x1, x), max(y1, y)
    if x1 < 0:
        sys.exit(f"{src}: the whole image is one colour")

    x0, y0 = max(0, x0 - MARGIN), max(0, y0 - MARGIN)
    x1, y1 = min(w - 1, x1 + MARGIN), min(h - 1, y1 + MARGIN)

    out = [bytes(b for x in range(x0, x1 + 1)
                 for b in rows[y][x * bpp:x * bpp + 3])
           for y in range(y0, y1 + 1)]
    write_png(DEST, x1 - x0 + 1, y1 - y0 + 1, out)
    print(f"art/logo.png: {x1 - x0 + 1}x{y1 - y0 + 1} "
          f"cropped from {os.path.relpath(src, os.path.dirname(ROOT))}, "
          f"background #{background[0]:02x}{background[1]:02x}{background[2]:02x}")


if __name__ == "__main__":
    main()
