"""Validate the redistributable dataset's actual pixels, metadata and workflow."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zlib

from vlm_eval.dataset import load_dataset
from vlm_eval.runner import run

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/shapes'


class ExampleTests(unittest.TestCase):
    def test_png_content_and_provenance(self):
        dataset = load_dataset(EXAMPLE / 'dataset.json')
        provenance = json.loads((EXAMPLE / 'provenance.json').read_text())
        self.assertEqual(len(dataset['manifest']['items']), 3)
        self.assertEqual(provenance['license'], 'MIT')
        colors = {'red': (220, 30, 30), 'green': (20, 160, 60), 'blue': (30, 80, 220)}
        for item in dataset['manifest']['items']:
            image = dataset['images'][item['id']][0]
            data = image['bytes']
            self.assertEqual(hashlib.sha256(data).hexdigest(), provenance['sha256'][image['path']])
            offset, chunks, compressed = 8, [], b''
            while offset < len(data):
                size = struct.unpack('>I', data[offset:offset+4])[0]
                kind = data[offset+4:offset+8]
                payload = data[offset+8:offset+8+size]
                crc = struct.unpack('>I', data[offset+8+size:offset+12+size])[0]
                self.assertEqual(zlib.crc32(kind + payload), crc)
                chunks.append(kind)
                if kind == b'IHDR':
                    self.assertEqual(struct.unpack('>IIBBBBB', payload), (256, 256, 8, 2, 0, 0, 0))
                if kind == b'IDAT':
                    compressed += payload
                offset += 12 + size
            self.assertEqual(chunks, [b'IHDR', b'IDAT', b'IEND'])
            pixels = zlib.decompress(compressed)
            self.assertEqual(len(pixels), 256 * 769)
            expected = bytes(colors[item['truth']['color']['value']])
            for row in range(256):
                self.assertEqual(pixels[row * 769], 0)
            self.assertEqual(pixels[128 * 769 + 1 + 128 * 3:128 * 769 + 1 + 129 * 3], expected)
            self.assertEqual(pixels[1:4], b'\xff\xff\xff')

    def test_example_workflow_fixture(self):
        dataset = load_dataset(EXAMPLE / 'dataset.json')
        answers = iter([{'color': 'red', 'shape': 'circle'},
                        {'color': 'green', 'shape': 'square'},
                        {'color': 'blue', 'shape': 'triangle'}])
        class Fixture:
            metadata = {'interface': 'fixture', 'model': 'not-a-model'}
            def generate(self, prompt, images):
                return {'message': {'content': json.dumps(next(answers))}, 'done': True}
        report = run(dataset, Fixture())
        self.assertEqual(len(report['rows']), 3)
        for field in ('color', 'shape'):
            self.assertEqual(report['summary'][field], {'pass': 3, 'fail': 0, 'skip': 0, 'rate': 1.0})
