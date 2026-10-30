"""Rebuild the original geometric example assets with Python's standard library.

Copyright (c) 2026 vlm-eval contributors. SPDX-License-Identifier: MIT
No source images, fonts, model calls or external assets are used.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

HERE = Path(__file__).resolve().parent
CASES = [('001.png', 'red', 'circle', (220, 30, 30)),
         ('002.png', 'green', 'square', (20, 160, 60)),
         ('003.png', 'blue', 'triangle', (30, 80, 220))]


def inside(shape, x, y):
    if shape == 'circle':
        return (x - 128) ** 2 + (y - 128) ** 2 <= 80 ** 2
    if shape == 'square':
        return 48 <= x <= 207 and 48 <= y <= 207
    return 40 <= y <= 216 and abs(x - 128) * 2 <= y - 40


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))


def main():
    hashes, items = {}, []
    for filename, color, shape, rgb in CASES:
        rows = b''.join(b'\x00' + b''.join(bytes(rgb if inside(shape, x, y) else (255, 255, 255))
                                         for x in range(256)) for y in range(256))
        data = (b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(rows, level=9)) + chunk(b'IEND', b''))
        (HERE / filename).write_bytes(data)
        hashes[filename] = hashlib.sha256(data).hexdigest()
        items.append({'id': filename[:-4], 'images': [filename], 'truth': {
            'color': {'state': 'value', 'value': color},
            'shape': {'state': 'value', 'value': shape}}})
    manifest = {'schema_version': 1, 'dataset_id': 'basic-shapes', 'version': '1',
                'prompt': 'Inspect the single colored shape on a white background. Return only a JSON object with color and shape fields. Use a basic color name and a basic shape name as strings, or null if a field cannot be determined.',
                'items': items}
    provenance = {'license': 'MIT', 'copyright': 'Copyright (c) 2026 vlm-eval contributors',
                  'created': '2026-10-30', 'generator': 'generate.py',
                  'source': 'Original procedural geometry; no external assets, fonts, photos or model outputs.',
                  'sha256': hashes}
    for name, content in [('dataset.json', manifest), ('provenance.json', provenance)]:
        (HERE / name).write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
