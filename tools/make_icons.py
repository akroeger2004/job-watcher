"""Draw the app icons (three rising bars on blue) with the standard library only.

    python tools/make_icons.py

Writes icons/icon-192.png, icons/icon-512.png and icons/icon-maskable-512.png.
The maskable icon keeps the artwork inside the central safe zone.
"""
import struct
import zlib
from pathlib import Path

BLUE = (42, 120, 214, 255)
PAPER = (252, 252, 251, 255)
CLEAR = (0, 0, 0, 0)


def png(width, height, pixels):
    raw = b"".join(b"\x00" + bytes(c for px in pixels[y * width:(y + 1) * width] for c in px)
                   for y in range(height))

    def chunk(kind, body):
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def icon(size, maskable):
    pad = 0.2 if maskable else 0.0          # maskable: keep art in the safe zone
    radius = 0 if maskable else size * 0.22  # maskable icons are full-bleed squares
    art = size * (1 - 2 * pad)
    left, top = size * pad, size * pad
    bar_w = art * 0.2
    gap = art * 0.1
    heights = (0.34, 0.58, 0.82)
    total = 3 * bar_w + 2 * gap
    x0 = left + (art - total) / 2
    base = top + art * 0.9
    bars = []
    for i, h in enumerate(heights):
        x = x0 + i * (bar_w + gap)
        bars.append((x, base - art * h, x + bar_w, base))

    def inside_round(x, y):
        if radius == 0:
            return True
        cx = min(max(x, radius), size - radius)
        cy = min(max(y, radius), size - radius)
        return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2

    pixels = []
    for y in range(size):
        for x in range(size):
            if not inside_round(x + 0.5, y + 0.5):
                pixels.append(CLEAR)
            elif any(a <= x < c and b <= y < d for a, b, c, d in bars):
                pixels.append(PAPER)
            else:
                pixels.append(BLUE)
    return png(size, size, pixels)


def main():
    out = Path(__file__).resolve().parent.parent / "icons"
    out.mkdir(exist_ok=True)
    (out / "icon-192.png").write_bytes(icon(192, False))
    (out / "icon-512.png").write_bytes(icon(512, False))
    (out / "icon-maskable-512.png").write_bytes(icon(512, True))
    print("wrote icons to", out)


if __name__ == "__main__":
    main()
