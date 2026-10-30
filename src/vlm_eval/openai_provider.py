"""Bounded, stateless OpenAI Responses API vision evaluation (no SDK required)."""
import base64
from http.client import HTTPException
import json
import math
import os
import urllib.error
import urllib.request

from .dataset import parse_json
from .providers import NoRedirect

ENDPOINT = 'https://api.openai.com/v1/responses'
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_REQUEST_BYTES = 32 * 1024 * 1024


class OpenAIConfigurationError(ValueError):
    """Static configuration advice, safe to display at the CLI."""


class OpenAIRequestError(RuntimeError):
    """Fixed codes only; never carry an HTTP body, header or exception text."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class OpenAIResponseError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def output_schema(fields):
    """Only output field names/types cross this boundary, never truth states/values."""
    if not fields or len(fields) > 100 or any(not isinstance(f, str) or not f.strip() or len(f) > 128 for f in fields):
        raise OpenAIConfigurationError('OpenAI requires 1-100 field names of at most 128 characters')
    return {'type': 'object', 'properties': {f: {'type': ['string', 'null']} for f in fields},
            'required': list(fields), 'additionalProperties': False}


def usage_metrics(raw):
    usage = raw.get('usage')
    result = {}
    if isinstance(usage, dict):
        for key in ('input_tokens', 'output_tokens', 'total_tokens'):
            if type(usage.get(key)) is int and usage[key] >= 0:
                result[key] = usage[key]
        for parent, key in [('input_tokens_details', 'cached_tokens'), ('output_tokens_details', 'reasoning_tokens')]:
            detail = usage.get(parent)
            if isinstance(detail, dict) and type(detail.get(key)) is int and detail[key] >= 0:
                result[key] = detail[key]
    return result


def inference_record(raw):
    """Retain raw inference text and safe metadata, not the whole API envelope."""
    if not isinstance(raw, dict):
        raise OpenAIRequestError('invalid_response_json')
    record = {k: raw[k] for k in ('id', 'model', 'status') if isinstance(raw.get(k), str)}
    record['has_error'] = raw.get('error') is not None
    reason = raw.get('incomplete_details')
    if isinstance(reason, dict):
        record['incomplete_details'] = {'reason': reason.get('reason') if reason.get('reason') in (
            'max_output_tokens', 'max_messages', 'content_filter', 'steered') else 'unknown'}
    # Do not store error bodies, annotations, input echoes, tools, or provider metadata.
    output = raw.get('output')
    record['output'] = None
    if isinstance(output, list):
        record['output'] = []
        for item in output:
            if not isinstance(item, dict):
                record['output'].append(None)
                continue
            kept = {k: item[k] for k in ('type', 'role', 'status') if isinstance(item.get(k), str)}
            if isinstance(item.get('content'), list):
                kept['content'] = [{k: part[k] for k in ('type', 'text', 'refusal') if k in part}
                                   if isinstance(part, dict) else None for part in item['content']]
            record['output'].append(kept)
    metrics = usage_metrics(raw)
    record['usage'] = {k: v for k, v in metrics.items() if k in ('input_tokens', 'output_tokens', 'total_tokens')}
    if 'cached_tokens' in metrics:
        record['usage']['input_tokens_details'] = {'cached_tokens': metrics['cached_tokens']}
    if 'reasoning_tokens' in metrics:
        record['usage']['output_tokens_details'] = {'reasoning_tokens': metrics['reasoning_tokens']}
    return record


class OpenAI:
    def __init__(self, model, *, api_key=None, temperature=None, seed=None, max_tokens=512, timeout=120.0):
        if seed is not None or temperature is not None:
            raise OpenAIConfigurationError('OpenAI adapter does not support --seed or --temperature; omit both')
        if not isinstance(model, str) or not model.strip() or type(max_tokens) is not int or max_tokens < 16 or not math.isfinite(timeout) or timeout <= 0:
            raise OpenAIConfigurationError('invalid OpenAI model, output-token limit (minimum 16), or timeout')
        key = os.environ.get('OPENAI_API_KEY') if api_key is None else api_key
        if not isinstance(key, str) or not key or any(c.isspace() or not 33 <= ord(c) <= 126 for c in key):
            raise OpenAIConfigurationError('set OPENAI_API_KEY to a nonempty credential without whitespace')
        self._api_key = key
        self.timeout = timeout
        self.metadata = {'interface': 'openai-responses', 'model': model,
                         'settings': {'max_output_tokens': max_tokens, 'image_detail': 'auto',
                                      'sampling': 'model_default', 'reasoning': 'model_default'},
                         'timeout_seconds': timeout, 'retries': 0, 'store': False, 'stream': False,
                         'format': 'strict-json-schema-string-or-null-v1', 'endpoint_recorded': False}

    def generate(self, prompt, images, *, fields):
        schema = output_schema(fields)
        content = [{'type': 'input_text', 'text': prompt}]
        for image in images:
            data = image['bytes']
            if len(data) > 20 * 1024 * 1024:
                raise OpenAIRequestError('invalid_image')
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                mime = 'image/png'
            elif data.startswith(b'\xff\xd8\xff'):
                mime = 'image/jpeg'
            else:
                raise OpenAIRequestError('invalid_image')
            content.append({'type': 'input_image', 'detail': 'auto',
                            'image_url': f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')})
        payload = {'model': self.metadata['model'], 'store': False, 'stream': False,
                   'max_output_tokens': self.metadata['settings']['max_output_tokens'],
                   'input': [{'role': 'user', 'content': content}],
                   'text': {'format': {'type': 'json_schema', 'name': 'vision_evaluation',
                                       'strict': True, 'schema': schema}}}
        body = json.dumps(payload, allow_nan=False).encode()
        if len(body) > MAX_REQUEST_BYTES:
            raise OpenAIRequestError('request_too_large')
        request = urllib.request.Request(ENDPOINT, data=body,
                                         headers={'Content-Type': 'application/json',
                                                  'Authorization': 'Bearer ' + self._api_key})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            code = 'authentication_error' if exc.code in (401, 403) else 'rate_limited' if exc.code == 429 else 'http_error'
            exc.close()
            raise OpenAIRequestError(code) from None
        except (OSError, HTTPException, ValueError):
            raise OpenAIRequestError('transport_error') from None
        if len(data) > MAX_RESPONSE_BYTES:
            raise OpenAIRequestError('response_too_large')
        try:
            record = inference_record(parse_json(data))
            # Defense against accidental credential echoes in response text.
            return parse_json(json.dumps(record, allow_nan=False).replace(json.dumps(self._api_key)[1:-1], '[REDACTED]'))
        except (ValueError, RecursionError):
            raise OpenAIRequestError('invalid_response_json') from None

    def parse_response(self, raw, fields):
        if raw.get('has_error') or raw.get('status') == 'failed':
            raise OpenAIResponseError('upstream_error')
        if raw.get('status') == 'incomplete':
            raise OpenAIResponseError('incomplete')
        if raw.get('status') != 'completed' or not isinstance(raw.get('output'), list):
            raise OpenAIResponseError('malformed_output')
        messages = []
        for item in raw['output']:
            if not isinstance(item, dict):
                raise OpenAIResponseError('malformed_output')
            if item.get('type') == 'reasoning':
                continue
            if item.get('type') != 'message' or item.get('role') != 'assistant' or item.get('status') != 'completed':
                raise OpenAIResponseError('malformed_output')
            messages.append(item)
        if len(messages) != 1 or not isinstance(messages[0].get('content'), list):
            raise OpenAIResponseError('malformed_output')
        parts = messages[0]['content']
        if any(isinstance(p, dict) and p.get('type') == 'refusal' for p in parts):
            raise OpenAIResponseError('refusal')
        if len(parts) != 1 or not isinstance(parts[0], dict) or parts[0].get('type') != 'output_text' or not isinstance(parts[0].get('text'), str):
            raise OpenAIResponseError('malformed_output')
        try:
            prediction = parse_json(parts[0]['text'])
            if not isinstance(prediction, dict) or set(prediction) != set(fields) or any(v is not None and not isinstance(v, str) for v in prediction.values()):
                raise ValueError('schema mismatch')
        except (ValueError, RecursionError):
            raise OpenAIResponseError('malformed_output') from None
        return prediction
