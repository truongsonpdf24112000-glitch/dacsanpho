#!/usr/bin/env python3
"""Generate PWA icons as solid-color PNGs using pure Python."""
import struct, zlib, sys

def create_png(width, height, r, g, b, filepath):
    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            raw += bytes([r, g, b, 255])

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + c + crc

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(raw)
    png = sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

    with open(filepath, 'wb') as f:
        f.write(png)
    print(f"  {filepath} ({len(png)} bytes, {width}x{height})")

icons_dir = sys.argv[1] if len(sys.argv) > 1 else 'public/icons'
create_png(192, 192, 229, 57, 53, f'{icons_dir}/icon-192.png')
create_png(512, 512, 229, 57, 53, f'{icons_dir}/icon-512.png')
create_png(1200, 630, 229, 57, 53, f'{icons_dir}/og-image.png')
print("Done!")
