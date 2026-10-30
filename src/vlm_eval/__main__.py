"""Command-line entry point."""
import argparse
import json
import os
from pathlib import Path
import sys

from .dataset import load_dataset
from .providers import Ollama, LlamaCpp
from .runner import run, validate_request_limit
from .openai_provider import OpenAI, OpenAIConfigurationError


def main(argv=None):
    parser = argparse.ArgumentParser(description='Evaluate structured vision answers with explicit ground truth.')
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate', help='validate a dataset without contacting a provider')
    validate.add_argument('dataset', type=Path)
    evaluate = commands.add_parser('run', help='make one model request per dataset item')
    evaluate.add_argument('dataset', type=Path)
    evaluate.add_argument('--provider', choices=['ollama', 'llama-cpp', 'openai'], default='ollama')
    evaluate.add_argument('--model', required=True, help='model identifier for the selected provider (OpenAI access is account-dependent)')
    evaluate.add_argument('--out', required=True, type=Path)
    evaluate.add_argument('--temperature', type=float, default=None, help='local providers: default 0; unsupported with OpenAI')
    evaluate.add_argument('--seed', type=int, default=None, help='local providers: default 0; unsupported with OpenAI')
    evaluate.add_argument('--max-tokens', type=int, default=512, help='per-request output cap (default 512); OpenAI includes reasoning tokens, minimum 16')
    evaluate.add_argument('--max-requests', type=int, help='maximum requests; required for OpenAI; oversized datasets fail before any calls')
    evaluate.add_argument('--timeout', type=float, default=120.0, help='per-network-operation timeout in seconds (default 120); no retries')
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.dataset)
        if args.command == 'validate':
            print(json.dumps({'valid': True, 'items': len(dataset['manifest']['items']), 'manifest_sha256': dataset['manifest_sha256']}))
            return 0
        if args.provider == 'openai':
            provider = OpenAI(args.model, temperature=args.temperature, seed=args.seed,
                              max_tokens=args.max_tokens, timeout=args.timeout)
        else:
            provider_class = Ollama if args.provider == 'ollama' else LlamaCpp
            default_url = 'http://127.0.0.1:11434' if args.provider == 'ollama' else 'http://127.0.0.1:8080'
            provider = provider_class(args.model, os.environ.get('VLM_EVAL_BASE_URL', default_url),
                                      api_key=os.environ.get('VLM_EVAL_API_KEY'),
                                      temperature=0.0 if args.temperature is None else args.temperature,
                                      seed=0 if args.seed is None else args.seed,
                                      max_tokens=args.max_tokens, timeout=args.timeout)
        validate_request_limit(dataset, provider, args.max_requests)
        # Reserve output before inference; never overwrite a previous run.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            report = run(dataset, provider, max_requests=args.max_requests)
            json.dump(report, target, indent=2, ensure_ascii=False, allow_nan=False)
            target.write('\n')
        print(json.dumps(report['summary']))
        return 1 if any(row['status'] != 'ok' for row in report['rows']) else 0
    except OpenAIConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError):
        print('Evaluation could not complete: check dataset, configuration, and unused output path. No sensitive error details displayed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
