"""Strict portable datasets; only explicit relative PNG/JPEG files are read."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from .scoring import TruthState


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON number')


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number")
    return number


def parse_json(text):
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 100000


def load_dataset(path):
    path = Path(path)
    raw = parse_json(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or set(raw) != {'schema_version', 'dataset_id', 'version', 'prompt', 'items'}:
        raise ValueError('invalid dataset keys')
    if type(raw['schema_version']) is not int or raw['schema_version'] != 1:
        raise ValueError('unsupported dataset schema')
    if not all(text(raw[k]) for k in ('dataset_id', 'version', 'prompt')):
        raise ValueError('dataset identity, version and prompt must be nonempty strings')
    if not isinstance(raw['items'], list) or not raw['items']:
        raise ValueError('dataset must contain items')
    ids, images = set(), {}
    for item in raw['items']:
        if not isinstance(item, dict) or set(item) != {'id', 'images', 'truth'}:
            raise ValueError('invalid item keys')
        if not text(item['id']) or item['id'] in ids:
            raise ValueError('invalid or duplicate item id')
        ids.add(item['id'])
        if not isinstance(item['truth'], dict) or not item['truth']:
            raise ValueError('truth must contain fields')
        for field, truth in item['truth'].items():
            if not text(field) or not isinstance(truth, dict):
                raise ValueError('invalid truth field')
            state = TruthState(truth.get('state'))
            expected = {'state', 'value'} if state == TruthState.VALUE else {'state'}
            if set(truth) != expected or (state == TruthState.VALUE and not text(truth['value'])):
                raise ValueError('invalid truth value')
        if not isinstance(item['images'], list) or not item['images']:
            raise ValueError('item needs images')
        images[item['id']] = []
        seen = set()
        for name in item['images']:
            if not text(name) or '\\' in name:
                raise ValueError('invalid image path')
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name or name in seen:
                raise ValueError('image must have a unique canonical relative path')
            seen.add(name)
            file = path.parent
            for part in relative.parts:
                file /= part
                if file.is_symlink():
                    raise ValueError('image symlinks are not supported')
            if file.suffix.lower() not in {'.jpg', '.jpeg', '.png'} or not file.is_file():
                raise ValueError('expected a PNG or JPEG file')
            if file.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('image exceeds 20 MiB')
            data = file.read_bytes()
            if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):
                raise ValueError('image signature is not PNG/JPEG')
            images[item['id']].append({'path': name, 'sha256': digest(data), 'bytes': data})
    canonical = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return {'manifest': raw, 'manifest_sha256': digest(canonical), 'images': images}
