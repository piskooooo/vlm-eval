"""Serial evaluation with raw response custody and explicit failure denominators."""
from datetime import datetime, timezone
import time
from http.client import HTTPException
from uuid import uuid4

from .dataset import parse_json
from .scoring import TruthField, TruthState, score_exact, score_truth_field
from . import __version__


def run(dataset, provider):
    manifest = dataset['manifest']
    report = {
        'schema_version': 1, 'tool_version': __version__, 'run_id': str(uuid4()),
        'started_at': datetime.now(timezone.utc).isoformat(),
        'dataset': {'id': manifest['dataset_id'], 'version': manifest['version'],
                    'manifest_sha256': dataset['manifest_sha256']},
        'provider': provider.metadata, 'prompt': manifest['prompt'],
        'scoring': 'normalized-exact-truth-states-v1', 'rows': [], 'summary': {},
    }
    for item in manifest['items']:
        started = time.perf_counter()
        raw, prediction, status = None, {}, 'ok'
        try:
            raw = provider.generate(manifest['prompt'], dataset['images'][item['id']])
        except (OSError, ValueError, RuntimeError, HTTPException):
            status = 'request_error'
        if status == 'ok':
            try:
                if provider.metadata.get('interface') == 'llama-cpp-chat':
                    choices = raw['choices']
                    if not isinstance(choices, list) or len(choices) != 1 or choices[0]['finish_reason'] != 'stop':
                        raise ValueError('expected one completed choice')
                    content = choices[0]['message']['content']
                else:
                    content = raw['message']['content']
                prediction = parse_json(content)
                if not isinstance(prediction, dict) or any(v is not None and not isinstance(v, str) for v in prediction.values()):
                    raise ValueError('expected string or null fields')
                if raw.get('done') is False or raw.get('done_reason') == 'length':
                    raise ValueError('incomplete response')
            except (ValueError, KeyError, TypeError):
                prediction, status = {}, 'invalid_response'
        scores = {}
        for field, truth in item['truth'].items():
            typed = TruthField(TruthState(truth['state']), truth.get('value'))
            score = score_truth_field(typed, prediction.get(field), score_exact)
            if score is not None and (status != 'ok' or field not in prediction):
                score = {**score, 'pass': False, 'outcome': status if status != 'ok' else 'missing_field'}
            scores[field] = score
            counter = report['summary'].setdefault(field, {'pass': 0, 'fail': 0, 'skip': 0})
            counter['skip' if score is None else 'pass' if score['pass'] else 'fail'] += 1
        usage = {}
        if isinstance(raw, dict):
            for key in ('prompt_eval_count', 'eval_count', 'total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration'):
                if type(raw.get(key)) is int and raw[key] >= 0:
                    usage[key] = raw[key]
            if provider.metadata.get('interface') == 'llama-cpp-chat' and isinstance(raw.get('usage'), dict):
                for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                    if type(raw['usage'].get(key)) is int and raw['usage'][key] >= 0:
                        usage[key] = raw['usage'][key]
        report['rows'].append({
            'id': item['id'], 'truth': item['truth'], 'status': status,
            'images': [{k: v for k, v in image.items() if k != 'bytes'} for image in dataset['images'][item['id']]],
            'raw': raw, 'prediction': prediction, 'scores': scores,
            'wall_seconds': time.perf_counter() - started, 'provider_metrics': usage,
        })
    for counter in report['summary'].values():
        total = counter['pass'] + counter['fail']
        counter['rate'] = counter['pass'] / total if total else None
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    return report
