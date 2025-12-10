#!/usr/bin/env python3
"""
Simple icon creator that generates basic PNG icons without external dependencies.
Creates colored square icons with simple lock emoji.
"""

import struct
import zlib

def create_simple_png(width, height, rgb_color):
    """Create a simple solid color PNG file."""
    def png_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk))

    # PNG signature
    png_data = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk (header)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    png_data += png_chunk(b'IHDR', ihdr_data)

    # IDAT chunk (image data)
    raw_data = b''
    r, g, b = rgb_color
    for y in range(height):
        raw_data += b'\x00'  # Filter type: None
        raw_data += bytes([r, g, b]) * width

    idat_data = zlib.compress(raw_data, 9)
    png_data += png_chunk(b'IDAT', idat_data)

    # IEND chunk (end)
    png_data += png_chunk(b'IEND', b'')

    return png_data

# Create icons in Saint Clair blue color
blue_color = (33, 150, 243)  # #2196F3 in RGB

sizes = [
    (16, 'icon16.png'),
    (48, 'icon48.png'),
    (128, 'icon128.png')
]

print("🎨 Creating extension icons...\n")

for size, filename in sizes:
    png_data = create_simple_png(size, size, blue_color)
    with open(filename, 'wb') as f:
        f.write(png_data)
    print(f"✅ Created {filename} ({size}x{size})")

print("\n🎉 All icons created successfully!")
print("📝 Note: These are simple blue squares. You can replace them with better designs later.")
